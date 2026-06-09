# tenjimn-site 開発ガイド

個人サイト [tenjimn.com](https://tenjimn.com) のソースコード。Astro + Tailwind CSS で構築。

## プロジェクト構造

```
tenjimn-site/
├── inbox/                       # 新規記事の投入先（ZIPを置く場所）
│   ├── work/                    # Work記事のZIPを置く
│   ├── life/                    # Life記事のZIPを置く
│   └── README.md                # 使い方の説明
├── src/
│   ├── content/blog/            # 記事MD（変換スクリプトが生成）
│   ├── pages/
│   │   ├── index.astro          # トップページ
│   │   └── blog/[slug].astro    # 記事ページ
│   ├── layouts/Layout.astro     # 共通レイアウト
│   └── styles/global.css
├── public/
│   ├── images/                  # 記事画像（変換スクリプトが配置）
│   └── favicon.svg              # ヒツジアイコン
├── notion_export/               # 処理済みアーカイブ（git管理外）
│   └── Article/
│       ├── Work/                # 処理済みWork記事のZIP・MD・画像
│       └── Life/                # 処理済みLife記事のZIP・MD・画像
├── scripts/
│   ├── add_from_zip.py          # 記事追加スクリプト（メイン）
│   ├── convert_notion.py        # 変換ロジックライブラリ / フルリビルド
│   └── check_dead_tweets.py     # リンク切れツイート監視
└── AGENTS.md                    # このファイル
```

## 記事の追加・更新ワークフロー

### 1. Notionで記事を書く
- Article の Work または Life データベースに記事を作成
- 画像はNotion内にアップロード

### 2. Notionからエクスポート
- 「Markdown & CSV」形式でエクスポート（ZIPがダウンロードされる）

### 3. ZIPを inbox/ に配置
- ダウンロードしたZIPファイルをカテゴリに応じたフォルダに置く
  - `inbox/work/` — Work カテゴリの記事
  - `inbox/life/` — Life カテゴリの記事
- ZIPは展開不要。そのまま置くだけでOK
- 複数のZIPを同時に置いて一括処理可能

### 4. 変換スクリプトを実行
```bash
python3 scripts/add_from_zip.py
```
これにより以下が自動実行される：
- inbox/ 内の全ZIPを検出・展開
- MDファイルの変換（11種類の変換処理）
- 変換結果を `src/content/blog/` に保存
- 画像を `public/images/{slug}/` へコピー
- HEIC画像をJPEGに自動変換（macOSのsipsコマンド使用）
- 処理済みZIPを `notion_export/Article/{Work|Life}/` にアーカイブ移動

### 5. ビルド・確認・デプロイ
```bash
npm run dev          # ローカル確認
npx astro build      # ビルド確認
```
- git commit / git push はユーザーがエディタ上で行う
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

## 記事追加の実行仕様（AIエージェント向け）

### スクリプト一覧と使い分け

| やりたいこと | 実行するスクリプト | コマンド |
|---|---|---|
| 新規記事を追加する | `add_from_zip.py` | `python3 scripts/add_from_zip.py` |
| 全記事をフルリビルドする | `convert_notion.py` | `python3 scripts/convert_notion.py --full` |
| リンク切れツイートを確認する | `check_dead_tweets.py` | `python3 scripts/check_dead_tweets.py` |

**重要**: 通常の記事追加では `convert_notion.py` は直接実行しない。`add_from_zip.py` が内部で `convert_notion.py` の変換関数を呼び出す。

### add_from_zip.py の挙動

#### 引数なし実行（推奨）
```bash
python3 scripts/add_from_zip.py
```

処理フロー:
1. `inbox/work/` と `inbox/life/` 内の `.zip` ファイルを全て検出する
2. 各ZIPについて以下を実行:
   a. ZIPを一時ディレクトリに展開（入れ子ZIPにも対応）
   b. 展開されたMDファイルからタイトルとスラッグを生成
   c. `convert_notion.py` の変換パイプラインを適用（11種類の変換処理）
   d. 変換結果を `src/content/blog/{slug}.md` に保存
   e. 画像を `public/images/{slug}/` にコピー（HEIC→JPEG自動変換含む）
   f. 処理済みZIPを `notion_export/Article/{Work|Life}/` にアーカイブ移動
3. ZIPが1つもない場合は「inbox/ にZIPがありません」と表示して正常終了

#### 個別ZIP指定（従来互換）
```bash
python3 scripts/add_from_zip.py path/to/export.zip --category work
```
- 指定したZIPのみを処理する
- `--category` でカテゴリを指定（work または life、デフォルト: work）
- この場合、アーカイブ移動は行われない

#### エラー時の挙動
- ZIPの展開に失敗 → エラー表示して次のZIPへ進む（1件の失敗で全体が止まらない）
- ZIP内にMDファイルがない → 警告表示してスキップ
- 変換中のエラー → エラー表示、ZIPはinboxに残す（アーカイブ移動しない）

### convert_notion.py の挙動

#### 引数なし実行
```bash
python3 scripts/convert_notion.py
```
- 「新規記事の追加は `add_from_zip.py` を使ってください」と案内を表示
- 何も変換しない

#### --full フラグ付き実行
```bash
python3 scripts/convert_notion.py --full
```
- `notion_export/Article/` 配下の全MD（Work + Life）を処理
- 全記事を上書きする（既存記事も含めてフルリビルド）
- **通常は使わない**。変換ロジックを修正した後に全記事に反映したい場合のみ使用

### AIエージェントが記事を追加する手順

1. ユーザーからNotionエクスポートのZIPファイルが提供される
2. ZIPをカテゴリに応じて `inbox/work/` または `inbox/life/` に配置する
3. `python3 scripts/add_from_zip.py` を実行する
4. 出力を確認し、エラーがないことを確認する
5. `npm run dev` でローカルプレビューし、表示を確認する
6. **git commit, git push は実行しない**（ユーザーがエディタ上で行う）
