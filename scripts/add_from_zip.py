#!/usr/bin/env python3
"""
scripts/add_from_zip.py

NotionからエクスポートしたZIPファイルを解析し、特定の1記事としてサイトに追加するスクリプト。
既存の scripts/convert_notion.py のロジックを再利用します。
"""

import os
import sys
import zipfile
import shutil
import tempfile
import argparse
from pathlib import Path

# convert_notion.py をインポートできるようにパスを通す
sys.path.append(os.path.dirname(__file__))
import convert_notion

def main():
    parser = argparse.ArgumentParser(description='NotionエクスポートZIPから記事を追加します。')
    parser.add_argument('zip_path', help='NotionからエクスポートしたZIPファイルのパス')
    parser.add_argument('--category', choices=['work', 'life'], default='work', help='記事のカテゴリ (デフォルト: work)')
    
    args = parser.parse_args()
    zip_path = Path(args.zip_path)

    if not zip_path.exists():
        print(f"❌ エラー: ファイルが見つかりません: {zip_path}")
        return

    print(f"📦 ZIPを展開中: {zip_path.name}")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # ZIPを展開（入れ子構造にも対応）
        def process_all_zips(directory, initial_zip):
            # 最初の一回
            try:
                with zipfile.ZipFile(initial_zip, 'r') as zip_ref:
                    zip_ref.extractall(directory)
            except Exception as e:
                print(f"❌ エラー: ZIPの展開に失敗しました: {e}")
                return False

            # 入れ子になったZIPを順次展開して削除
            while True:
                found_zips = list(directory.rglob('*.zip'))
                if not found_zips:
                    break
                for z in found_zips:
                    try:
                        with zipfile.ZipFile(z, 'r') as zip_ref:
                            # 展開先を展開元と同じ階層にする
                            zip_ref.extractall(z.parent)
                        z.unlink()
                    except Exception as e:
                        print(f"⚠️ 入れ子ZIPの展開中に問題が発生しました ({z.name}): {e}")
                        z.unlink() # 壊れていても削除してループを抜けるようにする
            return True

        if not process_all_zips(tmp_path, zip_path):
            return

        # Markdownファイルを探す（再帰的に探すように変更）
        md_files = list(tmp_path.rglob('*.md'))
        
        # 不要なファイル（index.md などがある場合を考慮し、中身のあるMDを優先）
        md_files = [f for f in md_files if f.stat().st_size > 0]

        if not md_files:
            print("❌ エラー: ZIP内にMarkdownファイルが見つかりませんでした。")
            return
        
        # 複数ある場合は、一番それっぽいもの（ファイル名が長い、またはサブディレクトリ内のもの等）を選択
        # ここでは単純に最初に見つかったものを使用しつつ、もし複数あれば通知する
        md_path = md_files[0]
        if len(md_files) > 1:
            print(f"💡 複数のMDファイルが見つかりました。{md_path.name} を処理します。")
        
        filename = md_path.name
        
        print(f"📄 記事を変換中: {filename}")
        
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        title = convert_notion.extract_title(content, filename)
        slug = convert_notion.slugify(md_path.stem)
        
        print(f"  📌 タイトル: {title}")
        print(f"  🔗 スラッグ: {slug}")

        # convert_notion.py のロジックを順次適用
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
        content = convert_notion.remove_hr_around_headings(content)
        
        # CSVギャラリー変換（ZIP内にもCSVがある可能性があるため）
        content = convert_notion.convert_csv_gallery(content, md_path, slug)

        # 画像処理（既存の関数が md_path の親ディレクトリを見るので、展開先で動作する）
        content = convert_notion.process_images(content, md_path, slug)

        # ヒーロー画像取得
        import re
        first_img_match = re.search(r'!\[[^\]]*\]\((/images/[^)]+)\)', content)
        hero_image = first_img_match.group(1) if first_img_match else None

        # Frontmatter付与
        frontmatter = convert_notion.create_frontmatter(title, args.category, slug, hero_image)
        final_content = frontmatter + content

        # 保存
        output_path = convert_notion.OUTPUT_BLOG / f"{slug}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"✅ 変換完了！")
        print(f"   📝 記事: src/content/blog/{slug}.md")
        print(f"   🖼️  画像: public/images/{slug}/")
        print("\n'npm run dev' で確認してください。")

if __name__ == '__main__':
    main()
