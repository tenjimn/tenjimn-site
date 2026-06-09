# 📥 記事投入ボックス

NotionからエクスポートしたZIPファイルをここに置いて、スクリプトを実行してください。

## 使い方

1. Notionから記事を「Markdown & CSV」でエクスポート（ZIPがダウンロードされる）
2. ダウンロードしたZIPをカテゴリに応じたフォルダに置く
   - `inbox/work/` — Work カテゴリの記事
   - `inbox/life/` — Life カテゴリの記事
3. 変換スクリプトを実行
   ```bash
   python3 scripts/add_from_zip.py
   ```
4. 処理後、ZIPは `notion_export/Article/` に自動でアーカイブ移動されます

## 注意事項

- ZIPは必ず `work/` または `life/` フォルダに入れてください（直下に置いても処理されません）
- 複数のZIPを同時に置いて一括処理できます
- 処理が完了すると inbox 内のZIPは自動で移動されます
