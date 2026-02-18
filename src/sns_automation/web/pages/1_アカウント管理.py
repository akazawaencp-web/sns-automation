"""
アカウント管理ページ

60アカウントの一覧表示・作成・削除・進捗管理
"""

import json
import logging
import time
import streamlit as st
from pathlib import Path
from datetime import datetime
from html import escape as html_escape
from sns_automation.utils import StateManager
from sns_automation.web.components import render_feedback_form

logger = logging.getLogger(__name__)

# 終了済みプロジェクト名を保存するローカルファイル
_ENDED_FILE = Path.home() / ".sns-automation" / "ended_projects.json"

# データキャッシュの有効期間（秒）
_CACHE_TTL = 60


@st.cache_resource(show_spinner=False)
def _get_spreadsheet():
    """
    Google Sheetsのスプレッドシート接続をキャッシュ。
    認証は1回だけ行い、以降はキャッシュされた接続を再利用する。
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        if not hasattr(st, "secrets") or "google_service_account" not in st.secrets:
            return None

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
        logger.info("Google Sheets接続をキャッシュしました")
        return spreadsheet
    except Exception as e:
        logger.warning(f"Google Sheets接続に失敗: {e}")
        return None


def _load_all_project_data(force_refresh: bool = False) -> tuple[list[dict], set]:
    """
    全プロジェクトデータと終了セットをまとめて読み込む。
    キャッシュを使い、不要なAPIコールを排除する。

    Args:
        force_refresh: Trueの場合キャッシュを無視して再取得

    Returns:
        (全プロジェクトのstateリスト, 終了済みプロジェクト名のset)
    """
    # キャッシュチェック
    cache_key = "_project_data_cache"
    cache_time_key = "_project_data_cache_time"

    if not force_refresh:
        cached = st.session_state.get(cache_key)
        cached_time = st.session_state.get(cache_time_key, 0)
        if cached and (time.time() - cached_time) < _CACHE_TTL:
            return cached

    state_dir = Path.home() / ".sns-automation" / "states"
    states = {}  # project_name -> state dict
    ended_set = set()

    # --- Google Sheetsから一括取得（キャッシュ済み接続を使用）---
    spreadsheet = _get_spreadsheet()
    if spreadsheet:
        # 1) プロジェクトデータ一括取得（1回のAPIコール）
        try:
            sheet = spreadsheet.worksheet("sns_automation_states")
            all_records = sheet.get_all_records()
            for record in all_records:
                pname = record.get("project_name")
                if not pname:
                    continue
                pname = str(pname)
                try:
                    data = json.loads(record.get("data_json", "{}") or "{}")
                    metadata = json.loads(record.get("metadata_json", "{}") or "{}")
                    states[pname] = {
                        "project_name": pname,
                        "last_chapter": record.get("last_chapter", 0),
                        "last_step": record.get("last_step", ""),
                        "data": data,
                        "metadata": metadata,
                        "updated_at": record.get("updated_at", ""),
                    }
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"プロジェクト「{pname}」のJSONパースエラー: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Google Sheetsからの一括読み込みに失敗: {e}")

        # 2) 終了済みリスト取得（1回のAPIコール）
        try:
            ended_sheet = spreadsheet.worksheet("ended_projects")
            values = ended_sheet.col_values(1)
            ended_set.update(v for v in values[1:] if v)
        except Exception:
            pass  # ワークシートが存在しない場合はスキップ

    # --- ローカルファイルから補完（Sheetsにないプロジェクト用）---
    if state_dir.exists():
        for state_file in state_dir.glob("*.json"):
            pname = state_file.stem
            if pname in states:
                continue  # Sheetsから取得済み
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                states[pname] = state
            except Exception:
                continue

    # ローカルの終了リストも読み込み
    if _ENDED_FILE.exists():
        try:
            with open(_ENDED_FILE, "r", encoding="utf-8") as f:
                ended_set.update(json.load(f))
        except Exception:
            pass

    result = (list(states.values()), ended_set)

    # キャッシュに保存
    st.session_state[cache_key] = result
    st.session_state[cache_time_key] = time.time()

    return result


def _invalidate_cache():
    """データキャッシュを無効化する"""
    st.session_state.pop("_project_data_cache", None)
    st.session_state.pop("_project_data_cache_time", None)


def _save_ended_set(ended: set) -> None:
    """終了済みプロジェクト名のセットを保存（ローカル + Google Sheets）"""
    ended_sorted = sorted(ended)

    # ローカルファイルに保存
    _ENDED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_ENDED_FILE, "w", encoding="utf-8") as f:
        json.dump(ended_sorted, f, ensure_ascii=False)

    # Google Sheetsにも保存（キャッシュ済み接続を使用）
    spreadsheet = _get_spreadsheet()
    if spreadsheet:
        try:
            try:
                sheet = spreadsheet.worksheet("ended_projects")
            except Exception:
                sheet = spreadsheet.add_worksheet(
                    title="ended_projects", rows=200, cols=1
                )
            # シートをクリアして再書き込み
            sheet.clear()
            sheet.update_cell(1, 1, "project_name")
            if ended_sorted:
                cells = [[name] for name in ended_sorted]
                sheet.update(f"A2:A{len(cells) + 1}", cells)
        except Exception as e:
            logger.warning(f"Google Sheetsへのended保存失敗: {e}")

    # キャッシュを無効化（次回読み込み時に最新データを取得）
    _invalidate_cache()


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
            _invalidate_cache()
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
                # キャッシュ済みデータからプロジェクト一覧を取得（APIコールなし）
                cached_states, _ = _load_all_project_data()
                existing_projects = {s["project_name"] for s in cached_states}
                # ローカルファイルも確認
                for sf in state_dir.glob("*.json"):
                    existing_projects.add(sf.stem)

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
                    _invalidate_cache()
                    st.rerun()

            if cancelled:
                st.session_state.show_create_dialog = False
                st.rerun()

    st.markdown("---")

    # 全プロジェクトデータ + 終了セットを一括読み込み（APIコール最小化）
    all_states, ended_set = _load_all_project_data()

    if not all_states:
        st.info("プロジェクトがまだ作成されていません。「新規作成」ボタンからプロジェクトを作成してください。")
        return

    # プロジェクトデータを整形
    all_projects = []
    all_owners = set()
    for state in all_states:
        try:
            pname = state.get("project_name", "")
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

            all_projects.append({
                "name": pname,
                "summary": summary,
                "owner": owner,
                "chapter": int(state.get("last_chapter", 0)),
                "step": str(state.get("last_step", "")),
                "updated_at": state.get("updated_at", ""),
                "ended": pname in ended_set,
            })
        except Exception as e:
            st.warning(f"プロジェクト「{state.get('project_name', '?')}」の処理エラー: {e}")
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
            ["全て（終了除く）", "全て（終了含む）", "未着手", "戦略設計済み", "コンテンツ生成済み", "終了"]
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

    projects = all_projects

    # フィルタリング
    if search_query:
        projects = [p for p in projects if search_query.lower() in p["name"].lower()]

    if filter_owner != "全員":
        projects = [p for p in projects if p["owner"] == filter_owner]

    if filter_status == "全て（終了除く）":
        projects = [p for p in projects if not p["ended"]]
    elif filter_status == "全て（終了含む）":
        pass  # 全件表示
    elif filter_status == "未着手":
        projects = [p for p in projects if p["chapter"] == 0 and not p["ended"]]
    elif filter_status == "戦略設計済み":
        projects = [p for p in projects if p["chapter"] == 1 and not p["ended"]]
    elif filter_status == "コンテンツ生成済み":
        projects = [p for p in projects if p["chapter"] == 3 and not p["ended"]]
    elif filter_status == "終了":
        projects = [p for p in projects if p["ended"]]

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

    # 終了の管理
    non_ended = [p for p in all_projects if not p["ended"]]
    ended_list = [p for p in all_projects if p["ended"]]
    ended_count = len(ended_list)

    st.markdown("---")

    ended_label = f"終了の管理（{ended_count}件が終了中）" if ended_count else "終了の管理"
    with st.expander(ended_label):
        # 終了済み一覧と解除（先に表示）
        if ended_list:
            st.markdown(f"**終了済みプロジェクト（{ended_count}件）**")
            _render_project_table(ended_list)
            st.markdown("")
            reopen_targets = st.multiselect(
                "終了を解除するプロジェクトを選択",
                [p["name"] for p in ended_list],
                key="reopen_targets",
            )
            if reopen_targets:
                if st.button(f"{len(reopen_targets)}件の終了を解除する", key="reopen_btn"):
                    new_ended = ended_set - set(reopen_targets)
                    _save_ended_set(new_ended)
                    st.success(f"{len(reopen_targets)}件の終了を解除しました")
                    st.rerun()
            st.markdown("---")
        else:
            st.info("終了済みのプロジェクトはありません")

        # 終了にする
        st.markdown("**プロジェクトを終了にする**")
        end_targets = st.multiselect(
            "終了にするプロジェクトを選択",
            [p["name"] for p in non_ended],
            key="end_targets",
        )
        if end_targets:
            if st.button(f"{len(end_targets)}件を終了にする", key="end_btn"):
                new_ended = ended_set | set(end_targets)
                _save_ended_set(new_ended)
                st.success(f"{len(end_targets)}件を終了にしました")
                st.rerun()


def _clean_summary(text: str) -> str:
    """概要テキストからアスタリスク等のマークダウン記号を除去"""
    if not text:
        return ""
    return text.replace("*", "").replace("#", "").strip()


def _render_project_table(projects: list):
    """プロジェクト一覧をスタイル付きHTMLテーブルで描画"""

    status_styles = {
        0: ("未着手", "#94a3b8", "rgba(148,163,184,0.1)"),
        1: ("戦略設計済み", "#f59e0b", "rgba(245,158,11,0.1)"),
        3: ("コンテンツ生成済み", "#10b981", "rgba(16,185,129,0.1)"),
    }
    ended_status = ("終了", "#6b7280", "rgba(107,114,128,0.1)")
    default_status = ("進行中", "#3b82f6", "rgba(59,130,246,0.1)")

    rows = []
    for p in projects:
        chapter = p["chapter"]
        if p.get("ended"):
            s_label, s_color, s_bg = ended_status
        else:
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

    st.markdown(
        "<style>"
        ".proj-table-wrap{border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04),0 4px 16px rgba(0,0,0,0.06);border:1px solid rgba(0,0,0,0.06);background:white;}"
        ".proj-table-wrap table{width:100%;border-collapse:collapse;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}"
        ".proj-table-wrap thead tr{background:linear-gradient(135deg,rgba(234,135,104,0.08) 0%,rgba(51,182,222,0.08) 100%);}"
        ".proj-table-wrap tbody tr{transition:background-color 0.2s ease;}"
        ".proj-table-wrap tbody tr:hover{background-color:rgba(234,135,104,0.04);}"
        ".proj-table-wrap tbody tr:not(:last-child) td{border-bottom:1px solid rgba(0,0,0,0.04);}"
        "</style>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="proj-table-wrap"><table>'
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
