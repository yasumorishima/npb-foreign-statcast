# Amendment 2 to PREREG_layer2.md — written 2026-09-24 (JST), before any Layer 2 model is fitted and before any 2026 NPB statistic is read

1. **Per-player AAA files.** Amendment 1 §2 compares against "the 59 per-player AAA files". 13 of them are header-only, because the player had no AAA regular-season pitch that season. For those 13, the check is that the player is absent from the league-wide AAA data. The other 46 must match the league-wide sums exactly.
2. **Upward bias in k (Amendment 1 §5).** Spearman–Brown is applied at the arithmetic mean denominator n̄, while player denominators vary widely. This biases k upward, meaning more shrinkage: a synthetic check gave about 140 against a true value of 107. The rule is kept as registered; the bias is stated here.
3. **Counting pairs for thin cells.** The ≥20-pair rule counts pairs whose denominator for the measure is positive at both levels, not rows.
