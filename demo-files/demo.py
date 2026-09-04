"""
End-to-end demonstration of the webpage-source covert channel.

We never touch the network here: instead we simulate a shared access log
(what an Apache log or a .pcap would give the receiver). The sender's GET
requests are interleaved with innocent traffic from other IP addresses to
show that the receiver simply filters by the sender's IP and preserves order.

Run:  python demo.py "return the books tonight near the old bridge"
"""

import sys
import random
from covert_channel import (
    parse_page, build_dictionaries,
    encode_message, numbers_to_urls,
    urls_to_numbers, decode_numbers,
)

SENDER_IP = "192.168.0.6"
NOISE_IPS = ["10.0.0.4", "10.0.0.9", "172.16.5.2"]


def load_page(path="index.html"):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def build_noisy_log(sender_urls, all_urls):
    """
    Interleave the sender's ordered requests with random innocent requests
    from other clients. Returns a list of (ip, url) log lines.
    Sender order is preserved; noise is scattered around it.
    """
    log = []
    for url in sender_urls:
        # 0-2 innocent hits before each covert request
        for _ in range(random.randint(0, 2)):
            log.append((random.choice(NOISE_IPS), random.choice(all_urls)))
        log.append((SENDER_IP, url))
    for _ in range(random.randint(1, 3)):
        log.append((random.choice(NOISE_IPS), random.choice(all_urls)))
    return log


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "return the books tonight near the old bridge"

    html = load_page()
    urls, words = parse_page(html)
    d = build_dictionaries(urls, words)

    print("=" * 68)
    print("SHARED SETUP (identical on both sides, derived from the page)")
    print("=" * 68)
    print(f"URLs on page : {d['n']}   (3 control + {d['k']} usable)")
    print(f"Words on page: {len(words)}")
    print(f"Word capacity: {d['capacity']}  = (n-3) + (n-3)^2")
    print()
    print("URL dictionary (first entries):")
    for i in range(min(d["n"], 8)):
        tag = {0: "  <START>", 1: "   <WAIT>", 2: "    <END>"}.get(i, "")
        print(f"  {i:2d}{tag} : {d['num_to_url'][i]}")
    print()

    # ---- SENDER ----
    print("=" * 68)
    print("SENDER  (web client)")
    print("=" * 68)
    print(f"Secret message : {message!r}")
    num_seq = encode_message(message, d)
    url_seq = numbers_to_urls(num_seq, d)
    print(f"URL-number plan: {num_seq}")
    print("Per-word encoding:")
    for w in message.lower().split():
        import re
        w = re.sub(r"[^a-z']", "", w)
        if w in d["word_to_code"]:
            print(f"    {w:<10} -> {d['word_to_code'][w]}")
    print(f"\nThe client now issues {len(url_seq)} ordinary HTTP GETs, in order:")
    for x, u in zip(num_seq, url_seq):
        print(f"    GET {u}   (url#{x})")

    # ---- NETWORK / LOG ----
    print("\n" + "=" * 68)
    print("SERVER ACCESS LOG  (sender requests + innocent noise, interleaved)")
    print("=" * 68)
    log = build_noisy_log(url_seq, urls)
    for ip, u in log:
        marker = "  <== sender" if ip == SENDER_IP else ""
        print(f"    {ip:<15} GET {u}{marker}")

    # ---- RECEIVER ----
    print("\n" + "=" * 68)
    print("RECEIVER  (reads the log, filters by sender IP, decodes)")
    print("=" * 68)
    observed_urls = [u for ip, u in log if ip == SENDER_IP]   # order preserved
    observed_nums = urls_to_numbers(observed_urls, d)
    recovered = decode_numbers(observed_nums, d)
    print(f"Observed url#s : {observed_nums}")
    print(f"Recovered msg  : {recovered!r}")
    print()
    print("MATCH" if recovered == " ".join(
        __import__("re").findall(r"[a-z']+", message.lower())
    ) else "MISMATCH")


if __name__ == "__main__":
    main()