#!/usr/bin/env python3
"""
check_dead_tweets.py

src/content/blog/ 内にある全てのMarkdown記事を走査し、
Twitter (現X) の埋め込み（`blockquote class="twitter-tweet"`）のURLを抽出します。
その後、XのoEmbed API (publish.twitter.com) に問い合わせを行い、
削除済み・非公開などで利用できなくなっている死活状態（404/403等）を検知します。
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# 対象ディレクトリ
BLOG_DIR = Path(__file__).resolve().parent.parent / "src" / "content" / "blog"

# Twitter埋め込みの正規表現パターン
TWEET_PATTERN = re.compile(r'<blockquote class=\"twitter-tweet\"><a href=\"(https://(?:twitter\.com|x\.com)/[^\"]+)\">')

def main():
    print("=" * 60)
    print("🐦 Twitter / X リンク切れツイートチェッカー")
    print("=" * 60)

    if not BLOG_DIR.exists():
        print(f"エラー: {BLOG_DIR} が見つかりません。")
        return

    # 全ツイートのURLを抽出
    results = []
    print("\n🔍 抽出中...")
    for fpath in BLOG_DIR.glob('*.md'):
        fname = fpath.name
        with open(fpath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                m = TWEET_PATTERN.search(line)
                if m:
                    url = m.group(1)
                    results.append((fname, i, url))

    total = len(results)
    print(f"✅ 対象ディレクトリ内のツイート数: {total}件\n")

    if total == 0:
        print("チェック対象のツイートは見つかりませんでした。")
        return

    # APIで死活確認
    print("📡 oEmbed APIで生存確認中 (1件0.3秒間隔)...")
    dead_tweets = []
    alive_tweets = []

    for idx, (fname, lineno, url) in enumerate(results, 1):
        # oEmbedは x.com でリクエスト
        check_url = url.replace("twitter.com", "x.com")
        oembed_url = f"https://publish.twitter.com/oembed?url={check_url}"
        
        try:
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode('utf-8'))
            alive_tweets.append((fname, lineno, url))
            print(f"  [{idx}/{total}] ✅ OK: {fname}:{lineno}")
        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code}"
            if e.code == 404:
                msg = "HTTP 404 (削除済みまたは存在しない)"
            elif e.code == 403:
                msg = "HTTP 403 (非公開アカウント等)"
            dead_tweets.append((fname, lineno, url, msg))
            print(f"  [{idx}/{total}] ❌ NG: {fname}:{lineno} -> {msg}")
        except Exception as e:
            dead_tweets.append((fname, lineno, url, str(e)))
            print(f"  [{idx}/{total}] ⚠️ ERROR: {fname}:{lineno} -> {e}")
        
        # レートリミット対策で少し待機
        time.sleep(0.3)

    print("\n" + "=" * 60)
    print(f"🎉 チェック完了!  正常: {len(alive_tweets)} 件 / エラー(リンク切れ): {len(dead_tweets)} 件")
    
    if dead_tweets:
        print("\n⚠️ 以下のツイートは現在表示できません。記事からの除去を検討してください。")
        for fname, lineno, url, reason in dead_tweets:
            print(f"  - {fname} (Line {lineno}):")
            print(f"    URL: {url}")
            print(f"    Reason: {reason}")
    print("=" * 60)

if __name__ == '__main__':
    main()
