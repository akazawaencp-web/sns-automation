# SNS Automation Platform - 開発ガイド

## プロジェクト概要

SNSアカウント構築・運用を自動化するStreamlitアプリ。Claude APIで戦略設計・企画・台本を自動生成し、Google Sheetsでデータ永続化。

## 技術スタック

- **UI**: Streamlit (マルチページ構成)
- **AI**: Claude API (Anthropic)
- **データ**: Google Sheets + ローカルJSON
- **チャート**: Plotly
- **テーマカラー**: コーラル `#ea8768` ↔ スカイブルー `#33b6de`

## ディレクトリ構成（Web UI部分）

```
src/sns_automation/web/
├── app.py                      # ホームページ（ダッシュボード）
├── components/
│   ├── __init__.py             # 全コンポーネントのexport
│   ├── styles.py               # ★ 全CSS一元管理
│   ├── shared.py               # ★ 共有UIコンポーネント
│   └── feedback.py             # フィードバックフォーム
└── pages/
    ├── 1_アカウント管理.py      # アカウントCRUD + テーブル表示
    ├── 2_戦略設計.py            # ウィザード形式の戦略設計
    ├── 3_コンテンツ量産.py      # 企画20案 + 台本一括生成
    └── 4_進捗管理.py            # ダッシュボード + 詳細チェック
```

## CSS設計（重要）

### 原則: CSSは `styles.py` に集約

各ページに `<style>` を直接書かない。代わりに:

```python
from sns_automation.web.components import inject_styles
inject_styles()  # これ1行で全共通CSSが適用される
```

### styles.py の構成

| セクション | 内容 |
|-----------|------|
| `_CSS_VARIABLES` | `--color-coral`, `--color-sky`, `--radius-*`, `--shadow-*` 等 |
| `_BASE_LAYOUT` | `.block-container` のガラスモーフィズム |
| `_TYPOGRAPHY` | `.page-header`, `.main-header`, `.section-header` 等 |
| `_SIDEBAR` | ナビリンクのホバー/アクティブ |
| `_BUTTONS` | pill型、primaryグラデーション |
| `_INPUTS` | focus時コーラルボーダー + リング |
| `_SELECTBOX` | ホバー/フォーカスでコーラルアクセント |
| `_CHECKBOX` | チェック時グラデーション背景 |
| `_RADIO` | 選択時アクセント背景 |
| `_EXPANDER` | コーラルボーダー、ホバーシャドウ |
| `_TABS` | アクティブにコーラル下線 |
| `_METRICS` | `::before` でグラデーションバー、ホバーリフト |
| `_TABLE` | `.app-table` 統一クラス + セルクラス群 |
| `_ANIMATIONS` | `fadeInUp`, `staggerFadeIn`, `spin` |

### ページ固有CSSが必要な場合

どうしてもページ固有のスタイルが必要な場合のみインラインOK（例: 戦略設計のラジオ3列グリッド）。ただし `styles.py` に追加できないか先に検討すること。

### 追加CSS注入関数

- `inject_feature_card_styles()` - ホームページの機能カード用（app.pyのみ）
- `inject_slides_table_styles()` - スライド詳細テーブル用（3_コンテンツ量産.pyのみ）

## 共有コンポーネント (`shared.py`)

| 関数 | 用途 |
|------|------|
| `render_loading(container, title, subtitle)` | アニメーション付きローディング表示 |
| `render_page_header(title, subtitle)` | 全ページ共通のヘッダー |
| `render_status_badge(label, color, bg_color)` | ステータスバッジHTML生成 |

## 新しいページを追加する手順

1. `pages/` に `N_ページ名.py` を作成
2. 以下のボイラープレートで開始:

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
    # ここにページ固有のロジック

if __name__ == "__main__":
    main()
```

3. テーブルを使う場合は `<div class="app-table">` でラップ
4. ローディングが必要なら `render_loading(container, title, subtitle)` を使う

## テーブルのCSSクラス

| クラス | 用途 |
|-------|------|
| `.app-table` | テーブル全体のラッパー |
| `.cell-name` | 名前列（太字、ダーク） |
| `.cell-nowrap` | 折り返し禁止 |
| `.cell-truncate` | 長いテキストを省略 |
| `.cell-center` | 中央揃え |
| `.cell-meta` | 補足情報（小さめ、グレー） |
| `.empty-placeholder` | 空データの「-」表示 |
| `.code-block` | コード/プロンプト表示ブロック |

## データフロー

```
Google Sheets ←→ StateManager ←→ ローカルJSON
                       ↕
                  Streamlit UI
```

- `StateManager`: ローカル + Google Sheets の二重永続化
- `ProgressManager`: 進捗データの管理（手動ステップ + KPI）
- キャッシュ: `st.session_state` にTTL付きで保持（60秒）

## 注意事項

- `components.html()` 内のスタイルは iframe 内なので `styles.py` とは別スコープ。コピーボタン等のインラインスタイルは残してOK
- テーマカラー変更時は `config.toml` の `primaryColor` と `styles.py` の `_CSS_VARIABLES` の両方を更新すること
