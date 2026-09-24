# Amendment 1 to PREREG_layer2.md (md5 8a7305c938eb50d04d319add64746ebe)

Written before any Layer 2 model has been fitted and before any 2026 NPB statistic is read. It records what a pre-run code audit found underspecified or unimplemented. No primary definition changes.

1. **MLB part for players with thin MLB samples.** Per-player MLB files had been fetched only for players with ≥100 statsapi PA/BF, the Pillar 1 entry superset. Layer 2 targets exactly the players below that line, so every season with statsapi PA/BF > 0 is now fetched (91 more player-seasons). The combined-measure code asserts that such a file exists for every training and held-out player-season. This affects no Pillar 1 result, because Pillar 1 entry needs ≥150 PA/BF.
2. **Completeness of the league-wide daily data.**
   - Before aggregating a season: the fetch log has no FAIL line and ends that season with "season done". Every date from 15 Mar to 5 Oct has either a data file or an empty-day marker.
   - The set of `game_pk` values must match the statsapi schedule of completed regular-season games, sportId 1 and 11. MLB must match exactly. For AAA, any unmatched games are listed and at most 1% may be missing.
   - The league-wide AAA sums must also equal the 59 per-player AAA files, restricted to `game_type == "R"`.
3. **Segments.** Each (player, AAA season) has one league, the league of the team where he had the most PA/BF, and one role. All of that season's AAA playing time takes that segment's δ. §4's "segments" means these (player, season) units.
4. **Bootstrap unit.** When seasons are pooled, the δ bootstrap resamples unique players, not player-seasons. A cell still below 20 pairs after full pooling is flagged, not dropped. Ties in first-appearance date are labelled "same_day" in the call-up/demotion split.
5. **Reliability-shrunk secondary (§6), made fully specified.**
   - **k per (measure, role).** Use AAA 2023–2025 player-seasons whose denominator for that measure is ≥100. Split each player-season's rows alternately (odd/even) in the order (game_date, game_pk, at_bat_number) for PA-denominator measures, or (game_date, game_pk, at_bat_number, pitch_number) for pitch-denominator measures. Compute the Pearson correlation r of the two half-rates across player-seasons, and the Spearman–Brown reliability ρ = 2r/(1+r) at the mean full denominator n̄. Under ρ(n) = n/(n+k), k = n̄(1−ρ)/ρ; this is the denominator at which reliability is 0.5.
   - **Shrinking.** For held-out players, the translated AAA part v = num_AAA/den_AAA + δ̄ is replaced by μ + den_AAA/(den_AAA + k)·(v − μ). μ is the unweighted mean of that measure's combined value over training entrants. The combined value is then rebuilt as in §4.
   - **Scoring.** The frozen Layer 2 coefficients are applied to the shrunk features, with no refit. Shrunk predictions are frozen together with the unshrunk ones, before any 2026 NPB statistic is read.
