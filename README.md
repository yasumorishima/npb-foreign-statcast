# npb-foreign-statcast

来日外国人選手の **NPB 初年度成績** を、MLB 時代の Statcast の **過程指標**（xwOBA・空振り率・ボール球スイング率・バレル・CSW%）が、MLB の **結果指標**（wOBA・K%・BB%・本塁打率・K−BB%）より良く予測するかを検証する研究。

- すべての解析は **事前登録してから 1 回だけ走らせる**。定義は結果を見る前に凍結し（md5 を記録）、直す場合は走る前に `AMENDMENTS*.md` に書く。
- 解析コードも、走らせる前に独立レビューを通す。
- 将来の NPB ホークアイ（NPB+）データ公開を見込み、NPB+ が表示している項目（球速・回転数・打球速度・角度など）で組める研究を MLB データで先に作る方針。

## 現在の結果

### 柱 1：MLB のみ（2016〜2025 来日・事前登録 `prereg/PREREG_pillar1.md`）

1 回だけ走らせた結果（`results/RESULTS_pillar1_run1.txt`）：

| | 定数（平均） | MLB 結果指標 | MLB 過程指標 | 片側 p（過程＞結果） |
|---|---|---|---|---|
| 打者 OPS（リーグ比）n=49 | 0.1309 | wOBA 0.1304 | xwOBA **0.1247** | 0.26 |
| 投手 K−BB% n=63 | 0.0468 | K−BB% 0.0462 | CSW% 0.0457 | 0.29 |

（数値は到来年を 1 年ずつ抜いた交差検証の平均絶対誤差。小さいほど良い）

- **主仮説は 2 本とも有意差なし**。打者は過程指標の方向だが、定数予測にも有意には勝たない。
- **MLB の wOBA は NPB 初年度 OPS の予測にほとんど役立たない**（定数 0.1309 に対し 0.1304）。
- 副次（補正なし）：**三振率と四球率は MLB の値が NPB に持ち越される**（K%：定数 0.0456 → MLB K% 0.0377）。長打・総合打撃は持ち越されない。
- 「出場機会に達したか」の AUC は、交差検証の作り方による人工物（予測子なしでも 0.23）で読めないことが走行後の診断で分かった。事前登録どおりの数字と診断を両方残している。

### 2026 来日組の予測（凍結済み・未採点）

NPB 2026 の成績を 1 つも読まずに、打者 6 人・投手 16 人の予測を凍結した（`results/pred26_*.csv`、md5 は `MD5SUMS_results.txt`）。**NPB 2026 レギュラーシーズン終了後に最終成績で採点**する。打者 6 人では検定にならないので、主眼は投手。

### 2 層：AAA を MLB の尺度へ換算して足す（事前登録 `prereg/PREREG_layer2.md`）

MLB の出場が少なく AAA で多く出ていた選手を扱うため、同じ年に AAA と MLB の両方に出た選手の対から換算量を出して、AAA の値を MLB の尺度に直す。事前登録と修正 2 本は凍結済み。リーグ全体の 2023〜2025 のデータを取得中で、終わり次第、換算量の計算と AAA 込みの 2026 予測の凍結まで自動で進む（`src/l2_chain.sh`）。

## 時刻についての正直な注記

- 事前登録ファイルは作業機（RPi5）上で凍結し、その時点の md5 を記録していた。**このリポジトリへの初回 commit は柱 1 の走行後**なので、柱 1 について「結果を見る前に決めた」ことを公開の commit 時刻では証明できない（証明できるのは md5 の一致まで）。
- **2026 予測は NPB 2026 シーズン終了前にこのリポジトリへ commit している**。こちらは commit 時刻が採点前の凍結の証拠になる。

## ファイル構成

| パス | 内容 |
|---|---|
| `prereg/` | 事前登録と修正記録（凍結時の md5 は `MD5SUMS_prereg.txt`） |
| `results/` | 柱 1 の結果、2026 の凍結予測と係数 |
| `src/link_foreign.py` ほか | Chadwick Register の `key_npb` と npb.jp 選手ページで NPB と MLB の ID を突き合わせる（誤結合 0 件を確認） |
| `src/fetch_mlb*.py` / `src/fetch_lg.py` | Baseball Savant から投球単位データを取得（選手別・リーグ全体の日別） |
| `src/ana1.py` | 柱 1 の解析（凍結した事前登録の md5 を起動時に確認） |
| `src/r26_*.py` / `src/pred26.py` | 2026 来日組の同定と予測の凍結 |
| `src/l2_*.py` | 2 層（AAA 換算・合成値・2026 予測） |

生データ（投球単位の CSV、NPB の成績表、npb.jp のページ）は含めていない。各スクリプトで取得し直せる。

## データの出典

- MLB / AAA 投球単位データ：Baseball Savant（MLB Advanced Media）
- MLB 選手のシーズン成績（取得対象の選定）：MLB Stats API（HF データセット [yasumorishima/mlb-stats](https://huggingface.co/datasets/yasumorishima/mlb-stats) 経由）
- NPB 成績：baseball-data.com、npb.jp（日本野球機構）
- 選手 ID の対応：Chadwick Baseball Bureau の Register（Open Data Commons Attribution License）

## 関連

- [npb-prediction](https://github.com/yasumorishima/npb-prediction)：NPB 選手・チーム成績予測
- [mlb-data-pipeline](https://github.com/yasumorishima/mlb-data-pipeline)：MLB データ基盤
- [savant-extras](https://pypi.org/project/savant-extras/)：Baseball Savant の追加データ取得
