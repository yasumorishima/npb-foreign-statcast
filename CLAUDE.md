# CLAUDE.md — npb-foreign-statcast

Working rules for Claude Code (cloud or local). This file is the source of truth for this project; the owner's local notes are not visible to cloud sessions.

## What this is
Does MLB/AAA Statcast *process* data (xwOBA, whiff, chase, barrel, CSW%) predict a foreign player's first NPB season better than MLB *result* data (wOBA, K%, BB%, HR rate, K−BB%)? See `README.md` for current results.

## Non-negotiable discipline
1. **Pre-register, then run once.** Definitions go into `prereg/` before any outcome is read. A gap found before a run goes into a new `prereg/AMENDMENTS*.md` *before* the run. Never change code or definitions after seeing results.
2. **Freeze = md5.** Frozen files are listed in `MD5SUMS_prereg.txt` / `MD5SUMS_results.txt`. Every scoring script asserts those md5s first. Never edit a frozen file; never regenerate `results/pred26_*.csv` or `results/layer2/pred26L2_*.csv`.
3. **Commit frozen artifacts here before the event they predict** (commit time is the public proof).
4. Code that produces a result gets an independent review before it runs; review claims are verified against the code/data before being accepted.
5. Report nulls as facts. Write summaries in Japanese.

## Next tasks (in order)
1. **Final 2026 scoring (after the NPB 2026 regular season ends, early October).**
   - Fetch the final npb.jp team pages (`https://npb.jp/bis/2026/stats/idb1_<team>.html`, `idp1_<team>.html`, 12 teams each) into `r26live/` (not committed).
   - Run `src/interim26.py`'s rules unchanged: it expects `pred26_bat.csv`, `pred26_pit.csv`, `l2/pred26L2_*.csv` in the working directory — copy them from `results/` and `results/layer2/` into a scratch dir; the md5 asserts must pass. Change only input paths, never scoring logic.
   - Commit the output under `results/final/` and update the README table (keep the interim table, label it as interim).
2. While waiting: a separate pre-registration replacing the pillar-1 S1 "reached playing time" AUC (the pooled LOYO AUC is an artifact: intercept-only gives 0.23). Candidates: mean of per-year AUC, or year fixed effects. Register before computing.
3. **Before 2027 opening day:** identify 2027 arrivals from rosters (`src/r26_*.py` pattern; left-handed marks `<sup>*</sup>` must be handled), compute δ(2026) from 2026 league-wide AAA/MLB pitch data (`src/fetch_lg.py`, `src/l2_*.py`), predict, freeze and commit **before the first NPB game**.

## Data access (cloud network allowlist needed)
`npb.jp`, `baseballsavant.mlb.com`, `statsapi.mlb.com`, `huggingface.co` (+ `cdn-lfs.huggingface.co`), `baseball-data.com`, `raw.githubusercontent.com` (Chadwick Register).
- Savant minors: must pass `minors=true&hfLevel=AAA|`, otherwise it silently returns MLB data.
- Raw pitch-level data (~1.2 GB: per-player MLB files ~370 MB, league-wide AAA/MLB ~860 MB) is **not** in the repo; re-fetch per session. Do not commit raw data or baseball-data.com tables (credit required; no redistribution of their tables).
- Interim/final NPB outcome rules: OPS_rel with OBP = (H+BB+HBP)/(PA−SH), SLG = TB/AB, league = non-pitcher hitters (a hitter counts as a pitcher only if on the same team's pitching page AND BF ≥ his PA); K−BB% = (SO−BB)/BF; innings cell `53.1` = 53⅓, `+` = 0 outs; strip `*`/`+` name marks.

## Credits (keep in README)
Baseball Savant (MLBAM), MLB Stats API via HF `yasumorishima/mlb-stats`, baseball-data.com, npb.jp, Chadwick Register (ODC-By 1.0).
