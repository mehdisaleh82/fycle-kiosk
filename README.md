# Fycle kiosk

A small static web site listing recent press articles by topic, rebuilt once
a day from the public feeds of a few media and published with GitHub Pages.

- `build_kiosk.py` reads the feeds, sorts the articles and writes the pages.
  Standard library only.
- `test_kiosk.py` checks the sorting.

The pages carry no script and no tracker, and are not indexed. Each article
links to its publisher's site; nothing of the articles is copied beyond the
title and the thumbnail the feed offers.
