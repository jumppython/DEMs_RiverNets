# ダム所在推計検索 前期版

## 概要

ダム名から、水系名・河川名・都道府県名を検索するための SQLite + Python 前期版です。

## ディレクトリ

```text
data/raw/          取得したHTMLなどの原本
data/processed/    HTMLテーブル抽出CSVなど
db/                SQLite DB
scripts/           DB作成・取込・検索スクリプト
outputs/           検索結果など
docs/              設計メモ
```

## DB 初期化

```powershell
C:\Users\jumpp\miniconda3\envs\geocode\python.exe scripts\init_db.py
```

## Webデータ取得・取込

```powershell
C:\Users\jumpp\miniconda3\envs\geocode\python.exe scripts\import_web_sources.py
```

まずHTMLだけ保存したい場合:

```powershell
C:\Users\jumpp\miniconda3\envs\geocode\python.exe scripts\import_web_sources.py --fetch-only
```

## 検索

```powershell
C:\Users\jumpp\miniconda3\envs\geocode\python.exe scripts\search_dam.py ダム名
```

例:

```powershell
C:\Users\jumpp\miniconda3\envs\geocode\python.exe scripts\search_dam.py 草木
```

## CSVからの投入

自動取得で不足するデータは、次の形式のCSVで投入できます。

```text
dam_name,river_system_name,river_name,prefecture,lat,lon
草木ダム,利根川水系,渡良瀬川,群馬県,36.525,139.316
```

テンプレート: `data/processed/dam_import_template.csv`

投入例:

```powershell
C:\Users\jumpp\miniconda3\envs\geocode\python.exe scripts\import_csv.py data\processed\dam_import_template.csv --source-name sample
```

## 主なテーブル

- `prefectures`: 都道府県マスタ
- `river_systems`: 水系
- `rivers`: 河川
- `dams`: ダム
- `dam_source_records`: 取得元の原始記録
- `dam_river_matches`: ダム・河川対応関係と信頼度

## 注意

現段階は前期版です。WebページのHTML構造により自動取込件数が少ない可能性があります。その場合でも `data/raw/` と `data/processed/` に保存された内容を確認し、列名マッピングを追加して取込精度を改善できます。
