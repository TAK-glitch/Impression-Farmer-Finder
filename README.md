# インプレゾンビ判定ツール

X APIで取得したリプライと投稿者情報をもとに、インプレゾンビ疑いの投稿を「晴れ・曇り・雨」の三段階で判定するPythonツールです。

## 概要

このツールは、Xのリプライ欄に出現する低品質な収益化目的リプライを検出するために作成しました。

まずPythonのルールベース判定で一次判定を行い、判断が難しい境界例のみGPT APIによる二次判定に回します。

全件をGPT APIに送信するのではなく、Pythonで処理できるものはPythonで処理し、文脈判断が必要なものだけGPTに任せる構成です。

## 主な機能

- X APIによるリプライ取得
- pagination_token による複数ページ取得
- tweet_id による重複排除
- tweet/user ペア化
- Pythonルールベースによる一次判定
- 晴れ / 曇り / 雨 の三段階分類
- GPT APIによる境界例の二次判定
- 判定結果のtxt保存

## ディレクトリ構成

```text
src/
  main.py              # 全体実行・設定管理・表示・保存
  reply_collector.py   # X API取得
  zombie_score.py      # Python一次判定
  gpt_judge.py         # GPT二次判定
　Pi_start.py          # API接続テスト用
