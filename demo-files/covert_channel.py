"""
Webpage-source based covert channel  -  proof of concept
========================================================

Implements the scheme from Madiraju, Johnson, Yuan & Lutz (RIT, 2012).


Both sides derive identical dictionaries from the same (unmodified) page:

    URL dictionary : every unique URL on the page, sorted, numbered 0..n-1
        0 -> START   (control)
        1 -> WAIT    (control)
        2 -> END     (control)
        3..n-1 -> usable for words / shifts

    Word dictionary: every unique word on the page, sorted alphabetically,
        mapped onto URL numbers:
          * first (n-3) words  -> a single URL      e.g. about -> (3,)
          * remaining words    -> shift + WAIT + word
                                  e.g. research -> (12, 1, 48)

"""

import re
from html.parser import HTMLParser

# Control URL numbers (fixed by the scheme)
START, WAIT, END = 0, 1, 2


class _PageParser(HTMLParser):
    """Pull <a href> links and visible text out of an HTML page."""

    def __init__(self):
        super().__init__()
        self.urls = []
        self._text = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        if tag == "a":
            for key, val in attrs:
                if key == "href" and val:
                    self.urls.append(val.strip())

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    @property
    def text(self):
        return " ".join(self._text)


def parse_page(html):
    """Return (sorted unique urls, sorted unique lowercase words)."""
    p = _PageParser()
    p.feed(html)
    urls = sorted({u for u in p.urls if u})
    words = sorted(set(re.findall(r"[a-z']+", p.text.lower())))
    return urls, words


def build_dictionaries(urls, words):
    """
    Build the shared dictionaries. Identical logic runs on both sides;
    the receiver just uses the reverse lookups.
    """
    n = len(urls)
    if n < 4:
        raise ValueError("Page needs at least 4 URLs (3 control + >=1 usable).")

    num_to_url = {i: urls[i] for i in range(n)}   # sender: number -> url
    url_to_num = {urls[i]: i for i in range(n)}   # receiver: url -> number

    k = n - 3                                     # usable (non-control) URLs
    capacity = k + k * k
    usable_words = words[:capacity]               # anything past capacity is unsendable

    word_to_code, code_to_word = {}, {}
    for idx, word in enumerate(usable_words):
        if idx < k:                               # single-URL word
            code = (3 + idx,)
        else:                                     # multi-URL word: shift + WAIT + word
            m = idx - k
            shift, pos = divmod(m, k)
            code = (3 + shift, WAIT, 3 + pos)
        word_to_code[word] = code
        code_to_word[code] = word

    return {
        "n": n,
        "k": k,
        "capacity": capacity,
        "num_to_url": num_to_url,
        "url_to_num": url_to_num,
        "word_to_code": word_to_code,
        "code_to_word": code_to_word,
    }


# --------------------------------------------------------------------------
# SENDER SIDE
# --------------------------------------------------------------------------
def encode_message(message, d):
    """
    Turn a plain-text message into the ordered list of URL NUMBERS the
    sender must request. Every message word must exist in the page vocabulary.
    """
    words = re.findall(r"[a-z']+", message.lower())
    missing = [w for w in words if w not in d["word_to_code"]]
    if missing:
        raise KeyError("These words are not on the page: " + ", ".join(sorted(set(missing))))

    seq = [START]
    for w in words:
        seq.extend(d["word_to_code"][w])
    seq.append(END)
    return seq


def numbers_to_urls(num_seq, d):
    """Map the URL-number sequence to the actual URLs the client will GET."""
    return [d["num_to_url"][x] for x in num_seq]


# --------------------------------------------------------------------------
# RECEIVER SIDE
# --------------------------------------------------------------------------
def urls_to_numbers(url_seq, d):
    """Receiver turns observed URL requests back into URL numbers."""
    return [d["url_to_num"][u] for u in url_seq if u in d["url_to_num"]]


def decode_numbers(num_seq, d):
    """Reconstruct the message from an ordered list of URL numbers."""
    if START not in num_seq:
        raise ValueError("No START control URL seen - not a covert transmission.")
    seq = num_seq[num_seq.index(START) + 1:]
    if END in seq:
        seq = seq[:seq.index(END)]

    words, i = [], 0
    while i < len(seq):
        x = seq[i]
        # A WAIT immediately after a URL flags a multi-URL (shift) word.
        if i + 1 < len(seq) and seq[i + 1] == WAIT:
            y = seq[i + 2]
            code = (x, WAIT, y)
            i += 3
        else:
            code = (x,)
            i += 1
        words.append(d["code_to_word"].get(code, "<?>"))
    return " ".join(words)