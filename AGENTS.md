# tenjimn-site 開発ガイド

個人サイト [tenjimn.com](https://tenjimn.com) のソースコード。Astro + Tailwind CSS で構築。

## プロジェクト構造

```
tenjimn-site/
├── src/
│   ├── content/blog/        # 記事MD（変換スクリプトが生成）
│   ├── pages/
│   │   ├── index.astro      # トップページ
│   │   └── blog/[slug].astro # 記事ページ
│   ├── layouts/Layout.astro  # 共通レイアウト
│   └── styles/global.css
├── public/
│   ├── images/              # 記事画像（変換スクリプトが配置）
│   └── favicon.svg          # ヒツジアイコン
├── notion_export/           # Notionエクスポートデータ（git管理外）
│   └── Article/
│       ├── Work/            # Work記事のMD + 画像
│       ├── Life/            # Life記事のMD + 画像
│       ├── Work *.csv       # Work記事の順序CSV
│       └── Life *.csv       # Life記事の順序CSV
├── scripts/
│   └── convert_notion.py    # 変換スクリプト（git管理外）
└── AGENTS.md                # このファイル
```

## 記事の追加・更新ワークフロー

### 1. Notionで記事を書く
- Article の Work または Life データベースに記事を作成
- 画像はNotion内にアップロード

### 2. Notionからエクスポート
- 「Markdown & CSV」形式でエクスポート
- ダウンロードしたZIPを展開し `notion_export/Article/` 配下に配置
- Work/Life 各フォルダと、順序を決めるCSVファイルが含まれる

### 3. 変換スクリプトを実行
```bash
python3 scripts/convert_notion.py
```
これにより以下が自動実行される：
- `notion_export/Article/Work/*.md` → `src/content/blog/` へ変換
- `notion_export/Article/Life/*.md` → `src/content/blog/` へ変換
- 画像を `public/images/{slug}/` へコピー
- HEIC画像をJPEGに自動変換（macOSのsipsコマンド使用）

### 4. ビルド・確認・デプロイ
```bash
npm run dev          # ローカル確認
npx astro build      # ビルド確認
git add -A && git commit -m "add new article" && git push origin main
```
- Cloudflare Pages が自動デプロイ

## 変換スクリプトの処理内容

`scripts/convert_notion.py` は以下の変換を順番に実行する：

| # | 関数名 | 処理内容 |
|---|--------|---------|
| 1 | `remove_notion_title` | 先頭の `# タイトル` を除去（frontmatterと重複するため） |
| 2 | `convert_notion_html` | `<aside>` などNotionのHTMLタグをMarkdownに変換 |
| 3 | `remove_outline_blocks` | 「📝 Outline」などNotion独自のcalloutブロックを削除 |
| 4 | `remove_callout_icons` | calloutのアイコン行（絵文字だけの引用行）を削除 |
| 5 | `remove_duplicate_bookmark_links` | Notionのbookmark由来の重複リンクを除去 |
| 6 | `fix_bold_fullwidth_chars` | 全角括弧を含む太字の壊れを修復（`**text<strong>` → `<strong>text</strong>`） |
| 7 | `convert_internal_links` | ten-ezo.com のリンクを `/blog/slug` に変換 |
| 8 | `convert_twitter_embeds` | Twitter/XのプレーンURLリンクを公式埋め込みblockquoteに変換 |
| 9 | `remove_hr_after_headings` | h2/h3 直後の `---` を除去（CSSと二重線になるため） |
| 10 | `convert_csv_gallery` | Notion DBの CSVリンクをキャプショングリッドHTMLに変換 |
| 11 | `process_images` | 画像をコピー、パスを書き換え、HEIC→JPEG変換 |

## 既知の注意点

### 太字の壊れパターン
Notionエクスポートで全角文字（括弧、カギ括弧等）の直後の `**` がMarkdownパーサーに認識されない。
`fix_bold_fullwidth_chars` が `<strong>` タグに変換して回避。
**重要**: 正規表現で `[^*\n]` を使い、改行をまたぐマッチを防止すること。

### HEIC画像
iPhoneの写真は `.heic` 形式。ブラウザは表示できないため、sipsコマンドでJPEGに自動変換される。

### CSVギャラリー
NotionのDBギャラリーはCSV+サブフォルダとしてエクスポートされ、画像とキャプションの正確な紐づけが消失する。
`convert_csv_gallery` 関数は、画像ファイル名に「キャプション文字列」が含まれていれば自動で紐付けて表示する。
**運用ルール**: Notionエクスポート後、ギャラリーの画像ファイル名をキャプションと同一（またはキャプションを含む名称）に変更して元画像フォルダ内に配置しておくこと。自動でコピーとHTML変換が行われる。

### リンク切れツイートの監視
Twitter(現X)の仕様変更やアカウント削除により、埋め込みツイートが非表示(404/403)になることがある。
定期的に以下のチェックスクリプトを実行し、記事内の死活確認を行うこと。
```bash
python3 scripts/check_dead_tweets.py
```

### favicon
`public/favicon.svg`（ヒツジアイコン）のみ使用。`favicon.ico` は不要（`Layout.astro` で SVG のみ参照）。

### 記事の順序
各カテゴリのCSVファイル（`Work *.csv` / `Life *.csv`）の上から順に `order` が付与される。トップページでは `order` 昇順で表示。

### 画像サイズ
`public/images/` は約1.2GiBあるため、GitHub Pagesではなく **Cloudflare Pages** でデプロイする。

## サイトデザインルール

- **フォント**: Cormorant Garamond（見出し）+ Inter（本文）
- **カラー**: モノトーン基調、CSSカスタムプロパティで管理（`global.css`）
- **h2**: `border-bottom: 1px solid` で下線付き
- **h3**: 下線なし
- **箇条書き**: `list-style-type: disc`（Tailwind CSSのリセットで消えるため明示指定）
- **Contact SNS**: インラインSVGアイコン（X/GitHub/Instagram/Facebook）
- **About me背景**: opacity 0.45、grayscale 40%
