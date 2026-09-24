# Pre-registration — Layer 2: AAA Statcast translated to the MLB scale

Frozen: 2026-09-24 (JST), after two pre-freeze audits; md5 recorded in the project notes. Builds on PREREG_pillar1.md (md5 77977d43…) and its two amendments. Every definition not restated here is inherited unchanged.

## 0. What has and has not been looked at
- **Pillar 1 has been run on 2016–2025 arrivals and its results are known.** Both primaries (B vs A) were null. B vs C was also non-significant, though its point estimates favoured B (dBC 0.0062 batters / 0.0010 pitchers). Pillar 1 §7 already registers B vs C and B vs A on 2026–27 arrivals for MLB-only measures. **The primaries below are chosen because of the coverage question (§1), not because of those point estimates.** B vs A on the new sample stays a secondary. This choice is stated here because it was made after the Pillar 1 results were seen.
- The 2026 MLB-only predictions are frozen (pred26_*.csv). No 2026 NPB statistic has been read.
- Per-player AAA files for 2024–25 arrivals (aaa/*.csv) were used only to count coverage.
- League-wide AAA and MLB pitch-level data for 2023–2025 (aaa_lg/, fetch_lg.py) are used only for the translation in §3, which uses no NPB data.

## 1. Question
Many foreign arrivals have little MLB time but a full AAA season. (a) For arrivals who reach the entry threshold **only when AAA is added** (fewer than 150 MLB PA/BF), does the combined measure predict their first NPB season better than the constant floor? (b) For arrivals who meet the threshold either way, does adding translated AAA keep the MLB-only accuracy (non-inferiority)?

## 2. AAA data
- Source: Savant `statcast-search-minors/csv` with `minors=true&hfLevel=AAA|`. Without that parameter the endpoint silently returns MLB. **Only rows with `game_type == "R"` are used**, as an explicit filter; the per-player files include W and C rows.
- AAA seasons **2023 and later**. The Savant minors search page text, read 2026-09-24, says 2022 tracking covers the Pacific Coast League and Charlotte home games only, so 2022 is excluded.
- Every A and B measure of PREREG_pillar1 §4 is computed on AAA with the same code (`mlb_features`, generalised to take a data frame). That includes the PA row set, the pitch sets and the imputed-launch rule. The imputed-launch rule is harmless here: no default pair recurs in AAA.
- The AAA strike-zone environment (automated ball-strike systems in 2023–2025) changed between and within seasons. δ is estimated per season; within-season changes are not modelled. K%, BB%, chase and CSW are flagged as zone-sensitive in every report.

## 3. Translation to the MLB scale (uses no NPB data)
- **Level-specific measure parts.** Each measure is a ratio num/den with its own denominator:
  - PA/BF for wOBA, xwOBA, K, BB, HR, barrels, K−BB and the FIP numerator;
  - swings for whiff;
  - out-of-zone pitches for chase;
  - non-excluded pitches for CSW.
- **Pairs.** For each season s ∈ {2023, 2024, 2025}, role r and AAA league g, take players with **≥50 PA/BF at both levels in season s** and the same role at both levels.
  - Roles are: batter; starting pitcher (`start_share` ≥ 0.5); relief pitcher (`start_share` < 0.5).
  - A batter's AAA team on a row is `away_team` if `inning_topbot == "Top"`, otherwise `home_team`; for pitchers it is the reverse. A player's AAA league (PCL or IL) is the league of the team where he had the most PA/BF that season. The team-to-league map comes from MLB statsapi (sportId 11; 20 IL and 10 PCL teams in 2023–25).
  - The 50-PA floor removes most MLB veterans on short rehab stints; no other rehab rule is applied.
- **Offset.** δ(m, s, r, g) = Σ wᵢ·(mᵢ,MLB − mᵢ,AAA) / Σ wᵢ, where wᵢ is the harmonic mean of the player's two denominators for measure m. The translation is additive.
- **Reported:** δ with player-bootstrap SE (2,000 draws, seed 20260924), the number of pairs and the slope of mᵢ,MLB on mᵢ,AAA (a diagnostic; noise alone pushes it below 1). δ is also reported separately for pairs whose first appearance that season was in MLB (demotion-first) and in AAA (call-up-first). The direction of selection bias is unknown and is not corrected.
- **Thin cells.** A (m, s, r, g) cell needs ≥20 pairs. If it has fewer:
  - first pool leagues, giving (m, s, r);
  - then pool SP and RP into one pitcher role, giving (m, s);
  - then pool seasons 2023–2025, giving (m).
  The level used is reported for every cell.
- **Later seasons.** AAA season 2026 uses δ(2026), estimated from 2026 AAA–MLB pairs (no NPB data) before the 2027 freeze. MLB introduced an ABS challenge system in 2026, and CSW is zone-sensitive. Every later AAA season uses its own δ, estimated the same way before the freeze that uses it.

## 4. Combined measure
For each player and measure m:

    combined = (num_MLB + den_AAA·(num_AAA/den_AAA + δ̄)) / (den_MLB + den_AAA)

- num and den are summed over MLB seasons 2015…(arrival−1) and AAA seasons 2023…(arrival−1).
- δ̄ is the mean of δ(m, s, r, g) over the player's AAA (season, league, role) segments, weighted by each segment's den_AAA for measure m.
- With no AAA seasons, combined equals the Pillar 1 value exactly.
- **Entry: pooled PA/BF (MLB + AAA) ≥ 150.**
- An **AAA-only entrant** is a player who meets this threshold but has fewer than 150 MLB PA/BF.
- Role for the pitcher δ uses the player's own `start_share` at that level and season.

## 5. Samples and the single frozen model
- **Training:** 2016–2025 arrivals meeting the §4 entry and the Pillar 1 outcome cut (≥100 NPB PA / ≥30 IP; trades summed by `key_npb`). For arrivals up to 2023 this is identical to Pillar 1.
- **One model is frozen:** C, A and B are fitted once on this training sample and used for every held-out season. There is no refit with held-out arrivals.
- **Freeze timing:**
  - 2026 combined predictions are frozen, with an md5, as soon as δ(2023–2025) exist and before any final 2026 NPB statistic is read.
  - For 2027 and later, predictions are frozen **before the first NPB regular-season game** of that season. They cover every foreign player on that season's rosters who has no NPB first-team season before it. Those who then appear become that season's arrivals.
- **Held-out:**
  - 2026 arrivals (r26_links.csv) and 2027 arrivals, identified by the same procedure.
  - The same NPB outcome cut applies.
  - Expected size: the 2024–25 arrivals had 4 batters and 2 pitchers who entered only through AAA and passed the outcome cut.

## 6. Tests
- **Co-primary (a): AAA-only held-out entrants, B vs C,** for batters (Y1 OPS_rel) and pitchers (P1 K−BB%). Δ = MAE_C − MAE_B.
  - Player bootstrap (2,000 draws, seed 20260924); one-sided p = share of (Δ* − Δ̂) ≥ Δ̂. Holm over the two roles, α = 0.05. Also reported as an estimate with a 95% percentile CI.
  - **Minimum n:** a role is tested only once its cumulative held-out AAA-only entrants who pass the outcome cut reach **≥10**. The test runs once, at the first season end at which the count reaches 10, whatever the results look like. Before that, results are reported descriptively each season.
- **Co-primary (b): non-inferiority** on held-out players who are entrants under both definitions. D = MAE(combined B) − MAE(MLB-only B).
  - **Comparator:** the frozen pred26_coef.csv coefficients applied to each held-out season's MLB-only features, with no refit. This clarifies PREREG_pillar1 §7 for 2027 and later: "same procedure" is read as no refit, and a Pillar 1 amendment records this at the freeze.
  - D compares the two deployed systems, which differ in both features and training rows. A sensitivity applies the pred26 coefficients to the combined features, isolating the change in features.
  - Paired player bootstrap (the same draws for both systems). **Non-inferior if the 97.5th percentile of D is below the margin, 0.5 × the Pillar 1 dBC: 0.0031 (Y1), 0.0005 (P1).** Tested once, when the both-defined held-out n per role first reaches ≥10.
- **Joint reading:** "AAA adds usable coverage" is stated for a role only if (a) rejects for that role **and** (b) is non-inferior for that role. Each co-primary is also reported separately.
- **Secondary** (unadjusted, labelled secondary):
  - B vs A and A vs C on all held-out entrants;
  - Y2–Y4 and P2–P3;
  - the Amendment-2 sensitivity;
  - a **reliability-shrunk** variant for AAA-only entrants. The translated AAA part of each measure is shrunk toward that measure's mean of combined values over training entrants, by the factor den_AAA/(den_AAA + k). k is estimated per measure as the denominator at which split-half reliability (odd/even PA, or odd/even pitches for pitch-denominator measures, Spearman–Brown corrected) equals 0.5, using 2023–2025 AAA data only.
- A null is recorded as a null for this n, not as evidence of no effect.

## 7. Not done
- No change to the translation, pooling, entry, model or tests after any held-out NPB statistic is read.
- No other translation form (multiplicative, regression-based, aging-adjusted) is used for the primaries. Any such variant gets its own registration before any held-out outcome is read.
