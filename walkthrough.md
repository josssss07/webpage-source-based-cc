## What the paper wants to achieve 
- A covert channel is a communication path that isn't meant to carry information, used in order to make sure that the existance of the channel is hidden 
- the main goal of a covert channel isn't encryption but to hide the message 
- this paper proposes a covert channel that is built on HTML source of an ordinary webapge. 
- the main advantages over previous HTTP based covert channels are: 
    - impreceptibility 
    - independence from timing 
    - higher bandwidth 

- this channel also removes any need for server-> client communication and has moved it to client-> server 

## How is this achieved: 
- this is achieved via encoding the message in the sequence of URL's from a shared unmodified page

| Number | Meaning | 
| ----- | -----| 
| 0 | start of transmission | 
| 1 | wait (flags a multi URL word) | 
| 2 | end of transmission | 
| 3, n-1 | a word or a shift | 

- The first n-3 words each get a single URL (about → (3)).
- Remaining words use a shift + WAIT + word sequence of three requests (research → (12, 1, 48)). The leading URL is a "shift," the WAIT URL (1) announces "this is a multi-URL word, keep reading," and the third URL picks the word within that shifted block.

## How an Implementation would look: 
- Shared setup (both sides): fetch/agree on one page → parse URLs and words → build the two dictionaries. The sender uses number→URL and word→code; the receiver uses the reverse lookups.
- Sender: take plaintext → look up each word's code → emit the URL-number sequence → issue those URLs as real HTTP GETs (ideally with random jitter between them).
- Receiver: ingest an Apache access.log or a .pcap → filter by the sender's IP → recover the ordered URL list → decode.

## Example Implementation: 
- dummy_site.html — a fake "Northgate Public Library" page: 15 links and a couple of paragraphs of ordinary prose. Nothing is hidden in it; it's a normal page. Parsing yields 15 URLs (3 control + 12 usable) and 140 words → capacity 12 + 12² = 156 words.
- covert_channel.py — the core: HTML parsing, dictionary building, encode_message, and decode_numbers, mirroring the paper's scheme (single-URL and shift+WAIT+word multi-URL encodings).
- demo.py — simulates the whole round trip without touching the network: the sender's GETs get interleaved with innocent traffic from other IPs into a fake access log, and the receiver filters by the sender's IP and decodes.


