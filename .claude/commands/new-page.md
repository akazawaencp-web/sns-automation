新しいStreamlitページを作成してください。

ページ名: $ARGUMENTS

以下のテンプレートに従って `src/sns_automation/web/pages/` にファイルを作成してください:

1. ファイル名は `N_ページ名.py` 形式（Nは既存ページの次の番号）
2. 必ず以下のボイラープレートを使う:

```python
import streamlit as st
from sns_automation.web.components import (
    inject_styles, render_page_header, render_feedback_form
)

def main():
    st.set_page_config(
        page_title="ページ名 - SNS Automation",
        page_icon="▲",
        layout="wide",
    )
    inject_styles()
    render_feedback_form()
    render_page_header("ページ名", "説明文")
    st.markdown("---")
    # ページ固有のロジック

if __name__ == "__main__":
    main()
```

3. テーブルが必要な場合は `<div class="app-table">` でラップし、セルには `.cell-name`, `.cell-center` 等のCSSクラスを使う
4. ローディングが必要なら `render_loading` をインポートして使う
5. CSSはインラインで書かず、必要なら `styles.py` に追加する

ページの目的に合わせて内容を実装してください。
