"""
全ページ共通CSSモジュール

inject_styles() を各ページで1回呼ぶだけで統一デザインが適用される。
"""

import streamlit as st


def inject_styles():
    """全ページ共通のCSSを注入"""
    st.markdown(get_global_css(), unsafe_allow_html=True)


def get_global_css() -> str:
    """グローバルCSSを返す"""
    return f"<style>{_CSS_VARIABLES}{_BASE_LAYOUT}{_TYPOGRAPHY}{_SIDEBAR}{_BUTTONS}{_INPUTS}{_SELECTBOX}{_CHECKBOX}{_RADIO}{_EXPANDER}{_TABS}{_METRICS}{_TABLE}{_FORMS}{_LOADING}{_ANIMATIONS}{_HR}{_HIDE_STREAMLIT}{_PROGRESS_BAR}</style>"


# ── CSS変数 ──────────────────────────────────────
_CSS_VARIABLES = """
:root {
    --color-coral: #ea8768;
    --color-sky: #33b6de;
    --color-gradient: linear-gradient(135deg, var(--color-coral) 0%, var(--color-sky) 100%);
    --color-gradient-light: linear-gradient(135deg, rgba(234,135,104,0.08) 0%, rgba(51,182,222,0.08) 100%);
    --color-gradient-subtle: linear-gradient(135deg, rgba(234,135,104,0.06) 0%, rgba(51,182,222,0.06) 100%);
    --color-text-dark: #121213;
    --color-text-gray: #828282;
    --color-text-body: #374151;
    --color-border: #d0d0d0;
    --color-bg-light: #f0f2f6;
    --radius-sm: 0.5rem;
    --radius-md: 1rem;
    --radius-lg: 1.5rem;
    --radius-xl: 20px;
    --radius-pill: 2.9rem;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 20px rgba(0,0,0,0.08);
    --shadow-lg: 0 8px 32px rgba(234,135,104,0.2);
    --shadow-card: 0 4px 20px rgba(0,0,0,0.06);
    --transition-default: all 0.3s ease;
}
"""

# ── ベースレイアウト ──────────────────────────────────
_BASE_LAYOUT = """
.stApp {
    background: transparent !important;
}

.block-container, [data-testid="block-container"] {
    background: rgba(255, 255, 255, 0.7) !important;
    backdrop-filter: blur(10px) !important;
    border-radius: var(--radius-xl) !important;
    padding: 2rem !important;
    padding-top: 3rem !important;
    padding-bottom: 3rem !important;
    box-shadow: var(--shadow-card) !important;
    max-width: 1200px !important;
    animation: fadeInUp 0.5s ease-out;
}
"""

# ── タイポグラフィ ──────────────────────────────────
_TYPOGRAPHY = """
.page-header {
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    color: var(--color-text-dark) !important;
    margin-bottom: 0.5rem;
    letter-spacing: -0.02em;
    animation: fadeInUp 0.4s ease-out;
}

.main-header {
    font-size: 3.5rem !important;
    font-weight: 700 !important;
    text-align: center;
    margin-bottom: 0.5rem;
    color: var(--color-text-dark) !important;
    letter-spacing: -0.03em;
    animation: fadeInUp 0.4s ease-out;
}

.page-subtitle, .main-subtitle {
    color: var(--color-text-gray) !important;
    font-size: 1.05rem !important;
    margin-bottom: 2rem;
    animation: fadeInUp 0.5s ease-out 0.1s both;
}

.main-subtitle {
    text-align: center;
    font-size: 1.15rem !important;
    margin-bottom: 4rem;
    font-weight: 400;
}

.section-header {
    font-size: 2rem !important;
    font-weight: 600 !important;
    color: var(--color-text-dark) !important;
    margin-top: 3rem;
    margin-bottom: 2rem;
}
"""

# ── サイドバー ───────────────────────────────────
_SIDEBAR = """
section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid var(--color-border) !important;
}

section[data-testid="stSidebar"] > div {
    background-color: #ffffff !important;
}

a[data-testid="stSidebarNavLink"] {
    border-radius: var(--radius-md) !important;
    padding: 0.6rem 1rem !important;
    margin: 0.15rem 0.5rem !important;
    transition: var(--transition-default) !important;
    text-decoration: none !important;
}

a[data-testid="stSidebarNavLink"]:hover {
    background: var(--color-gradient-light) !important;
    transform: translateX(4px) !important;
}

a[data-testid="stSidebarNavLink"][aria-current="page"],
a[data-testid="stSidebarNavLink"].is-active {
    background: var(--color-gradient-light) !important;
    border-left: 3px solid var(--color-coral) !important;
    font-weight: 600 !important;
}
"""

# ── ボタン ───────────────────────────────────────
_BUTTONS = """
.stButton > button {
    border-radius: var(--radius-pill) !important;
    font-weight: 500 !important;
    transition: var(--transition-default) !important;
    border: 1px solid transparent !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}

.stButton > button[kind="primary"] {
    background: var(--color-gradient) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(234,135,104,0.3) !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(234,135,104,0.4) !important;
}
"""

# ── 入力フィールド ──────────────────────────────────
_INPUTS = """
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--color-border) !important;
    background-color: white !important;
    transition: var(--transition-default) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--color-coral) !important;
    box-shadow: 0 0 0 3px rgba(234,135,104,0.15) !important;
}

.stTextArea textarea:disabled {
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
}
"""

# ── セレクトボックス ─────────────────────────────────
_SELECTBOX = """
[data-testid="stSelectbox"] > div > div {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--color-border) !important;
    background-color: white !important;
    transition: var(--transition-default) !important;
}

[data-testid="stSelectbox"] > div > div:hover {
    border-color: var(--color-coral) !important;
}

[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--color-coral) !important;
    box-shadow: 0 0 0 3px rgba(234,135,104,0.15) !important;
}
"""

# ── チェックボックス ─────────────────────────────────
_CHECKBOX = """
div[role="checkbox"][aria-checked="true"] {
    background: var(--color-gradient) !important;
    border-color: var(--color-coral) !important;
}
"""

# ── ラジオボタン ──────────────────────────────────
_RADIO = """
[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"],
[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
    background: rgba(234,135,104,0.06) !important;
    border-radius: var(--radius-sm) !important;
}
"""

# ── Expander ──────────────────────────────────
_EXPANDER = """
[data-testid="stExpander"] {
    border: 1px solid rgba(234,135,104,0.15) !important;
    border-radius: var(--radius-lg) !important;
    transition: var(--transition-default) !important;
    overflow: hidden;
}

[data-testid="stExpander"]:hover {
    box-shadow: 0 4px 16px rgba(234,135,104,0.1) !important;
}

[data-testid="stExpander"] summary {
    transition: var(--transition-default) !important;
}

[data-testid="stExpander"] summary:hover {
    color: var(--color-coral) !important;
}
"""

# ── タブ ─────────────────────────────────────
_TABS = """
button[role="tab"] {
    transition: var(--transition-default) !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
}

button[role="tab"]:hover {
    background: var(--color-gradient-light) !important;
}

button[role="tab"][aria-selected="true"] {
    border-bottom: 3px solid var(--color-coral) !important;
    font-weight: 600 !important;
}
"""

# ── メトリクスカード ─────────────────────────────────
_METRICS = """
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.95) !important;
    padding: 1.8rem !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-md) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    transition: var(--transition-default) !important;
    backdrop-filter: blur(10px) !important;
    position: relative;
    overflow: hidden;
}

[data-testid="stMetric"]::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: var(--color-gradient);
}

[data-testid="stMetric"]:hover {
    transform: translateY(-4px) !important;
    box-shadow: var(--shadow-lg) !important;
}

[data-testid="stMetric"] label {
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: var(--color-text-gray) !important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    background: var(--color-gradient) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}
"""

# ── テーブル共通 ─────────────────────────────────
_TABLE = """
.app-table {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    border: 1px solid rgba(0,0,0,0.06);
    background: white;
}

.app-table table {
    width: 100%;
    border-collapse: collapse;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.app-table thead tr {
    background: var(--color-gradient-light);
}

.app-table tbody tr {
    transition: background-color 0.2s ease;
    animation: staggerFadeIn 0.3s ease-out both;
}

.app-table tbody tr:hover {
    background-color: rgba(234,135,104,0.04);
}

.app-table tbody tr:not(:last-child) td {
    border-bottom: 1px solid rgba(0,0,0,0.04);
}

.app-table th {
    padding: 0.9rem 1rem;
    font-size: 0.8rem;
    font-weight: 700;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid rgba(234,135,104,0.15);
}

.app-table td {
    padding: 0.85rem 1rem;
    font-size: 0.9rem;
    color: #374151;
}

.app-table td.cell-name {
    font-weight: 600;
    color: #1e293b;
    white-space: nowrap;
}

.app-table td.cell-nowrap {
    white-space: nowrap;
}

.app-table td.cell-truncate {
    max-width: 350px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.app-table td.cell-center {
    text-align: center;
}

.app-table td.cell-meta {
    color: #4b5563;
    font-size: 0.85rem;
    text-align: center;
    white-space: nowrap;
}

.app-table .empty-placeholder {
    color: #ccc;
}

.code-block {
    background-color: var(--color-bg-light);
    padding: 1rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    font-family: monospace;
    font-size: 14px;
    line-height: 1.6;
    word-wrap: break-word;
    white-space: pre-wrap;
    margin-bottom: 1rem;
}
"""

# ── フォーム ─────────────────────────────────────
_FORMS = """
[data-testid="stForm"] {
    border: 1px solid rgba(234,135,104,0.15) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1.5rem !important;
}
"""

# ── ローディング ─────────────────────────────────
_LOADING = """
.loading-indicator {
    display: flex;
    align-items: center;
    gap: 1.2rem;
    padding: 1.5rem 2rem;
    margin: 1rem 0;
    background: var(--color-gradient-subtle);
    border: 1px solid rgba(234,135,104,0.15);
    border-radius: var(--radius-md);
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 3px solid rgba(234,135,104,0.2);
    border-top-color: var(--color-coral);
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
}

.loading-title {
    font-weight: 600;
    font-size: 1rem;
    color: #1e293b;
}

.loading-subtitle {
    font-size: 0.85rem;
    color: #64748b;
    margin-top: 0.2rem;
}
"""

# ── アニメーション ──────────────────────────────────
_ANIMATIONS = """
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(16px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes staggerFadeIn {
    from {
        opacity: 0;
        transform: translateX(-8px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
"""

# ── HR置き換え ───────────────────────────────────
_HR = """
hr {
    border: none !important;
    height: 2px !important;
    background: var(--color-gradient-light) !important;
    margin: 2rem 0 !important;
}
"""

# ── Streamlit非表示要素 ──────────────────────────────
_HIDE_STREAMLIT = """
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
"""

# ── プログレスバー ──────────────────────────────────
_PROGRESS_BAR = """
.stProgress > div > div {
    background: var(--color-gradient) !important;
}
"""


# ── 機能カード（ホームページ用） ───────────────────────────
FEATURE_CARD_CSS = """
.feature-card-container {
    background: rgba(255, 255, 255, 0.9) !important;
    padding: 2rem !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-md) !important;
    border: 1px solid rgba(234, 135, 104, 0.1) !important;
    margin: 1rem 0 !important;
    transition: var(--transition-default) !important;
    backdrop-filter: blur(10px) !important;
}

.feature-card-container:hover {
    transform: translateY(-5px) !important;
    box-shadow: 0 12px 40px rgba(234, 135, 104, 0.15) !important;
    border-color: rgba(234, 135, 104, 0.3) !important;
}

.feature-card-container h3 {
    color: var(--color-text-dark) !important;
    font-size: 1.4rem !important;
    font-weight: 600 !important;
    margin-bottom: 1rem !important;
}

.feature-card-container p {
    color: #666 !important;
    line-height: 1.7 !important;
    margin-bottom: 1rem !important;
}

.feature-card-container ul {
    color: var(--color-text-dark) !important;
    line-height: 1.8 !important;
}

.feature-card-container ul li {
    margin-bottom: 0.5rem !important;
}
"""


def inject_feature_card_styles():
    """ホームページ用の機能カードCSSを追加注入"""
    st.markdown(f"<style>{FEATURE_CARD_CSS}</style>", unsafe_allow_html=True)


# ── スライドテーブル（コンテンツ量産ページ用） ──────────────────
SLIDES_TABLE_CSS = """
.slides-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    margin-top: 1rem;
}
.slides-table th {
    background-color: var(--color-bg-light);
    color: #31333F;
    font-weight: 600;
    padding: 12px;
    text-align: left;
    border: 1px solid var(--color-border);
    white-space: nowrap;
}
.slides-table td {
    padding: 12px;
    border: 1px solid var(--color-border);
    vertical-align: top;
    word-wrap: break-word;
    white-space: pre-wrap;
    line-height: 1.6;
    position: relative;
}
.slides-table tr:nth-child(even) {
    background-color: #f9f9f9;
}
.slides-table tr:hover {
    background-color: var(--color-bg-light);
}
.col-slide-no { width: 80px; text-align: center; }
.col-duration { width: 80px; text-align: center; }
.col-narration { width: calc((100% - 160px) / 2); }
.col-video-instruction-ja { width: calc((100% - 160px) * 0.35); }
.col-video-instruction-en { width: calc((100% - 160px) * 0.15); }
.copy-btn-cell {
    position: absolute;
    top: 4px; right: 4px;
    background-color: var(--color-bg-light);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    opacity: 0.7;
}
.copy-btn-cell:hover { opacity: 1; background-color: #e0e2e6; }
.cell-content-wrapper { padding-right: 60px; }
"""


def inject_slides_table_styles():
    """スライドテーブル用CSSを追加注入"""
    st.markdown(f"<style>{SLIDES_TABLE_CSS}</style>", unsafe_allow_html=True)
