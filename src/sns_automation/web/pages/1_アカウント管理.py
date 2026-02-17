"""
アカウント管理ページ

60アカウントの一覧表示・作成・削除・進捗管理
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
from html import escape as html_escape
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

    # プロジェクトデータを読み込み（StateManager経由）
    active_projects = []
    archived_projects = []
    all_owners = set()
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

            owner = metadata.get("owner", "")
            if owner:
                all_owners.add(owner)

            project_data = {
                "name": state.get("project_name", pname),
                "summary": summary,
                "owner": owner,
                "chapter": state.get("last_chapter", 0),
                "step": state.get("last_step", ""),
                "updated_at": state.get("updated_at", ""),
            }

            if metadata.get("archived", False):
                archived_projects.append(project_data)
            else:
                active_projects.append(project_data)
        except:
            continue

    # フィルター・ソート - vertical_alignmentで高さ揃え
    col1, col2, col3, col4 = st.columns(4, vertical_alignment="bottom")

    with col1:
        search_query = st.text_input("検索", placeholder="プロジェクト名で検索")

    with col2:
        owner_options = ["全員"] + sorted(all_owners)
        filter_owner = st.selectbox("担当者で絞り込み", owner_options)

    with col3:
        filter_status = st.selectbox(
            "状態でフィルター",
            ["全て", "未着手", "戦略設計済み", "コンテンツ生成済み"]
        )

    with col4:
        sort_by = st.selectbox(
            "並び順",
            [
                "更新日時（新しい順）", "更新日時（古い順）",
                "プロジェクト名（昇順）", "プロジェクト名（降順）",
                "ステータス順（未着手→完了）", "ステータス順（完了→未着手）",
            ]
        )

    projects = active_projects

    # フィルタリング
    if search_query:
        projects = [p for p in projects if search_query.lower() in p["name"].lower()]

    if filter_owner != "全員":
        projects = [p for p in projects if p["owner"] == filter_owner]

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
    elif sort_by == "ステータス順（未着手→完了）":
        projects = sorted(projects, key=lambda x: x["chapter"])
    elif sort_by == "ステータス順（完了→未着手）":
        projects = sorted(projects, key=lambda x: x["chapter"], reverse=True)

    # 表形式で表示
    st.markdown(f"**{len(projects)}件のプロジェクト**")

    if projects:
        _render_project_table(projects)

    # アーカイブ済みセクション
    if archived_projects:
        with st.expander(f"アーカイブ済み（{len(archived_projects)}件）"):
            _render_project_table(archived_projects, greyed_out=True)
            st.markdown("")
            restore_target = st.selectbox(
                "復元するプロジェクト",
                ["選択してください"] + [p["name"] for p in archived_projects],
                key="restore_target",
            )
            if restore_target != "選択してください":
                if st.button(f"「{restore_target}」を戻す", key="restore_btn"):
                    sm_restore = StateManager(restore_target)
                    state = sm_restore.load_state()
                    if state:
                        metadata = state.get("metadata", {})
                        metadata["archived"] = False
                        sm_restore.save_state(
                            chapter=state.get("last_chapter", 0),
                            step=state.get("last_step", ""),
                            data=state.get("data", {}),
                            metadata=metadata,
                        )
                        st.success(f"「{restore_target}」を復元しました")
                        st.rerun()

    st.markdown("---")

    # プロジェクトの管理（アーカイブ + 削除）
    with st.expander("プロジェクトの管理"):
        mgmt_col1, mgmt_col2 = st.columns(2)

        with mgmt_col1:
            st.markdown("**アーカイブする**")
            archive_target = st.selectbox(
                "アーカイブするプロジェクト",
                ["選択してください"] + [p["name"] for p in active_projects],
                key="archive_target",
            )
            if archive_target != "選択してください":
                if st.button(f"「{archive_target}」をアーカイブ", key="archive_btn"):
                    sm_archive = StateManager(archive_target)
                    state = sm_archive.load_state()
                    if state:
                        metadata = state.get("metadata", {})
                        metadata["archived"] = True
                        sm_archive.save_state(
                            chapter=state.get("last_chapter", 0),
                            step=state.get("last_step", ""),
                            data=state.get("data", {}),
                            metadata=metadata,
                        )
                        st.success(f"「{archive_target}」をアーカイブしました")
                        st.rerun()

        with mgmt_col2:
            st.markdown("**削除する**")
            all_project_names = [p["name"] for p in active_projects] + [p["name"] for p in archived_projects]
            delete_target = st.selectbox(
                "削除するプロジェクト",
                ["選択してください"] + all_project_names,
                key="delete_target",
            )
            if delete_target != "選択してください":
                if st.button(f"「{delete_target}」を削除", type="primary", key="delete_btn"):
                    sm_del = StateManager(delete_target)
                    sm_del.delete_state()
                    st.success(f"「{delete_target}」を削除しました")
                    st.rerun()


def _clean_summary(text: str) -> str:
    """概要テキストからアスタリスク等のマークダウン記号を除去"""
    if not text:
        return ""
    return text.replace("*", "").replace("#", "").strip()


def _render_project_table(projects: list, greyed_out: bool = False):
    """プロジェクト一覧をスタイル付きHTMLテーブルで描画"""

    status_styles = {
        0: ("未着手", "#94a3b8", "rgba(148,163,184,0.1)"),
        1: ("戦略設計済み", "#f59e0b", "rgba(245,158,11,0.1)"),
        3: ("コンテンツ生成済み", "#10b981", "rgba(16,185,129,0.1)"),
    }
    default_status = ("進行中", "#3b82f6", "rgba(59,130,246,0.1)")

    rows = []
    for p in projects:
        chapter = p["chapter"]
        s_label, s_color, s_bg = status_styles.get(chapter, default_status)
        name = html_escape(p["name"])
        owner = html_escape(p.get("owner", "")) or '<span style="color:#ccc;">-</span>'
        summary = html_escape(_clean_summary(p["summary"])) if p["summary"] else '<span style="color:#ccc;">-</span>'
        last_op = _format_last_operation(p["chapter"], p["step"], p["updated_at"])
        badge = f'<span style="display:inline-block;padding:0.3rem 0.85rem;border-radius:20px;font-size:0.8rem;font-weight:600;color:{s_color};background:{s_bg};">{s_label}</span>'
        rows.append(
            f"<tr>"
            f'<td style="padding:0.85rem 1rem;font-weight:600;color:#1e293b;white-space:nowrap;">{name}</td>'
            f'<td style="padding:0.85rem 1rem;color:#374151;font-size:0.9rem;white-space:nowrap;">{owner}</td>'
            f'<td style="padding:0.85rem 1rem;color:#374151;font-size:0.9rem;max-width:350px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{summary}</td>'
            f'<td style="padding:0.85rem 1rem;text-align:center;">{badge}</td>'
            f'<td style="padding:0.85rem 1rem;color:#4b5563;font-size:0.85rem;text-align:center;white-space:nowrap;">{last_op}</td>'
            f"</tr>"
        )
    rows_html = "\n".join(rows)

    th_style = "padding:0.9rem 1rem;font-size:0.8rem;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:0.05em;border-bottom:2px solid rgba(234,135,104,0.15);"

    wrap_class = "proj-table-wrap-archived" if greyed_out else "proj-table-wrap"
    opacity_style = "opacity:0.5;" if greyed_out else ""

    st.markdown(
        "<style>"
        ".proj-table-wrap,.proj-table-wrap-archived{border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04),0 4px 16px rgba(0,0,0,0.06);border:1px solid rgba(0,0,0,0.06);background:white;}"
        ".proj-table-wrap table,.proj-table-wrap-archived table{width:100%;border-collapse:collapse;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}"
        ".proj-table-wrap thead tr,.proj-table-wrap-archived thead tr{background:linear-gradient(135deg,rgba(234,135,104,0.08) 0%,rgba(51,182,222,0.08) 100%);}"
        ".proj-table-wrap tbody tr,.proj-table-wrap-archived tbody tr{transition:background-color 0.2s ease;}"
        ".proj-table-wrap tbody tr:hover,.proj-table-wrap-archived tbody tr:hover{background-color:rgba(234,135,104,0.04);}"
        ".proj-table-wrap tbody tr:not(:last-child) td,.proj-table-wrap-archived tbody tr:not(:last-child) td{border-bottom:1px solid rgba(0,0,0,0.04);}"
        ".proj-table-wrap-archived{opacity:0.5;}"
        "</style>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="{wrap_class}" style="{opacity_style}"><table>'
        f'<thead><tr>'
        f'<th style="{th_style}text-align:left;">アカウント名</th>'
        f'<th style="{th_style}text-align:left;">担当者</th>'
        f'<th style="{th_style}text-align:left;">概要</th>'
        f'<th style="{th_style}text-align:center;">ステータス</th>'
        f'<th style="{th_style}text-align:center;">最終操作</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True,
    )


def _format_last_operation(chapter: int, step: str, dt_str: str) -> str:
    """chapterとstepから最終操作名を推定し、日付と合わせて表示"""
    # 操作名の推定
    if chapter == 0 and step == "created":
        op_name = "作成"
    elif chapter == 1:
        op_name = "戦略設計"
    elif chapter == 2:
        op_name = "企画生成"
    elif chapter == 3:
        op_name = "台本生成"
    elif step:
        op_name = step
    else:
        op_name = "更新"

    # 日付フォーマット
    if not dt_str:
        return op_name

    try:
        dt = datetime.fromisoformat(dt_str)
        return f"{op_name} {dt.strftime('%m/%d')}"
    except:
        return op_name


if __name__ == "__main__":
    main()
