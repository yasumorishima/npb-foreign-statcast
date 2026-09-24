# Amendment 1 to PREREG_pillar1_S1v2.md (md5 f9754643bbd42af806af25b125c3c58c)

Written 2026-09-24 23:10 JST, before the first run of s1v2.py on real data. Source: an independent review of s1v2.py (run only on synthetic data). No statistic of the prereg has been computed. None of these changes a definition or a test.

1. Sens-b: lbfgs does not flag separation (in a synthetic test a single-class year's dummy diverged to ~46 with no ConvergenceWarning). In addition to the warning count, the run reports the number of LOYO folds whose training data contain an arrival year with a single class. This count depends only on the outcome and the years.
2. Integrity gate: before computing anything new, the script recomputes the registered pooled S1 AUCs (already public in RESULTS_pillar1_run1.txt) from the regenerated feat_*.csv and asserts bat 0.1796 / 0.2762 and pit 0.5118 / 0.4988 (rounded to 4 decimals). If this fails, the run stops and nothing new is reported.
3. Output labelling only: years/pairs are asserted equal for A and B and printed once as shared; Sens-a gets its own line; Sens-c prints the primary statistic only; the intercept-only = 0.5 property is asserted and labelled as a diagnostic.
4. Environment: the run uses scikit-learn < 1.10 (`penalty=None`, as in ana1.py, is removed in 1.10).
