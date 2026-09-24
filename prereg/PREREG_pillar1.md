# Pre-registration — Pillar 1: does MLB process data predict a foreign player's first NPB season better than MLB results?

Frozen: 2026-09-24 (JST), after two pre-freeze audits and before any predictor–outcome association has been computed.
Workspace: RPi5 `~/claude-scratch/npbmlb/`. The md5 of this file is recorded in the project notes at freeze time.

## 0. What has and has not been looked at (honest disclosure)
- NPB first-season stat lines (OPS, ERA, PA, IP…) are already in `links.csv` and individual rows were printed while linking IDs. **No correlation, regression, or error comparison between any MLB variable and any NPB outcome has been computed.**
- Sample sizes by predictor availability were counted (`size_win.py`), and for coverage purposes the counts were split by NPB playing time (≥100 PA / ≥30 IP). Nothing else.

## 1. Question
For foreign players whose first NPB season is 2016–2025, do MLB **process** measures (Statcast: contact quality, swing decisions, whiff) predict that first NPB season better than the matching MLB **result** measures? Each process measure is paired in advance with the result measure it is meant to beat (§4).

## 2. Sample
- Players: rows of `links.csv` (Chadwick `key_npb` → npb.jp page → (name, year, team) match; 303 checked, 0 wrong matches found). First NPB season = the first year on the player's npb.jp career page.
- Predictor window: **every MLB regular season from 2015 through (first NPB year − 1)**, pooled. Entry requires **≥150 MLB PA (batters) / ≥150 MLB batters faced (pitchers)** in that window, counted from the same pitch-level pull as the predictors (§4). The expected n below was counted from `statsapi_*` and may shift slightly.
- **Primary outcome sample**: NPB first season ≥100 PA (batters) / ≥30 IP (pitchers). Expected n ≈ 49 batters and 63 pitchers.
- **This cut is selection on the outcome** (players dropped early vanish). This is addressed with two pre-specified checks: (a) sensitivity at ≥50 PA / ≥15 IP; (b) the outcome S1 in §3, which is defined for every entrant regardless of NPB playing time (expected n ≈ 64 / 96).
- Two-way players and position players who pitch are analysed only in their NPB role (`kind` in `links.csv`).
- **Mid-season trades**: a player traded within NPB has one row per team (`links.csv` 312 rows / 311 players; the NPB season CSVs have 38 hitter and 39 pitcher duplicate name-year rows). Counting stats are **summed by (`key_npb`, year)** before any cut or outcome is computed (IP converted from thirds first). Katakana names are never used as join keys (they collide).
- PA / BF totals of the MLB window are reported by arrival year (a 2016 arrival has at most one Statcast season, a 2025 arrival up to ten).

## 3. Outcomes (NPB first season; all from npb.jp season lines)
Batters
- **Y1 (primary): OPS_rel** = player OPS / league OPS of the same year. OBP (player and league) = Σ(H+BB+HBP) ÷ Σ(PA−SH) (the CSV has no SF column; this reproduces the published OBP to within 0.005, while ÷PA misses by up to 0.052). SLG = Σ(SLG·AB) ÷ ΣAB (no TB column). League = **all non-pitcher hitters** in `npb_hitters_2015_2025.csv` that year (both leagues; pitchers' own batting is not in the file).
- Y2: K% = SO / PA. Y3: BB% = BB / PA (NPB BB includes intentional walks — the CSV has no IBB column; the MLB side excludes them. This asymmetry is stated, not corrected). Y4: HR / PA.

Pitchers
- **P1 (primary): K−BB%** = (SO − BB) / BF.
- P2: ERA_rel = player ERA − league ERA of the same year (league ERA = 9·ΣER / ΣIP over all NPB pitchers that year, from `npb_pitchers_2015_2025.csv`; IP converted from NPB thirds notation before summing).
- P3: HR / BF.

Uncensored
- **S1: reached the playing-time cut** (≥100 PA / ≥30 IP) in the first NPB season, a yes/no outcome for every entrant.

## 4. Predictors — each outcome has exactly one pre-paired A (result) and B (process) measure
All values are pooled over the predictor window (sums of numerators over sums of denominators; never averages of seasonal rates).

| Outcome | A = MLB result | B = MLB process |
|---|---|---|
| Y1 OPS_rel | wOBA = Σ`woba_value` ÷ Σ`woba_denom` | xwOBA = same, with `estimated_woba_using_speedangle` replacing `woba_value` on batted balls |
| Y2 K% | K% = strikeouts ÷ PA | whiff% = swinging strikes ÷ swings |
| Y3 BB% | BB% = walks ÷ PA | chase% = swings on pitches in zones 11–14 ÷ pitches in zones 11–14 |
| Y4 HR/PA | HR ÷ PA | barrels ÷ PA (`launch_speed_angle == 6`) |
| P1 K−BB% | (K − BB) ÷ BF | CSW% = (called strikes + swinging strikes) ÷ pitches |
| P2 ERA_rel | FIP numerator per batter = (13·HR + 3·(BB+HBP) − 2·K) ÷ BF | xwOBA allowed (as in Y1) |
| P3 HR/BF | HR ÷ BF | barrels allowed ÷ BF |
| S1 | the A of Y1 (bat) / P1 (pit) | the B of Y1 (bat) / P1 (pit) |

**Every A and B is computed from the same per-player pitch-level pull** (the HF season tables are not used: `statsapi_batting` has ~40% fewer rows from 2022 and 19% missing `woba`).

PA row set (one set, used identically by every A and B): rows whose `events` is in {single, double, triple, home_run, walk, hit_by_pitch, strikeout, strikeout_double_play, field_out, force_out, grounded_into_double_play, double_play, triple_play, fielders_choice, fielders_choice_out, field_error, sac_fly, sac_fly_double_play, other_out}. Excluded: intent_walk, sac_bunt, sac_bunt_double_play, catcher_interf, truncated_pa. PA = number of rows in the set; BF likewise for pitchers.
- wOBA (A) = mean of `woba_value` over the set. (Σ`woba_value`/Σ`woba_denom` is **not** used: `woba_denom` is empty on some batted balls without launch data while `woba_value` is not, and non-zero `woba_value` appears on intent_walk / sac_bunt.)
- xwOBA (B) = the same mean, except that on batted balls (`type == "X"`) with valid launch data `woba_value` is replaced by `estimated_woba_using_speedangle`. So A and B differ **only on batted balls**. Batted balls without valid launch data keep `woba_value`; the share of such fallbacks is reported by arrival year.
- **Valid launch data** = `launch_speed` and `launch_angle` present and not one of the four imputed default pairs 82.9/−21, 80.0/69, 90.3/−17, 89.2/39. Counted on the 263 batter files fetched so far, these four pairs are 684 of 6,887 batted balls in 2015 and 409–677 per season through 2019, and no exact pair occurs more than 3 times in any season from 2020. Batted balls with valid launch data but an empty `estimated_woba_using_speedangle` also keep `woba_value`.
- `woba_value` follows Savant's convention (non-zero on strikeouts where the batter reached on a wild pitch or passed ball, and on field_error / fielders_choice). This affects A and B identically.
- Every file is checked to contain only `game_type == "R"`, the requested player and the requested season.
- K = strikeout + strikeout_double_play; BB = walk; HBP = hit_by_pitch; HR = home_run.
- Barrels = rows with valid launch data and `launch_speed_angle == 6`.

Pitch sets (Savant `description`):
- swinging strike = swinging_strike, swinging_strike_blocked, foul_tip, missed_bunt, bunt_foul_tip, swinging_pitchout;
- swing = swinging strike + foul, foul_bunt, foul_pitchout, and any description starting with hit_into_play;
- called strike = called_strike;
- pitch denominators (CSW, chase) exclude intent_ball, pitchout, automatic_ball, automatic_strike. Zones 11–14 are the out-of-zone codes (only 1–9 and 11–14 occur). Pitches with empty `zone` count in the CSW denominator and are excluded from chase.
- ball, blocked_ball and hit_by_pitch are non-swings. `hit_into_play` rows attached to catcher_interf count as swings, although that PA is outside the PA set.
- B for Y1 is speed-angle xwOBA as defined above, not Savant's leaderboard xwOBA.

## 5. Models and scoring
- Three models per outcome: **C** constant (training-fold mean), **A** OLS y ~ A, **B** OLS y ~ B. Secondary: **AB** OLS y ~ A + B. S1 uses logistic regression and is scored by AUC instead of MAE.
- **Cross-validation: leave one arrival year out** over 2016–2025 (10 folds). Every player's error comes from a model that never saw their arrival year.
- Score: per-player absolute error; unweighted mean (primary), NPB-PA/BF-weighted mean (sensitivity).
- No MLB run-environment or park normalisation is applied to A or B (A and B are treated identically, so the comparison is not biased by it; the omission is stated).

## 6. Hypotheses and tests
- **H1 (batters, Y1)** and **H2 (pitchers, P1)**: B has lower MAE than A. Statistic Δ = MAE_A − MAE_B.
- **Primary inference: player-level bootstrap of the whole procedure** — resample players with replacement (2,000 resamples, seed 20260924), re-run the leave-one-arrival-year-out CV on each resample, recompute Δ. One-sided p = share of resamples with (Δ* − Δ̂) ≥ Δ̂ (bootstrap null centred on the observed Δ̂). A player drawn more than once keeps his single arrival year, so every copy sits in the same test fold (no leakage). A fold with no players in a resample is skipped. S1's AUC is computed over the pooled out-of-fold predictions; a resample in which a training fold has only one S1 class is dropped, and the number dropped is reported. **Holm over H1 and H2, family α = 0.05.** (The CV errors are not independent across players, so a sign-flip test is reported only as a secondary.)
- Floor rule: each primary B is also compared with C by the same bootstrap at one-sided α = 0.05 (not multiplicity-adjusted); **a B that beats A but not C is not reported as predictive.**
- Secondary (unadjusted p, labelled secondary, never promoted to a headline): Y2–Y4, P2–P3; AB; sign-flip permutation (20,000); ≥50 PA / ≥15 IP sensitivity; weighted MAE; **windows restricted to 2020+ MLB seasons** (the imputed launch pairs are present 2015–2019; the number of arrivals this drops is reported); for pitchers, **B + MLB starter share** (appearances = distinct `game_pk`; started = his first pitch of that game is in inning 1 with 0 outs, bases empty and `pitch_number == 1`; openers count as starters; starter share = started ÷ appearances) and A + starter share (role mix is uncontrolled otherwise; the NPB CSV has no GS column).
- **S1**: ΔAUC = AUC_B − AUC_A from the same bootstrap. Caveat: COVID-delayed arrivals in 2020–21 push S1 toward "missed".
- Power is low (n ≈ 49 / 63). A null here is recorded as a null for this n, not as evidence of no effect.

## 7. Held-out confirmations (not yet observable)
- **2026 arrivals**: fit all models on 2016–2025, write the frozen coefficients and every 2026 arrival's prediction to a file with an md5 **before** pulling final 2026 NPB stats (after the NPB regular season ends). Same statistics as §6.
- **2027 arrivals**: same procedure after the 2027 season.

## 8. Layer 2 (AAA, 2024+ arrivals) — descriptive only in this registration
AAA Statcast (Savant minors endpoint, `minors=true&hfLevel=AAA|` is required) covers most 2024–2025 arrivals. n is ≈15 / 20, so no test is registered here. A later registration will define how AAA and MLB values are placed on one scale before any AAA-based association is computed.

## 9. Things that will not be done
- No change to outcomes, pairings, windows, thresholds or the test after the first association is computed. Any deviation is written in an AMENDMENT section with its timestamp and reason, and the original analysis is still reported.
- No searching over feature combinations for the primaries.
