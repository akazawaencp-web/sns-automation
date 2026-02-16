"""
アカウント管理ページ

60アカウントの一覧表示・作成・削除・進捗管理
"""

import streamlit as st
from pathlib import Path
import json
from datetime import datetime
import pandas as pd
from sns_automation.utils import StateManager


def main():
    st.set_page_config(
        page_title="アカウント管理 - SNS Automation",
        page_icon="▲",
        layout="wide",
    )

    # シンプルで洗練されたCSS
    st.markdown("""
        <style>
        /* メインコンテンツエリア */
        .block-container, [data-testid="block-container"] {
            background: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(10px) !important;
            border-radius: 20px !important;
            padding: 2rem !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06) !important;
        }

        .page-header {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            color: #121213 !important;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }

        .page-subtitle {
            color: #828282 !important;
            font-size: 1.05rem !important;
            margin-bottom: 2rem;
        }

        .stButton > button {
            border-radius: 2.9rem !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #ea8768 0%, #33b6de 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(234, 135, 104, 0.3) !important;
        }

        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 6px 20px rgba(234, 135, 104, 0.4) !important;
            transform: translateY(-1px) !important;
        }

        .stTextInput > div > div > input {
            border-radius: 1rem !important;
            border: 1px solid #d0d0d0 !important;
            background-color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-header">アカウント管理</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">最大60アカウントを一元管理。進捗状況を可視化し、効率的な運用をサポート。</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 状態ディレクトリ
    state_dir = Path.home() / ".sns-automation" / "states"
    state_dir.mkdir(parents=True, exist_ok=True)

    # アクションボタン - vertical_alignmentで高さ揃え
    col1, col2, col3 = st.columns([2, 1, 1], vertical_alignment="bottom")

    with col1:
        st.markdown("### プロジェクト一覧")

    with col2:
        if st.button("更新", use_container_width=True):
            st.rerun()

    with col3:
        if st.button("新規作成", use_container_width=True, type="primary"):
            st.session_state.show_create_dialog = True

    # 新規作成ダイアログ - containerでカード風に
    if st.session_state.get("show_create_dialog", False):
        with st.container(border=True):
            with st.form("create_project_form"):
                st.subheader("新規プロジェクト作成")

                project_name = st.text_input(
                    "プロジェクト名",
                    placeholder="例: beauty-account-01",
                    help="半角英数字、ハイフン、アンダースコアのみ使用可能"
                )

                description = st.text_area(
                    "説明（任意）",
                    placeholder="このアカウントの概要や目的を記入してください"
                )

                col1, col2 = st.columns(2, vertical_alignment="center")

                with col1:
                    submitted = st.form_submit_button("作成", use_container_width=True, type="primary")

                with col2:
                    cancelled = st.form_submit_button("キャンセル", use_container_width=True)

            if submitted:
                if not project_name:
                    st.error("プロジェクト名を入力してください")
                elif not _is_valid_project_name(project_name):
                    st.error("プロジェクト名は半角英数字、ハイフン、アンダースコアのみ使用できます")
                elif project_name in sm_list.list_all_projects():
                    st.error(f"プロジェクト「{project_name}」は既に存在します")
                else:
                    # StateManagerで初期状態を保存（ローカル + Google Sheets）
                    sm_new = StateManager(project_name)
                    sm_new.save_state(
                        chapter=0,
                        step="created",
                        data={},
                        metadata={"description": description, "created_at": datetime.now().isoformat()},
                    )

                    st.success(f"プロジェクト「{project_name}」を作成しました")
                    st.session_state.show_create_dialog = False
                    st.rerun()

            if cancelled:
                st.session_state.show_create_dialog = False
                st.rerun()

    st.markdown("---")

    # プロジェクト一覧を取得（StateManager経由でローカル + Google Sheets）
    sm_list = StateManager()
    project_names_all = sm_list.list_all_projects()

    if not project_names_all:
        st.info("プロジェクトがまだ作成されていません。「新規作成」ボタンからプロジェクトを作成してください。")
        return

    # フィルター・ソート - vertical_alignmentで高さ揃え
    col1, col2, col3 = st.columns(3, vertical_alignment="bottom")

    with col1:
        search_query = st.text_input("検索", placeholder="プロジェクト名で検索")

    with col2:
        filter_status = st.selectbox(
            "状態でフィルター",
            ["全て", "未着手", "戦略設計済み", "コンテンツ生成済み"]
        )

    with col3:
        sort_by = st.selectbox(
            "並び順",
            ["更新日時（新しい順）", "更新日時（古い順）", "プロジェクト名（昇順）", "プロジェクト名（降順）"]
        )

    # プロジェクトデータを読み込み（StateManager経由）
    projects = []
    for pname in project_names_all:
        try:
            sm_item = StateManager(pname)
            state = sm_item.load_state()
            if not state:
                continue

            projects.append({
                "name": state.get("project_name", pname),
                "description": state.get("metadata", {}).get("description", state.get("description", "")),
                "chapter": state.get("last_chapter", 0),
                "step": state.get("last_step", ""),
                "updated_at": state.get("updated_at", ""),
                "created_at": state.get("metadata", {}).get("created_at", state.get("created_at", "")),
                "ideas_count": len(state.get("data", {}).get("ideas", [])),
                "scripts_count": len(state.get("data", {}).get("scripts", [])),
            })
        except:
            continue

    # フィルタリング
    if search_query:
        projects = [p for p in projects if search_query.lower() in p["name"].lower()]

    if filter_status == "未着手":
        projects = [p for p in projects if p["chapter"] == 0]
    elif filter_status == "戦略設計済み":
        projects = [p for p in projects if p["chapter"] == 1]
    elif filter_status == "コンテンツ生成済み":
        projects = [p for p in projects if p["chapter"] == 3]

    # ソート
    if sort_by == "更新日時（新しい順）":
        projects = sorted(projects, key=lambda x: x["updated_at"], reverse=True)
    elif sort_by == "更新日時（古い順）":
        projects = sorted(projects, key=lambda x: x["updated_at"])
    elif sort_by == "プロジェクト名（昇順）":
        projects = sorted(projects, key=lambda x: x["name"])
    elif sort_by == "プロジェクト名（降順）":
        projects = sorted(projects, key=lambda x: x["name"], reverse=True)

    # カード形式で表示
    st.markdown(f"**{len(projects)}件のプロジェクト**")

    # グリッドレイアウト（3列）
    cols_per_row = 3
    for i in range(0, len(projects), cols_per_row):
        cols = st.columns(cols_per_row)

        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(projects):
                break

            project = projects[idx]

            with col:
                _render_project_card(project)

    st.markdown("---")

    # 一括削除 - containerでカード風に
    st.markdown("### 危険な操作")

    with st.container(border=True):
        with st.expander("一括削除"):
            st.warning("この操作は元に戻せません。慎重に実行してください。")

            delete_all = st.checkbox("全てのプロジェクトを削除することを理解しました")

            if st.button("全てのプロジェクトを削除", disabled=not delete_all, type="primary"):
                for pname in project_names_all:
                    sm_del = StateManager(pname)
                    sm_del.delete_state()

                st.success("全てのプロジェクトを削除しました")
                st.rerun()


def _is_valid_project_name(name: str) -> bool:
    """
    プロジェクト名が有効か検証

    Args:
        name: プロジェクト名

    Returns:
        有効な場合True
    """
    import re
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", name))


def _render_project_card(project: dict):
    """
    プロジェクトカードを描画

    Args:
        project: プロジェクト情報
    """
    # 進捗状況のバッジ
    chapter = project["chapter"]

    if chapter == 0:
        status_badge = "未着手"
        status_color = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)"
    elif chapter == 1:
        status_badge = "戦略設計済み"
        status_color = "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
    elif chapter == 3:
        status_badge = "コンテンツ生成済み"
        status_color = "linear-gradient(135deg, #10b981 0%, #059669 100%)"
    else:
        status_badge = "進行中"
        status_color = "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)"

    # 美しいカードのHTML（hover効果はCSSで実装）
    card_id = f"project-card-{project['name'].replace('_', '-')}"
    st.markdown(f"""
        <style>
        #{card_id} {{
            padding: 1.8rem;
            border-radius: 1.5rem;
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid rgba(234, 135, 104, 0.1);
            margin-bottom: 1.5rem;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        #{card_id}:hover {{
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(234, 135, 104, 0.15);
        }}
        </style>
        <div id="{card_id}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0; font-size: 1.3rem; font-weight: 600; color: #121213;">{project['name']}</h3>
                <span style="
                    padding: 0.4rem 1rem;
                    border-radius: 20px;
                    background: {status_color};
                    color: white;
                    font-size: 0.85rem;
                    font-weight: 500;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                ">{status_badge}</span>
            </div>
            <p style="color: #666; font-size: 0.95rem; margin: 0.8rem 0; line-height: 1.6;">
                {project['description'] if project['description'] else '<em style="color: #999;">説明なし</em>'}
            </p>
            <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-around; font-size: 0.9rem;">
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: 700; background: linear-gradient(135deg, #ea8768 0%, #33b6de 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{project['ideas_count']}</div>
                        <div style="color: #999; font-size: 0.8rem; margin-top: 0.3rem;">企画</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: 700; background: linear-gradient(135deg, #ea8768 0%, #33b6de 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{project['scripts_count']}</div>
                        <div style="color: #999; font-size: 0.8rem; margin-top: 0.3rem;">台本</div>
                    </div>
                </div>
                <div style="margin-top: 1rem; text-align: center; font-size: 0.8rem; color: #999;">
                    更新: {_format_datetime(project['updated_at'])}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # アクションボタン - vertical_alignmentで高さ揃え
    col1, col2, col3 = st.columns(3, vertical_alignment="center")

    with col1:
        if st.button("詳細", key=f"detail_{project['name']}", use_container_width=True):
            st.session_state.selected_project = project["name"]
            # 詳細ページに遷移（今後実装）
            st.info(f"プロジェクト「{project['name']}」の詳細ページは今後実装予定です")

    with col2:
        if st.button("編集", key=f"edit_{project['name']}", use_container_width=True):
            # 編集ページに遷移（今後実装）
            st.info("編集機能は今後実装予定です")

    with col3:
        if st.button("削除", key=f"delete_{project['name']}", use_container_width=True):
            # 削除確認
            with st.expander("削除の確認"):
                st.warning(f"プロジェクト「{project['name']}」を削除しますか？この操作は元に戻せません。")

                if st.button(f"はい、削除します", key=f"confirm_delete_{project['name']}", type="primary"):
                    sm_del = StateManager(project['name'])
                    sm_del.delete_state()
                    st.success(f"プロジェクト「{project['name']}」を削除しました")
                    st.rerun()


def _format_datetime(dt_str: str) -> str:
    """
    日時文字列をフォーマット

    Args:
        dt_str: ISO形式の日時文字列

    Returns:
        フォーマット済みの日時文字列
    """
    if not dt_str:
        return "不明"

    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y/%m/%d %H:%M")
    except:
        return dt_str


if __name__ == "__main__":
    main()
