"""
フィードバックフォームコンポーネント

サイドバーにフィードバック送信フォームを表示し、
Google Sheetsの「feedback」シートに記録する
"""

import streamlit as st
from datetime import datetime
import inspect
from pathlib import Path


# ファイル名 → ページ名のマッピング
_PAGE_NAME_MAP = {
    "app": "ホーム",
    "1_アカウント管理": "アカウント管理",
    "2_戦略設計": "戦略設計",
    "3_コンテンツ量産": "コンテンツ量産",
}


def render_feedback_form():
    """サイドバーにフィードバックフォームを描画"""

    # ページ名を自動取得（呼び出し元のファイル名から）
    try:
        caller_frame = inspect.stack()[1]
        caller_filename = Path(caller_frame.filename).stem
        page_name = _PAGE_NAME_MAP.get(caller_filename, caller_filename)
    except Exception:
        page_name = "不明"

    with st.sidebar:
        st.markdown("---")
        st.markdown("### フィードバック")

        with st.form("feedback_form", clear_on_submit=True):
            reporter = st.selectbox(
                "報告者",
                ["Futa", "Maho", "Toshi"],
            )

            content = st.text_area(
                "内容",
                placeholder="修正点や要望を自由に記入してください",
            )

            submitted = st.form_submit_button("送信", use_container_width=True)

        if submitted:
            if not content:
                st.sidebar.warning("内容を入力してください")
            else:
                success = _submit_feedback(
                    reporter=reporter,
                    content=content,
                    page_name=page_name,
                )
                if success:
                    st.sidebar.success("フィードバックを送信しました")
                else:
                    st.sidebar.error("送信に失敗しました")


def _submit_feedback(reporter: str, content: str, page_name: str) -> bool:
    """
    フィードバックをGoogle Sheetsに送信

    Args:
        reporter: 報告者名
        content: フィードバック内容
        page_name: ページ名

    Returns:
        成功した場合True
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        service_account_info = dict(st.secrets["google_service_account"])
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]

        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(
            service_account_info, scopes=scope
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(spreadsheet_id)

        # feedbackシートを取得または作成
        try:
            sheet = spreadsheet.worksheet("feedback")
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(
                title="feedback", rows=1000, cols=4
            )
            sheet.append_row(["日時", "ページ", "報告者", "内容"])

        # データを追加
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, page_name, reporter, content])

        return True

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"フィードバック送信エラー: {e}")
        return False
