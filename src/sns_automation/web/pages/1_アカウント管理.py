"""
アカウント管理ページ

60アカウントの一覧表示・作成・削除・進捗管理
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
import pandas as pd
from sns_automation.utils import StateManager
from sns_automation.web.components import render_feedback_form


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

    # フィードバックフォーム
    render_feedback_form()

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

                # 担当者選択
                members = ["Ryoji", "Futa", "Maho", "Toshi"]
                owner = st.selectbox("担当者", members)

                col1, col2 = st.columns(2, vertical_alignment="center")

                with col1:
                    submitted = st.form_submit_button("作成", use_container_width=True, type="primary")

                with col2:
                    cancelled = st.form_submit_button("キャンセル", use_container_width=True)

            if submitted:
                # プロジェクト名を自動生成（担当者名-account-連番）
                existing_projects = StateManager().list_all_projects()
                owner_lower = owner.lower()
                owner_projects = [p for p in existing_projects if p.startswith(f"{owner_lower}-")]
                next_num = len(owner_projects) + 1
                project_name = f"{owner_lower}-account-{next_num:02d}"

                if project_name in existing_projects:
                    st.error(f"プロジェクト「{project_name}」は既に存在します")
                else:
                    # StateManagerで初期状態を保存（ローカル + Google Sheets）
                    sm_new = StateManager(project_name)
                    sm_new.save_state(
                        chapter=0,
                        step="created",
                        data={},
                        metadata={"owner": owner, "created_at": datetime.now().isoformat()},
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

            # 概要を戦略設計のコンセプト・ターゲットから自動取得
            metadata = state.get("metadata", {})
            data = state.get("data", {})
            concept = metadata.get("concept", "") or data.get("strategy", {}).get("selected_concept", "") or data.get("selected_concept", "")
            target = metadata.get("target", "") or data.get("strategy", {}).get("target", "") or data.get("target", "")
            if concept:
                summary = concept
            elif target:
                summary = target
            else:
                summary = ""

            projects.append({
                "name": state.get("project_name", pname),
                "summary": summary,
                "chapter": state.get("last_chapter", 0),
                "step": state.get("last_step", ""),
                "updated_at": state.get("updated_at", ""),
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

    # 表形式で表示
    st.markdown(f"**{len(projects)}件のプロジェクト**")

    if projects:
        # テーブルデータを作成
        table_data = []
        for p in projects:
            chapter = p["chapter"]
            if chapter == 0:
                status = "未着手"
            elif chapter == 1:
                status = "戦略設計済み"
            elif chapter == 3:
                status = "コンテンツ生成済み"
            else:
                status = "進行中"

            table_data.append({
                "アカウント名": p["name"],
                "概要": p["summary"] if p["summary"] else "-",
                "ステータス": status,
                "更新日": _format_datetime(p["updated_at"]),
            })

        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "アカウント名": st.column_config.TextColumn(width="medium"),
                "概要": st.column_config.TextColumn(width="large"),
                "ステータス": st.column_config.TextColumn(width="small"),
                "更新日": st.column_config.TextColumn(width="small"),
            },
        )

    st.markdown("---")

    # 個別削除
    with st.expander("プロジェクトの削除"):
        delete_target = st.selectbox(
            "削除するプロジェクト",
            ["選択してください"] + [p["name"] for p in projects],
            key="delete_target",
        )
        if delete_target != "選択してください":
            if st.button(f"「{delete_target}」を削除", type="primary"):
                sm_del = StateManager(delete_target)
                sm_del.delete_state()
                st.success(f"プロジェクト「{delete_target}」を削除しました")
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
