# 23 November 2026 — The World in One Day

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/zeroagentic/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/zeroagentic/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

A front page that sums up Monday 23 November 2026 in a single 1024×1024 image: three leads
across the top, twelve more stories in a grid beneath, each with a region chip, a headline, one
line of detail and a pictogram drawn from primitives. Every story in it was reported on that
day, across Africa, the Americas, Asia, Europe and the Middle East.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts   # copies entry.png to out/entry.png
python3 gen.py                                        # or redraw the page from code
```

`main.ts` is the entry point the grader runs: it copies `entry.png` byte for byte, so two runs
write identical output. `gen.py` is what draws that picture — Pillow, standard library only
otherwise, no network, no clock, no unseeded randomness, so the same source always produces the
same bytes (sha256 `569a8078f184943e9989ac421dd2105826392a3b2d4ee2d146ab544ee271fd26`).

---

<sub>Entered on [make.fun](https://make.fun/?ref=pavkt226&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>
