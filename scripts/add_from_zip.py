#!/usr/bin/env python3
"""
scripts/add_from_zip.py

NotionからエクスポートしたZIPファイルを解析し、記事をサイトに追加するスクリプト。
inbox/ ディレクトリ内のZIPを一括処理するか、個別ZIPパスを指定して処理する。

## 使い方

### inbox/ 一括処理（推奨）
```bash
python3 scripts/add_from_zip.py
```
inbox/work/ と inbox/life/ 内の全ZIPを検出して一括処理する。
処理済みZIPは notion_export/Article/{Work|Life}/ にアーカイブ移動される。

### 個別ZIP指定（従来互換）
```bash
python3 scripts/add_from_zip.py path/to/export.zip --category work
```
指定したZIPのみを処理する。--category でカテゴリを指定。

## 処理フロー
1. ZIPを一時ディレクトリに展開（入れ子ZIPにも対応）
2. 展開されたMDファイルからタイトルとスラッグを生成
3. convert_notion.py の変換パイプラインを適用（11種類の変換処理）
4. 変換結果を src/content/blog/{slug}.md に保存
5. 画像を public/images/{slug}/ にコピー（HEIC→JPEG自動変換含む）
6. 処理済みZIPを notion_export/Article/{Work|Life}/ にアーカイブ移動
"""

import os
import sys
import zipfile
import shutil
import tempfile
import argparse
import re
from datetime import datetime
from pathlib import Path

# convert_notion.py をインポートできるようにパスを通す
sys.path.append(os.path.dirname(__file__))
import convert_notion

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = PROJECT_ROOT / "inbox"
ARCHIVE_DIR = PROJECT_ROOT / "notion_export" / "Article"

# カテゴリ名とinbox/archive内のフォルダ名の対応
CATEGORY_MAP = {
    "work": {"inbox": INBOX_DIR / "work", "archive": ARCHIVE_DIR / "Work"},
    "life": {"inbox": INBOX_DIR / "life", "archive": ARCHIVE_DIR / "Life"},
}


def extract_zip(zip_path: Path, dest_dir: Path) -> bool:
    """ZIPを展開する。入れ子ZIPにも対応。

    Args:
        zip_path: 展開するZIPファイルのパス
        dest_dir: 展開先ディレクトリ

    Returns:
        成功した場合True
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
    except Exception as e:
        print(f"❌ エラー: ZIPの展開に失敗しました: {e}")
        return False

    # 入れ子になったZIPを順次展開して削除
    while True:
        found_zips = list(dest_dir.rglob('*.zip'))
        if not found_zips:
            break
        for z in found_zips:
            try:
                with zipfile.ZipFile(z, 'r') as zip_ref:
                    zip_ref.extractall(z.parent)
                z.unlink()
            except Exception as e:
                print(f"⚠️ 入れ子ZIPの展開中に問題が発生しました ({z.name}): {e}")
                z.unlink()
    return True


def find_markdown_files(directory: Path) -> list[Path]:
    """ディレクトリ内のMarkdownファイルを再帰的に検索する。

    Args:
        directory: 検索するディレクトリ

    Returns:
        見つかったMDファイルのリスト（サイズ0のファイルは除外）
    """
    md_files = list(directory.rglob('*.md'))
    md_files = [f for f in md_files if f.stat().st_size > 0]
    return md_files


def process_single_zip(zip_path: Path, category: str) -> bool:
    """1つのZIPファイルを処理して記事に変換する。

    Args:
        zip_path: 処理するZIPファイルのパス
        category: カテゴリ名（"work" または "life"）

    Returns:
        処理が成功した場合True
    """
    print(f"\n📦 ZIPを展開中: {zip_path.name}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # ZIP展開
        if not extract_zip(zip_path, tmp_path):
            return False

        # Markdownファイルを探す
        md_files = find_markdown_files(tmp_path)

        if not md_files:
            print("❌ エラー: ZIP内にMarkdownファイルが見つかりませんでした。")
            return False

        # 複数ある場合は通知しつつ最初のものを使用
        md_path = md_files[0]
        if len(md_files) > 1:
            print(f"💡 複数のMDファイルが見つかりました。{md_path.name} を処理します。")

        filename = md_path.name

        print(f"📄 記事を変換中: {filename}")

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        title = convert_notion.extract_title(content, filename)
        slug = convert_notion.get_slug_for_article(title)

        print(f"  📌 タイトル: {title}")
        print(f"  🔗 スラッグ: {slug}")

        # convert_notion.py の変換パイプラインを順次適用
        content = convert_notion.remove_notion_title(content)
        content = convert_notion.clean_notion_properties(content)
        content = convert_notion.bold_headings(content)
        content = convert_notion.convert_notion_html(content)
        content = convert_notion.remove_outline_blocks(content)
        content = convert_notion.remove_callout_icons(content)
        content = convert_notion.remove_duplicate_bookmark_links(content)
        content = convert_notion.fix_bold_fullwidth_chars(content)
        content = convert_notion.convert_internal_links(content, {})
        content = convert_notion.convert_twitter_embeds(content)
        content = convert_notion.convert_podcast_embeds(content)
        content = convert_notion.remove_hr_around_headings(content)

        # CSVギャラリー変換
        content = convert_notion.convert_csv_gallery(content, md_path, slug)

        # 画像処理
        content = convert_notion.process_images(content, md_path, slug)

        # ヒーロー画像取得
        first_img_match = re.search(r'!\[[^\]]*\]\((/images/[^)]+)\)', content)
        hero_image = first_img_match.group(1) if first_img_match else None

        # Instagram埋め込み変換
        if "Instagram" in content or "instagram" in content:
            content = convert_notion.convert_instagram_embeds(content)

        # Frontmatter付与
        frontmatter = convert_notion.create_frontmatter(title, category, slug, hero_image)
        final_content = frontmatter + content

        # 保存
        output_path = convert_notion.OUTPUT_BLOG / f"{convert_notion.slugify(title)}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"  ✅ 変換完了！")
        print(f"     📝 記事: {output_path.relative_to(PROJECT_ROOT)}")
        print(f"     🖼️  画像: public/images/{slug}/")

    return True


def archive_zip(zip_path: Path, category: str):
    """処理済みZIPを notion_export/Article/{Category}/ にアーカイブ移動する。

    同名ファイルが存在する場合はタイムスタンプ付きでリネームする。

    Args:
        zip_path: 移動するZIPファイルのパス
        category: カテゴリ名（"work" または "life"）
    """
    archive_dir = CATEGORY_MAP[category]["archive"]
    archive_dir.mkdir(parents=True, exist_ok=True)

    dest = archive_dir / zip_path.name

    # 同名ファイルが存在する場合はタイムスタンプ付きでリネーム
    if dest.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = zip_path.stem
        dest = archive_dir / f"{stem}_{timestamp}.zip"

    shutil.move(str(zip_path), str(dest))
    print(f"  📦 アーカイブ移動: {dest.relative_to(PROJECT_ROOT)}")


def process_inbox():
    """inbox/ 内の全ZIPを検出して一括処理する。"""
    print("=" * 60)
    print("📥 inbox/ 一括処理モード")
    print("=" * 60)

    total_processed = 0
    total_errors = 0

    for category, paths in CATEGORY_MAP.items():
        inbox_category_dir = paths["inbox"]

        if not inbox_category_dir.exists():
            inbox_category_dir.mkdir(parents=True, exist_ok=True)
            continue

        zip_files = sorted(inbox_category_dir.glob("*.zip"))

        if not zip_files:
            continue

        print(f"\n{'─' * 40}")
        print(f"📁 {category.capitalize()} カテゴリ: {len(zip_files)} 件のZIP")
        print(f"{'─' * 40}")

        for zip_path in zip_files:
            success = process_single_zip(zip_path, category)

            if success:
                archive_zip(zip_path, category)
                total_processed += 1
            else:
                print(f"  ⚠️ 処理に失敗しました。ZIPはinboxに残ります: {zip_path.name}")
                total_errors += 1

    print(f"\n{'=' * 60}")
    if total_processed == 0 and total_errors == 0:
        print("📭 inbox/ にZIPファイルがありません。")
        print("   NotionエクスポートのZIPを inbox/work/ または inbox/life/ に置いてください。")
    else:
        print(f"✨ 処理完了！ {total_processed} 件成功", end="")
        if total_errors > 0:
            print(f", {total_errors} 件エラー", end="")
        print()
        if total_processed > 0:
            print("   'npm run dev' で確認してください。")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='NotionエクスポートZIPから記事を追加します。',
        epilog='引数なしで実行すると inbox/ 内の全ZIPを一括処理します。'
    )
    parser.add_argument(
        'zip_path',
        nargs='?',
        default=None,
        help='処理するZIPファイルのパス（省略時は inbox/ を一括処理）'
    )
    parser.add_argument(
        '--category',
        choices=['work', 'life'],
        default='work',
        help='記事のカテゴリ (デフォルト: work)。個別ZIP指定時のみ使用。'
    )

    args = parser.parse_args()

    if args.zip_path is None:
        # inbox/ 一括処理モード
        process_inbox()
    else:
        # 個別ZIP指定モード（従来互換）
        zip_path = Path(args.zip_path)

        if not zip_path.exists():
            print(f"❌ エラー: ファイルが見つかりません: {zip_path}")
            return

        success = process_single_zip(zip_path, args.category)

        if success:
            print("\n'npm run dev' で確認してください。")


if __name__ == '__main__':
    main()
