# Amendments to PREREG_pillar1.md (md5 77977d43ac5c315da48710ef6218a7c5)

Written before the first run of ana1.py. No MLB–NPB association has been computed. Source: a code audit of ana1.py, run before its first execution. None of these changes a definition, sample, or test.

1. §2 says katakana names are never join keys. In practice, `links.csv` rows are joined to the NPB season CSVs on (player, team, year) as written in those same CSVs. This key is unique in both files (asserted). Cross-player aggregation still uses `key_npb` only.
2. §4 gives the reason for not using `statsapi_batting` as "~40% fewer rows from 2022". The row drop coincides with the universal DH (pitchers stop batting), so it is not a coverage defect. The decision (one pitch-level source for A and B) is unchanged.
3. §3 says the OBP formula reproduces published OBP "to within 0.005". It does for PA ≥ 100, but two low-PA rows differ by up to 0.0137. The formula is unchanged.
4. Implementation choices not spelled out in §6: in the 2020+ window, the ≥150 entry is re-counted inside that window, and a model is run only if ≥3 arrival years remain. Every bootstrap uses the same seed.
