CSSインライン監査を実行してください。

以下をチェック:

1. `src/sns_automation/web/pages/` 内の全 `.py` ファイルで `<style>` タグが使われていないか検索
2. 見つかった場合、それが本当にページ固有のものか、`styles.py` に移すべきかを判断
3. `styles.py` の CSS変数 (`--color-coral` 等) と `.streamlit/config.toml` の `primaryColor` が一致しているか確認
4. `__init__.py` のexportと各ページのimportに齟齬がないか確認
5. `render_loading` / `render_page_header` / `inject_styles` が全ページで正しく使われているか確認

結果をまとめて報告してください。問題があれば修正案も提示してください。
