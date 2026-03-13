#!/usr/bin/env python3
"""
Notion Export → Astro Blog Converter

Notionの書き出しデータをAstroのブログ形式に変換するスクリプト。
- notion_export内のMarkdownを読み込み
- 画像をpublic/images/へコピー
- 画像パスをAstro形式に書き換え
- frontmatter(title, category, order, heroImage)を付与
- src/content/blog/に保存
"""

import csv
import os
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, quote

# ===== パス設定 =====
PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOTION_EXPORT = PROJECT_ROOT / "notion_export" / "Article"
OUTPUT_BLOG = PROJECT_ROOT / "src" / "content" / "blog"
OUTPUT_IMAGES = PROJECT_ROOT / "public" / "images"


def slugify(text: str) -> str:
    """日本語対応のスラッグ生成。
    英数字 + ハイフンのみ、日本語はそのまま保持。"""
    text = text.strip().lower()
    # Notionのハッシュを除去（末尾の32文字hex）
    text = re.sub(r'\s+[0-9a-f]{32}$', '', text)
    # 特殊文字をハイフンに置換
    text = re.sub(r'[^\w\s\u3000-\u9fff\uff00-\uffef-]', '', text)
    text = re.sub(r'[\s\u3000]+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text


def extract_title(md_content: str, filename: str) -> str:
    """Markdownの先頭 # からタイトルを抽出。なければファイル名から。"""
    match = re.match(r'^#\s+(.+)$', md_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # ファイル名からハッシュを除去してタイトルに
    name = Path(filename).stem
    name = re.sub(r'\s+[0-9a-f]{32}$', '', name)
    return name


def get_image_dir_for_article(md_path: Path) -> Optional[Path]:
    """記事のMarkdownファイルに対応する画像ディレクトリを見つける。
    Notionのエクスポートでは、同名のフォルダに画像がある。"""
    stem = md_path.stem
    parent = md_path.parent

    candidates = [
        parent / stem,
        parent / unquote(stem),
    ]

    title_only = re.sub(r'\s+[0-9a-f]{32}$', '', stem)
    candidates.append(parent / title_only)
    candidates.append(parent / unquote(title_only))

    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def extract_first_image(md_content: str) -> Optional[str]:
    """Markdown内の最初の画像パスを抽出する（外部URLは除外）。"""
    img_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
    for match in img_pattern.finditer(md_content):
        img_ref = match.group(1)
        if not img_ref.startswith('http://') and not img_ref.startswith('https://'):
            return img_ref
    return None


def process_images(md_content: str, md_path: Path, article_slug: str) -> str:
    """Markdown内の画像リンクを検出し、画像をコピーしてパスを書き換える。"""
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    image_dir = get_image_dir_for_article(md_path)

    def replace_image(match):
        alt_text = match.group(1)
        img_ref = match.group(2)

        if img_ref.startswith('http://') or img_ref.startswith('https://'):
            return match.group(0)

        decoded_ref = unquote(img_ref)

        img_source = md_path.parent / decoded_ref
        if not img_source.exists():
            if image_dir:
                img_name = Path(decoded_ref).name
                img_source = image_dir / img_name
            if not img_source.exists():
                print(f"  ⚠️ 画像が見つかりません: {decoded_ref}")
                return match.group(0)

        article_img_dir = OUTPUT_IMAGES / article_slug
        article_img_dir.mkdir(parents=True, exist_ok=True)

        img_filename = img_source.name
        dest_path = article_img_dir / img_filename

        shutil.copy2(img_source, dest_path)

        # HEIC→JPEG変換（ブラウザはHEICを表示できない）
        if img_filename.lower().endswith('.heic'):
            jpeg_filename = Path(img_filename).stem + '.jpeg'
            jpeg_dest = article_img_dir / jpeg_filename
            try:
                import subprocess
                subprocess.run(
                    ['sips', '-s', 'format', 'jpeg', str(dest_path), '--out', str(jpeg_dest)],
                    capture_output=True, check=True
                )
                dest_path.unlink()  # HEICファイルを削除
                img_filename = jpeg_filename
                print(f"  🔄 HEIC→JPEG変換: {img_source.name} → {jpeg_filename}")
            except Exception as e:
                print(f"  ⚠️ HEIC変換失敗: {e}")

        new_path = f"/images/{article_slug}/{quote(img_filename)}"
        return f'![{alt_text}]({new_path})'

    return img_pattern.sub(replace_image, md_content)


def remove_notion_title(md_content: str) -> str:
    """先頭の # タイトル行を除去（frontmatterのtitleと重複するため）。"""
    lines = md_content.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip():
            start_idx = i
            break

    if start_idx < len(lines) and lines[start_idx].startswith('# '):
        lines = lines[:start_idx] + lines[start_idx + 1:]
        while lines and lines[0].strip() == '':
            lines.pop(0)

    return '\n'.join(lines)


def convert_notion_html(md_content: str) -> str:
    """Notionの <aside> タグなどを整形する。"""
    md_content = re.sub(
        r'<aside>\s*\n?(.*?)\n?\s*</aside>',
        lambda m: '\n> ' + m.group(1).replace('\n', '\n> ') + '\n',
        md_content,
        flags=re.DOTALL,
    )
    return md_content


def remove_callout_icons(md_content: str) -> str:
    """calloutのアイコン行を削除。
    > 🤖  や  > 💭  のような絵文字だけの引用行を除去する。"""
    # パターン: > に続いて絵文字のみ（空白含む）の行
    lines = md_content.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # "> 絵文字" のパターンを検出（絵文字+空白のみの引用行）
        if re.match(r'^>\s*$', stripped):
            # 空の引用行はそのまま保持
            cleaned.append(line)
        elif re.match(r'^>\s+\S{1,4}\s*$', stripped):
            # 引用記号 + 短いテキスト(絵文字1文字程度)だけの行か判定
            content_after_quote = re.sub(r'^>\s*', '', stripped).strip()
            # 絵文字のみかどうか判定
            if all(unicodedata.category(c).startswith(('So', 'Sk', 'Sm', 'Cn')) or c in '\ufe0f\u200d' or ord(c) > 0x1F000 for c in content_after_quote if not c.isspace()):
                # 絵文字だけの引用行 → スキップ
                continue
            else:
                cleaned.append(line)
        else:
            cleaned.append(line)
    return '\n'.join(cleaned)


def remove_duplicate_bookmark_links(md_content: str) -> str:
    """Notionのbookmark由来の重複リンクを除去。
    パターン1: [**テキスト**](URL)\n\n[テキスト](URL) → boldリンクだけ残す
    パターン2: [テキスト](URL)\n\n[テキスト](URL) → 1つだけ残す
    パターン3: [テキスト](URL)\n\n[テキスト | サイト名](URL2) → 1つ目だけ残す"""
    # パターン1: [**boldテキスト**](URL) の後に [同じテキスト](URL or URL2)
    # bold版リンクの後にプレーン版が続くパターン
    def remove_bold_plain_duplicates(content):
        # [**text**](url1)\n\n[text...](url2) - 同じテキストのリンクが続く
        pattern = re.compile(
            r'(\[\*\*([^*]+)\*\*\]\(([^)]+)\))\s*\n\s*\n\s*\[([^\]]+)\]\(([^)]+)\)',
            re.MULTILINE
        )
        def replace_match(m):
            bold_link = m.group(1)  # [**text**](url) 部分
            bold_text = m.group(2)  # text部分
            plain_text = m.group(4)  # プレーンリンクのテキスト
            # プレーンテキストがboldテキストを含む場合、重複と判定
            if bold_text in plain_text or plain_text in bold_text:
                return bold_link
            return m.group(0)  # 重複でなければそのまま
        prev = None
        while prev != content:
            prev = content
            content = pattern.sub(replace_match, content)
        return content
    
    md_content = remove_bold_plain_duplicates(md_content)
    
    # パターン2: 完全一致の重複リンク
    pattern2 = re.compile(
        r'(\[([^\]]+)\]\(([^)]+)\))\s*\n\s*\n\s*\[\2\]\(\3\)',
        re.MULTILINE
    )
    prev = None
    while prev != md_content:
        prev = md_content
        md_content = pattern2.sub(r'\1', md_content)
    
    # パターン3: 同じURLでテキストが少し違うパターン
    # [テキスト](URL)\n\n[テキスト | サイト](URL) → 1つ目だけ
    pattern3 = re.compile(
        r'(\[([^\]]+)\]\((https?://[^)]+)\))\s*\n\s*\n\s*\[[^\]]+\]\(\3\)',
        re.MULTILINE
    )
    prev = None
    while prev != md_content:
        prev = md_content
        md_content = pattern3.sub(r'\1', md_content)
    
    return md_content


def remove_outline_blocks(md_content: str) -> str:
    """「📝 Outline」や「💡 Outline」のようなNotion独自のcalloutブロックを削除する。
    引用ブロック全体（> 行の連続）を削除。"""
    lines = md_content.split('\n')
    cleaned = []
    skip_block = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Outlineブロックの開始を検出
        if re.match(r'^>\s*.{0,4}\s*\*\*Outline\*\*', stripped):
            skip_block = True
            continue
        
        if skip_block:
            # 引用ブロックが続いている限りスキップ
            if stripped.startswith('>') or stripped == '':
                # 空行の場合、次の行が引用でなければブロック終了
                if stripped == '':
                    # 次の非空行が > で始まらなければブロック終了
                    next_nonempty = None
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip():
                            next_nonempty = lines[j].strip()
                            break
                    if next_nonempty is None or not next_nonempty.startswith('>'):
                        skip_block = False
                        # 空行は保持しない（Outlineブロックの一部）
                        continue
                continue
            else:
                skip_block = False
                cleaned.append(line)
        else:
            cleaned.append(line)
    
    return '\n'.join(cleaned)


def fix_bold_fullwidth_chars(md_content: str) -> str:
    """Notionエクスポートで壊れた太字パターンを包括的に修正する。
    
    問題の根本原因: Notionから出力されたMarkdownで、全角文字（括弧、カギ括弧等）の
    直後にある**がMarkdownパーサーに認識されないため、<strong>タグへの変換が
    部分的にしか行われず、**text<strong> や </strong>text** といった壊れたパターンが発生する。
    
    この関数は以下のパターンを全て修正する:
    1. **text<strong> → <strong>text</strong>  (開始**あり、閉じが<strong>に化けている)
    2. </strong>text** → <strong>text</strong>  (開始が</strong>に化けている、閉じ**あり)
    3. ## **heading<strong> → ## <strong>heading</strong>  (見出し内の太字1)
    4. ## </strong>heading** → ## <strong>heading</strong>  (見出し内の太字2)
    5. ***italic*<strong> → <strong><em>italic</em></strong>  (斜体+太字の壊れ)
    6. </strong>*italic*** → <strong><em>italic</em></strong>  (斜体+太字の壊れ2)
    7. 通常の全角括弧含み太字: **text（desc）** → <strong>text（desc）</strong>
    
    リンク [**text**](url) 内の太字は変換しない。
    """
    # Step 1: リンクパターンを一旦プレースホルダーに置換して保護
    links = []
    link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
    
    def save_link(match):
        idx = len(links)
        links.append(match.group(0))
        return f'__LINK_PLACEHOLDER_{idx}__'
    
    protected = link_pattern.sub(save_link, md_content)
    
    # Step 2: 壊れたパターンを修正（全て行内でのみマッチさせる）
    
    # パターン A: ***italic*<strong> → <strong><em>italic</em></strong>
    # (斜体+太字の開始が***、閉じが*<strong>に化けている)
    protected = re.sub(
        r'\*\*\*([^*\n]+)\*<strong>',
        r'<strong><em>\1</em></strong>',
        protected
    )
    
    # パターン B: </strong>*italic*** → <strong><em>italic</em></strong>  
    protected = re.sub(
        r'</strong>\*([^*\n]+)\*\*\*',
        r'<strong><em>\1</em></strong>',
        protected
    )
    
    # パターン C: **text<strong> → <strong>text</strong>
    # (開始**あり、閉じが<strong>タグに化けている)
    protected = re.sub(
        r'\*\*([^*<>\n]+)<strong>',
        r'<strong>\1</strong>',
        protected
    )
    
    # パターン D: </strong>text** → <strong>text</strong>
    # (開始が</strong>タグに化けている、閉じ**あり)
    protected = re.sub(
        r'</strong>([^*<>\n]+)\*\*',
        r'<strong>\1</strong>',
        protected
    )
    
    # パターン E: 通常の全角括弧等を含む太字 **text（desc）** → <strong>タグ
    # (全角括弧、カギ括弧、角括弧の直後の**がパーサーに認識されない問題)
    # 重要: [^*\n] で改行をまたぐマッチを防止
    bold_fullwidth = re.compile(r'\*\*([^*\n]*[）」】\]）][^*\n]*)\*\*')
    protected = bold_fullwidth.sub(r'<strong>\1</strong>', protected)
    
    # さらに包括的なパターン: ** 任意の文字列 ** を <strong> に変換
    # 既存のMarkdownリンク以外で、** が残ってしまうケースを一斉置換
    # 連続する改行を含まない範囲でマッチ
    any_bold = re.compile(r'\*\*([^*<>\n]+)\*\*')
    protected = any_bold.sub(r'<strong>\1</strong>', protected)
    
    # Step 3: プレースホルダーを元のリンクに復元
    for i, link in enumerate(links):
        protected = protected.replace(f'__LINK_PLACEHOLDER_{i}__', link)
    
    return protected


def remove_hr_around_headings(md_content: str) -> str:
    """h2/h3の前後に存在する --- (水平線) を除去する。
    CSSのborder-bottomと重なって二重線に見えるのを防ぐ。"""
    lines = md_content.split('\n')
    cleaned = []
    skip_next_hr = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if skip_next_hr:
            if stripped == '':
                cleaned.append(line)  # 空行は保持
                continue
            elif stripped == '---' or stripped == '***' or stripped == '___':
                skip_next_hr = False
                continue  # 直後のhrをスキップ
            else:
                skip_next_hr = False
                cleaned.append(line)
        else:
            if stripped.startswith('## ') or stripped.startswith('### '):
                skip_next_hr = True
                # 直前のhr（空行を挟んでも可）を遡って削除する
                for j in range(len(cleaned)-1, -1, -1):
                    prev_stripped = cleaned[j].strip()
                    if prev_stripped == '':
                        continue
                    elif prev_stripped in ('---', '***', '___'):
                        cleaned.pop(j)
                        break
                    else:
                        break # hrではなかったら終了
            cleaned.append(line)
    
    return '\n'.join(cleaned)


def convert_csv_gallery(md_content: str, md_path: Path, article_slug: str) -> str:
    """Notion DBのCSVリンクをキャプションリストのギャラリー形式に変換する。
    画像が同封されていれば紐付けて出力する。
    [DB Name](path/to/file.csv) → 画像付きまたはキャプションのみのグリッドHTML"""
    csv_link_pattern = re.compile(
        r'\[([^\]]+)\]\((.*?\.csv)\)'
    )
    
    image_dir = get_image_dir_for_article(md_path)
    
    def scrub_text(text: str) -> str:
        # 画像マッチング用に、ひらがなカタカナ漢字英数字以外（記号や空白）を可能な限り除去する
        import string
        for c in [' ', '　', '_', '、', '。', ',', '.', '・', '！', '？', '-', '(', ')', '（', '）', '[', ']']:
            text = text.replace(c, '')
        return text
    
    def replace_csv_link(match):
        db_name = match.group(1)
        csv_ref = match.group(2)
        
        # CSVファイルのパスを解決
        decoded_ref = unquote(csv_ref)
        csv_file = md_path.parent / decoded_ref
        
        if not csv_file.exists():
            print(f"  ⚠️ CSVファイルが見つかりません: {decoded_ref}")
            return match.group(0)
        
        # CSVからキャプション（Name列）を読み取り
        captions = []
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if row and row[0].strip():
                        captions.append(row[0].strip())
        except Exception as e:
            print(f"  ⚠️ CSV読み取りエラー: {e}")
            return match.group(0)
        
        if not captions:
            return match.group(0)
            
        # 出力先ディレクトリ
        article_img_dir = OUTPUT_IMAGES / article_slug
        
        # HTMLギャラリーを生成
        items_html = []
        found_images_count = 0
        for caption in captions:
            # 画像を探す
            img_src_path = None
            clean_caption = scrub_text(caption)
            
            # 1. まずは出力先（public/images/...）にすでに存在するか確認
            if article_img_dir.exists():
                for f in article_img_dir.iterdir():
                    if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.heic', '.webp']:
                        fname_clean = scrub_text(f.stem)
                        if clean_caption in fname_clean or fname_clean in clean_caption:
                            img_src_path = f
                            break
            
            # 2. なければNotion Exportのディレクトリ（image_dir）を探す
            if not img_src_path and image_dir and image_dir.exists():
                for f in image_dir.rglob('*'):
                    if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.heic', '.webp']:
                        fname_clean = scrub_text(f.stem)
                        if clean_caption in fname_clean or fname_clean in clean_caption:
                            img_src_path = f
                            break
                            
            if img_src_path:
                found_images_count += 1
                # 画像をコピー・変換
                article_img_dir.mkdir(parents=True, exist_ok=True)
                img_filename = img_src_path.name
                dest_path = article_img_dir / img_filename
                
                if img_src_path != dest_path:
                    shutil.copy2(img_src_path, dest_path)
                
                # HEIC→JPEG変換
                if img_filename.lower().endswith('.heic'):
                    jpeg_filename = Path(img_filename).stem + '.jpeg'
                    jpeg_dest = article_img_dir / jpeg_filename
                    try:
                        import subprocess
                        subprocess.run(
                            ['sips', '-s', 'format', 'jpeg', str(dest_path), '--out', str(jpeg_dest)],
                            capture_output=True, check=True
                        )
                        dest_path.unlink()  # HEICファイルを削除
                        img_filename = jpeg_filename
                        print(f"  🔄 ギャラリー画像HEIC→JPEG変換: {img_src_path.name} → {jpeg_filename}")
                    except Exception as e:
                        print(f"  ⚠️ ギャラリー画像HEIC変換失敗: {e}")
                
                new_path = f"/images/{article_slug}/{quote(img_filename)}"
                items_html.append(f'<div class="gallery-item"><img src="{new_path}" alt="{caption}" loading="lazy" /><p class="gallery-caption">{caption}</p></div>')
            else:
                items_html.append(f'<div class="gallery-item"><p class="gallery-caption">{caption}</p></div>')
        
        grid_html = f'<div class="gallery-grid">\n' + '\n'.join(items_html) + '\n</div>'
        if found_images_count > 0:
            print(f"  🖼️  ギャラリー変換: {db_name} → {len(captions)} 件 (うち {found_images_count} 件画像付与あり)")
        else:
            print(f"  🖼️  ギャラリー変換: {db_name} → {len(captions)} 件 (画像なし)")
        return grid_html
    
    return csv_link_pattern.sub(replace_csv_link, md_content)


def convert_internal_links(md_content: str, all_slugs: dict) -> str:
    """ten-ezo.comへの内部リンクや、Notionの記事間リンクを
    新サイトの /blog/slug パスに変換する。"""
    # ten-ezo.comのリンクを内部リンクに変換
    def replace_tenezo_link(match):
        text = match.group(1)
        url = match.group(2)
        # ten-ezo.comのトップページ → /
        if re.match(r'https?://ten-ezo\.com/?$', url):
            return f'[{text}](/)'  
        # ten-ezo.comの記事リンクは判別が難しいのでそのまま
        return match.group(0)
    
    md_content = re.sub(
        r'\[([^\]]+)\]\((https?://ten-ezo\.com[^)]*?)\)',
        replace_tenezo_link,
        md_content
    )
    return md_content


def convert_twitter_embeds(md_content: str) -> str:
    """Twitter/XのプレーンURLリンクを公式埋め込みblockquoteに変換する。
    [URL](URL) パターン（URLがリンクテキストそのもの）のみを変換。
    [テキスト](URL) のような既にテキスト付きのリンクは変換しない。"""
    # パターン: [https://twitter.com/...](https://twitter.com/...) or [https://x.com/...](https://x.com/...)
    # リンクテキストとURLが同一(またはほぼ同一)のもののみ対象
    twitter_url_pattern = re.compile(
        r'\[(https?://(?:twitter\.com|x\.com)/[^\]]+)\]\((https?://(?:twitter\.com|x\.com)/[^)]+)\)',
        re.IGNORECASE
    )
    
    def replace_twitter_link(match):
        link_text = match.group(1)
        url = match.group(2)
        # リンクテキストがURL自体である場合のみ変換
        text_clean = link_text.strip().rstrip('/')
        url_clean = url.strip().rstrip('/')
        if text_clean == url_clean or url_clean.startswith(text_clean) or text_clean.startswith(url_clean):
            # status URLのみ埋め込み対象（ツイート）
            if '/status/' in url:
                url = url.replace('x.com', 'twitter.com')
                return f'<blockquote class="twitter-tweet"><a href="{url}"></a></blockquote>'
        return match.group(0)
    
    md_content = twitter_url_pattern.sub(replace_twitter_link, md_content)
    
    # 段落としてURLだけが単独行にあるパターンも対応
    # https://twitter.com/.../status/... (リンク構文なし、URLのみの行)
    bare_url_pattern = re.compile(
        r'^(https?://(?:twitter\.com|x\.com)/\w+/status/\d+[^\s]*)\s*$',
        re.MULTILINE | re.IGNORECASE
    )
    
    def replace_bare_url(match):
        url = match.group(1).replace('x.com', 'twitter.com')
        return f'<blockquote class="twitter-tweet"><a href="{url}"></a></blockquote>'
    
    md_content = bare_url_pattern.sub(replace_bare_url, md_content)
    
    return md_content


def create_frontmatter(title: str, category: str, slug: str, order: int, hero_image: Optional[str] = None) -> str:
    """Astro用のfrontmatterを生成。"""
    safe_title = title.replace("'", "''")
    fm = f"""---
title: '{safe_title}'
category: '{category}'
slug: '{slug}'
order: {order}"""
    if hero_image:
        fm += f"\nheroImage: '{hero_image}'"
    fm += "\n---\n"
    return fm


def load_csv_order(csv_path: Path) -> list:
    """CSVファイルから記事タイトルの順序を読み取る。"""
    titles = []
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # ヘッダーをスキップ
            for row in reader:
                if row:
                    titles.append(row[0].strip())
    return titles


def match_md_to_order(md_path: Path, order_titles: list) -> int:
    """MDファイルのタイトルをCSV順序リストと照合し、順番を返す。"""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    title = extract_title(content, md_path.name)

    # 完全一致で探す
    for i, csv_title in enumerate(order_titles):
        if csv_title == title:
            return i + 1

    # 部分一致で探す（Notionの微妙な変換差を吸収）
    title_normalized = title.lower().strip()
    for i, csv_title in enumerate(order_titles):
        csv_normalized = csv_title.lower().strip()
        # 引用符を除去して比較
        csv_clean = csv_normalized.replace('"', '').replace('"', '').replace('"', '')
        title_clean = title_normalized.replace('"', '').replace('"', '').replace('"', '')
        if csv_clean == title_clean or csv_clean in title_clean or title_clean in csv_clean:
            return i + 1

    # 見つからなかった場合は大きい数字（末尾に配置）
    print(f"  ⚠️ CSV内に順番が見つかりません: {title}")
    return 999


def process_category(category_name: str, category_dir: Path, csv_path: Path):
    """カテゴリ（Work/Life）ごとの記事を処理。"""
    # CSVから記事の順番を読み取り
    order_titles = load_csv_order(csv_path)
    print(f"  📋 CSV順序: {len(order_titles)} 件")

    md_files = list(category_dir.glob('*.md'))

    # CSVの順番に基づいてソート
    md_files_with_order = []
    for md_path in md_files:
        order = match_md_to_order(md_path, order_titles)
        md_files_with_order.append((order, md_path))

    md_files_with_order.sort(key=lambda x: x[0])

    count = 0

    for order, md_path in md_files_with_order:
        filename = md_path.name
        print(f"\n📄 処理中: {filename} (order: {order})")

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        title = extract_title(content, filename)
        print(f"  📌 タイトル: {title}")

        # 手作業で調整が必要な複雑な記事は上書きしないようにスキップ
        if title in ["2023年買って良かったもの", "公私ともに色々あった2022年を振り返る"]:
            print(f"  ⏭️ 除外記事のためスキップします: {title}")
            continue

        slug = slugify(md_path.stem)
        print(f"  🔗 スラッグ: {slug}")

        # タイトル行の除去
        content = remove_notion_title(content)

        # Notion HTMLの変換
        content = convert_notion_html(content)

        # Outlineブロック削除
        content = remove_outline_blocks(content)

        # calloutアイコン行の削除
        content = remove_callout_icons(content)

        # 重複bookmarkリンクの除去
        content = remove_duplicate_bookmark_links(content)

        # 全角括弧を含む太字パターンの修正
        content = fix_bold_fullwidth_chars(content)

        # 内部リンク変換
        content = convert_internal_links(content, {})

        # Twitter/X埋め込み変換
        content = convert_twitter_embeds(content)

        # h2/h3前後のhr除去
        content = remove_hr_around_headings(content)

        # CSVギャラリー変換
        content = convert_csv_gallery(content, md_path, slug)

        # 画像処理
        content = process_images(content, md_path, slug)

        # 最初の画像をheroImageとして取得（変換後のパスから）
        first_img_match = re.search(r'!\[[^\]]*\]\((/images/[^)]+)\)', content)
        hero_image = first_img_match.group(1) if first_img_match else None
        if hero_image:
            print(f"  🖼️  ヒーロー画像: {hero_image}")

        # frontmatter付与
        frontmatter = create_frontmatter(title, category_name, slug, order, hero_image)
        final_content = frontmatter + content

        # 出力
        output_path = OUTPUT_BLOG / f"{slug}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"  ✅ 保存: {output_path.relative_to(PROJECT_ROOT)}")
        count += 1

    return count


def main():
    print("=" * 60)
    print("🔄 Notion Export → Astro Blog 変換ツール")
    print("=" * 60)

    # 出力ディレクトリ作成
    OUTPUT_BLOG.mkdir(parents=True, exist_ok=True)
    OUTPUT_IMAGES.mkdir(parents=True, exist_ok=True)

    total = 0

    # Work カテゴリ
    work_dir = NOTION_EXPORT / "Work"
    work_csv = NOTION_EXPORT / "Work 4be3bfcd233b42b38bc1c46dfb2a83a2.csv"
    if work_dir.exists():
        print("\n" + "─" * 40)
        print("📁 Work カテゴリ")
        print("─" * 40)
        total += process_category("work", work_dir, work_csv)

    # Life カテゴリ
    life_dir = NOTION_EXPORT / "Life"
    life_csv = NOTION_EXPORT / "Life 41e3d9aa8ea140dea6cd8f1be2e88778.csv"
    if life_dir.exists():
        print("\n" + "─" * 40)
        print("📁 Life カテゴリ")
        print("─" * 40)
        total += process_category("life", life_dir, life_csv)

    print("\n" + "=" * 60)
    print(f"✨ 変換完了！ 合計 {total} 件の記事を変換しました")
    print(f"   📝 記事: {OUTPUT_BLOG.relative_to(PROJECT_ROOT)}/")
    print(f"   🖼️  画像: {OUTPUT_IMAGES.relative_to(PROJECT_ROOT)}/")
    print("=" * 60)


if __name__ == '__main__':
    main()
