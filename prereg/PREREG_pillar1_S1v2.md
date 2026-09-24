# Pre-registration — Pillar 1, S1 replacement: within-year AUC for "reached playing time"

Written 2026-09-24 22:30 JST, before any statistic defined below has been computed. Frozen by md5 in `MD5SUMS_prereg.txt`.
This adds to `PREREG_pillar1.md` (md5 77977d43ac5c315da48710ef6218a7c5); it changes nothing there. The registered pooled S1 numbers stay in `results/RESULTS_pillar1_run1.txt` and keep being reported next to the numbers defined here.

## 0. Why, and what has already been seen (honest disclosure)
- The registered S1 score is an AUC over the pooled leave-one-arrival-year-out (LOYO) predictions. A post-hoc diagnostic (`src/diag_s1.py`) showed that an intercept-only model scores 0.2306 (bat) / 0.3579 (pit) on that metric: the held-out year's base rate is predicted from the other years, so the pooled ranking across years is anti-correlated with the truth. The pooled S1 AUC is therefore not interpretable.
- Already seen: pooled AUC_A / AUC_B = 0.1796 / 0.2762 (bat), 0.5118 / 0.4988 (pit); the intercept-only pooled AUCs above; the reached-cut rate by arrival year (printed by `diag_s1.py`).
- **Not computed by anyone**: any per-year or within-year AUC, any year-fixed-effect fit, or any other association between a predictor and S1 inside a year.
- 2026: the interim scoring (`results/interim/interim26_2026-09-24.txt`, stats as of 9/23) showed how many frozen 2026 arrivals were below the cut at that date (bat 0 of 6, pit 9 of 16). No AUC of the frozen `S1_A` / `S1_B` probabilities has been computed.

## 1. Sample, outcome, predictors, fits — unchanged
- Entrants exactly as in `ana1.py`: rows of `feat_bat.csv` / `feat_pit.csv` (written by `ana1.py`) with `n >= 150`; expected n = 64 bat / 96 pit.
- Outcome `ok100` (bat NPB PA >= 100; pit NPB outs >= 90). Predictors: A = `woba` / `kbb`, B = `xwoba` / `csw`.
- Out-of-fold probabilities come from `logit_oof` in `ana1.py`, copied verbatim (one-predictor unpenalized logistic regression, `max_iter=1000`, LOYO over arrival years 2016–2025). No new fitting choice is made for the primary.

## 2. Primary statistic (S1v2): within-year AUC
For out-of-fold probabilities p, over arrival years y with at least one reached and one missed player:

AUC_w(p) = Σ_y Σ_{i reached in y} Σ_{j missed in y} [ 1(p_i > p_j) + ½·1(p_i = p_j) ] ÷ Σ_y n_reached,y · n_missed,y

Only pairs of players who arrived in the same year are compared. A year with a single class contributes no pairs. Because every player of a held-out year gets his probability from the same fitted model, an intercept-only model scores exactly 0.5, so the base-rate artifact is removed by construction. (A consequence stated in advance: within a year the ranking is the ranking of the predictor, signed by the slope fitted on the other nine years.)

Reported for A and B, bat and pit: AUC_w, number of years contributing, total pairs.

## 3. Tests (secondary, unadjusted, as S1 was registered)
- ΔAUC_w = AUC_w(B) − AUC_w(A). Same centred player bootstrap as `ana1.py` §6: 2,000 resamples, seed 20260924, players resampled with replacement and every copy keeps its arrival year (so copies sit in the same held-out fold), LOYO refit on every resample. One-sided p = share of resamples with (Δ* − Δ̂) ≥ Δ̂.
- Floor: for each of A and B, AUC_w − 0.5 (0.5 is the intercept-only value) with the same bootstrap and the same centred p, one-sided.
- A resample is dropped when a training fold has a single class (as in `ana1.py`) or when no year has both classes; the number dropped is reported. Pairs between two copies of the same player cannot occur (same outcome).
- **Direction rule**: B is reported as better at ranking playing time only if p(ΔAUC_w) ≤ 0.05 **and** p(B floor) ≤ 0.05. These are secondary results and are never promoted to a headline.

## 4. Sensitivities (reported, no inference)
- Sens-a: unweighted mean of per-year AUCs over years with both classes.
- Sens-b: year fixed effects — in each LOYO training fold, fit ok100 ~ x + arrival-year dummies (unpenalized logistic, `max_iter=1000`); score the held-out year by β̂·x (the held-out year has no dummy, so only the slope ranks) and apply AUC_w. A year in which every training player reached (or missed) the cut makes its dummy diverge; the fit is kept as the optimizer returns it and convergence warnings are counted and reported.
- Sens-c: `ok50` (PA >= 50 / outs >= 45) in place of `ok100`, primary statistic only.

## 5. 2026 held-out (descriptive, after the NPB 2026 regular season)
- For the frozen `results/pred26_bat.csv` / `pred26_pit.csv` rows, S1 = final 2026 PA >= 100 / outs >= 90 from the final npb.jp pages, summed over teams, with the parsing rules of `src/interim26.py`. One arrival year, so AUC_w is the ordinary AUC of the frozen `S1_A` / `S1_B`. Reported with n per class; not tested. If a class is empty (expected for batters), it is reported as undefined.

## 6. Things that will not be done
- No other aggregation, weighting, or predictor is added after the first number of §2 is seen. Any gap found before the run goes into a new amendment file before the run.
- The run is done once, by a script that asserts this file's md5 and has passed an independent review.
