# Scripts

One-off or reusable research scripts live here.

## gov.cn XXGK

`govcn_xxgk_crawler.py` is the command entry point for the central gov.cn XXGK
crawler. Prefer the `just` recipes at the repository root:

```bash
just govcn-xxgk-cache-pilot
just govcn-xxgk-live-full
just govcn-xxgk-all-probe
just govcn-xxgk-all-full
```

See `docs/govcn-xxgk-crawler.md` before changing query configs or running broad
live collection.
