---
description: Notionからエクスポートした記事をAstroブログに変換する
---

# Notion記事の変換ワークフロー

// turbo-all

## 前提条件
- Python3 がインストールされていること
- `notion_export/Article/` 配下にNotionエクスポートデータが配置されていること
- Node.js と npm がインストールされていること（`npm install` 済み）

## 手順

### 1. Notionエクスポートデータの配置
Notionから「Markdown & CSV」形式でエクスポートしたZIPを展開し、以下の構造で配置する：
```
notion_export/Article/
├── Work/          # Work記事のMDファイル + 画像フォルダ
├── Life/          # Life記事のMDファイル + 画像フォルダ  
├── Work *.csv     # Work記事の順序CSV
└── Life *.csv     # Life記事の順序CSV
```

### 2. 変換スクリプトの実行
```bash
python3 scripts/convert_notion.py
```
44件の記事が変換され、以下が生成される：
- `src/content/blog/` に記事MDファイル
- `public/images/{slug}/` に画像ファイル

### 3. ローカルで確認
```bash
npm run dev
```
http://localhost:4321 でサイトを確認。

### 4. ビルド確認
```bash
npx astro build
```
エラーが0件であることを確認。

### 5. コミット & プッシュ
```bash
git add -A
git commit -m "update articles"
git push origin main
```
Cloudflare Pagesが自動デプロイする。

## トラブルシューティング

### 画像が表示されない
- `.heic` 画像は変換スクリプトで自動的にJPEGに変換される
- 画像ファイル名にスペースがある場合はURLエンコード（`%20`）される
- `public/images/{slug}/` に画像が存在するか確認

### 太字が壊れている
- `fix_bold_fullwidth_chars` 関数が自動修正する
- 正規表現の `[^*\n]` で改行またぎを防止（重要）
- 修正後は `npx astro build` でエラーがないか確認

### h2の下線が二重になる
- `remove_hr_after_headings` 関数がh2直後の `---` を自動除去する
- CSSの `border-bottom` との重複を防止
