"""
共有UIコンポーネント

ページ間で重複していたUI部品を一元管理。
"""

import streamlit as st


def render_loading(container, title: str, subtitle: str = ""):
    """
    アニメーション付きローディング表示

    Args:
        container: st.empty() などのStreamlitコンテナ
        title: メインタイトル
        subtitle: サブタイトル（省略可）
    """
    container.markdown(f"""
    <div class="loading-indicator">
        <div class="loading-spinner"></div>
        <div>
            <div class="loading-title">{title}</div>
            <div class="loading-subtitle">{subtitle}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str):
    """
    ページ共通ヘッダーを描画

    Args:
        title: ページタイトル
        subtitle: サブタイトル（説明文）
    """
    st.markdown(
        f'<div class="page-header">{title}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def render_status_badge(label: str, color: str, bg_color: str) -> str:
    """
    ステータスバッジHTMLを生成

    Args:
        label: バッジのテキスト
        color: テキスト色
        bg_color: 背景色

    Returns:
        バッジのHTML文字列
    """
    return (
        f'<span style="display:inline-block;padding:0.3rem 0.85rem;'
        f'border-radius:20px;font-size:0.8rem;font-weight:600;'
        f'color:{color};background:{bg_color};">{label}</span>'
    )
