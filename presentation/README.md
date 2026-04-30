# Austin RHUG 2026 — companion presentation

Walkthrough deck that pairs with the 17 screen recordings under
`/Users/davidkypuros/Documents/Git_ONLINE/austin_rhug_obs/`.

## Layout

```
presentation/
├── README.md                ← this file
├── project/
│   ├── input.yaml           ← intent (carries the original presentation_harness conventions)
│   └── notes.txt            ← build/ownership notes
└── pptx/
    ├── build_deck.py        ← regenerator (one slide per video + cover + closer)
    └── austin_rhug_2026.pptx← rendered deck (19 slides, 16:9)
```

## Rebuild the deck

The deck uses `python-pptx` from the presentation_harness venv. From this folder:

```sh
/Users/davidkypuros/Documents/Git_ONLINE/presentation_harness/pptx/venv/bin/python \
  presentation/pptx/build_deck.py
```

The script embeds thumbnails directly from `austin_rhug_obs/frames/<n>_<slug>.jpg`,
so chronological order matches the recording order.

## Wiring up YouTube links

After uploading the 17 MP4s in `austin_rhug_obs/mp4/` (the `1_…17_…` filenames
match each slide), open `austin_rhug_2026.pptx` and on each video slide:

1. Right-click the thumbnail → Hyperlink…
2. Paste the YouTube URL.
3. Optionally also hyperlink the "▶ YouTube link" placeholder text and replace
   the placeholder caption with the URL itself.

Embedding is intentionally left manual — the script doesn't fetch URLs.
