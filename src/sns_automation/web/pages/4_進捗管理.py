"""
進捗管理ページ

60アカウント運用の全工程（戦略設計→投稿→分析）を一元管理する。
ステップ1-3は自動検出、ステップ4-11は手動チェックで追跡。
"""

import json
import logging
import time
import streamlit as st
from pathlib import Path
from datetime import datetime
from html import escape as html_escape
from sns_automation.utils import StateManager
from sns_automation.utils.progress_manager import ProgressManager
from sns_automation.web.components import render_feedback_form, inject_styles, render_page_header

logger = logging.getLogger(__name__)

# データキャッシュの有効期間（秒）
_CACHE_TTL = 60

# 担当者リスト
_MEMBERS = ["Ryoji", "Futa", "Maho", "Toshi"]


# ─── Google Sheets接続キャッシュ ────────────────────────
@st.cache_resource(show_spinner=False)
def _get_spreadsheet():
    """Google Sheetsのスプレッドシート接続をキャッシュ"""
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
        return client.open_by_key(spreadsheet_id)
    except Exception as e:
        logger.warning(f"Google Sheets接続に失敗: {e}")
        return None


# ─── データ読み込み ─────────────────────────────────
def _load_all_data(force_refresh: bool = False):
    """
    全プロジェクトのstateデータと進捗データを一括読み込み（TTLキャッシュ付き）

    Returns:
        (project_states: dict[name, state], progress_data: dict[name, progress], ended_set: set)
    """
    cache_key = "_progress_page_cache"
    cache_time_key = "_progress_page_cache_time"

    if not force_refresh:
        cached = st.session_state.get(cache_key)
        cached_time = st.session_state.get(cache_time_key, 0)
        if cached and (time.time() - cached_time) < _CACHE_TTL:
            return cached

    project_states = {}
    progress_data = {}
    ended_set = set()

    # ─ Google Sheetsからバッチ取得 ─
    spreadsheet = _get_spreadsheet()
    if spreadsheet:
        # 1) sns_automation_states
        try:
            sheet = spreadsheet.worksheet("sns_automation_states")
            for record in sheet.get_all_records():
                pname = record.get("project_name")
                if not pname:
                    continue
                pname = str(pname)
                try:
                    data = json.loads(record.get("data_json", "{}") or "{}")
                    metadata = json.loads(record.get("metadata_json", "{}") or "{}")
                    project_states[pname] = {
                        "project_name": pname,
                        "last_chapter": record.get("last_chapter", 0),
                        "last_step": record.get("last_step", ""),
                        "data": data,
                        "metadata": metadata,
                        "updated_at": record.get("updated_at", ""),
                    }
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            logger.warning(f"sns_automation_states読み込み失敗: {e}")

        # 2) content_progress
        try:
            sheet = spreadsheet.worksheet("content_progress")
            for record in sheet.get_all_records():
                pname = record.get("project_name")
                if not pname:
                    continue
                pname = str(pname)
                try:
                    contents = json.loads(record.get("progress_json", "{}") or "{}")
                    progress_data[pname] = {
                        "project_name": pname,
                        "updated_at": record.get("updated_at", ""),
                        "contents": contents,
                    }
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception:
            pass  # シートがまだ無い場合

        # 3) ended_projects
        try:
            ended_sheet = spreadsheet.worksheet("ended_projects")
            values = ended_sheet.col_values(1)
            ended_set.update(v for v in values[1:] if v)
        except Exception:
            pass

    # ─ ローカルファイルから補完 ─
    state_dir = Path.home() / ".sns-automation" / "states"
    if state_dir.exists():
        for state_file in state_dir.glob("*.json"):
            pname = state_file.stem
            if pname in project_states:
                continue
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    project_states[pname] = json.load(f)
            except Exception:
                continue

    progress_dir = Path.home() / ".sns-automation" / "progress"
    if progress_dir.exists():
        for pf in progress_dir.glob("*.json"):
            pname = pf.stem
            if pname in progress_data:
                continue
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    progress_data[pname] = json.load(f)
            except Exception:
                continue

    # ローカルended
    ended_file = Path.home() / ".sns-automation" / "ended_projects.json"
    if ended_file.exists():
        try:
            with open(ended_file, "r", encoding="utf-8") as f:
                ended_set.update(json.load(f))
        except Exception:
            pass

    result = (project_states, progress_data, ended_set)
    st.session_state[cache_key] = result
    st.session_state[cache_time_key] = time.time()
    return result


def _invalidate_cache():
    """データキャッシュを無効化"""
    st.session_state.pop("_progress_page_cache", None)
    st.session_state.pop("_progress_page_cache_time", None)


# ─── ユーティリティ ────────────────────────────────
def _get_owner(state: dict) -> str:
    """プロジェクトの担当者を取得"""
    return state.get("metadata", {}).get("owner", "")


def _build_project_summary(project_states, progress_data, ended_set):
    """
    全プロジェクトのサマリーデータを構築

    Returns:
        list[dict] - 各プロジェクトの集約データ
    """
    summaries = []
    for pname, state in project_states.items():
        if pname in ended_set:
            continue

        owner = _get_owner(state)
        auto = ProgressManager.detect_auto_steps(state)
        progress = progress_data.get(pname, {}).get("contents", {})

        ideas_count = auto["ideas_count"]
        scripts = auto["scripts"]

        # 各ステップの完了カウント
        counts = {
            "script": 0,
            "midjourney": 0,
            "kling_ai": 0,
            "eleven_labo": 0,
            "vrew": 0,
            "capcut": 0,
            "posted": 0,
            "kpi": 0,
            "improvement": 0,
        }

        for i in range(ideas_count):
            idx = str(i)
            if scripts.get(idx):
                counts["script"] += 1
            content_progress = progress.get(idx, {})
            steps = content_progress.get("steps", {})
            for step_key in ProgressManager.MANUAL_STEPS:
                if step_key == "improvement":
                    continue
                if steps.get(step_key, {}).get("done"):
                    counts[step_key] += 1
            if steps.get("improvement", {}).get("done"):
                counts["improvement"] += 1
            if content_progress.get("kpi_records"):
                counts["kpi"] += 1

        summaries.append({
            "name": pname,
            "owner": owner,
            "strategy_done": auto["strategy_done"],
            "ideas_done": auto["ideas_done"],
            "ideas_count": ideas_count,
            "counts": counts,
        })

    return summaries


# ─── Tab 1: ダッシュボード ──────────────────────────
def _render_dashboard(project_states, progress_data, ended_set):
    """ダッシュボードタブを描画"""
    summaries = _build_project_summary(project_states, progress_data, ended_set)

    if not summaries:
        st.info("アクティブなプロジェクトがありません。")
        return

    # 上部メトリクス行
    total_accounts = len(summaries)
    total_contents = sum(s["ideas_count"] for s in summaries)
    total_posted = sum(s["counts"]["posted"] for s in summaries)
    total_all_done = 0
    for s in summaries:
        for i in range(s["ideas_count"]):
            idx = str(i)
            # 全ステップ完了 = 台本 + 全手動ステップ
            script_done = s["counts"]["script"] > i  # 簡易判定
            all_manual = True
            progress = progress_data.get(s["name"], {}).get("contents", {}).get(idx, {})
            steps = progress.get("steps", {})
            for step_key in ProgressManager.MANUAL_STEPS:
                if not steps.get(step_key, {}).get("done"):
                    all_manual = False
                    break
            if script_done and all_manual and progress.get("kpi_records"):
                total_all_done += 1

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("管理中アカウント数", total_accounts)
    with col2:
        st.metric("コンテンツ総数", total_contents)
    with col3:
        st.metric("投稿完了数", total_posted)
    with col4:
        st.metric("全工程完了数", total_all_done)

    st.markdown("---")

    # 担当者別サマリーテーブル
    st.markdown("### 担当者別サマリー")
    owner_stats = {}
    for s in summaries:
        owner = s["owner"] or "未設定"
        if owner not in owner_stats:
            owner_stats[owner] = {
                "accounts": 0,
                "contents": 0,
                "script": 0,
                "midjourney": 0,
                "kling_ai": 0,
                "eleven_labo": 0,
                "capcut": 0,
                "posted": 0,
                "kpi": 0,
            }
        stats = owner_stats[owner]
        stats["accounts"] += 1
        stats["contents"] += s["ideas_count"]
        stats["script"] += s["counts"]["script"]
        stats["midjourney"] += s["counts"]["midjourney"]
        stats["kling_ai"] += s["counts"]["kling_ai"]
        stats["eleven_labo"] += s["counts"]["eleven_labo"]
        stats["capcut"] += s["counts"]["capcut"]
        stats["posted"] += s["counts"]["posted"]
        stats["kpi"] += s["counts"]["kpi"]

    header_cols = [
        "担当者", "アカウント数", "コンテンツ数", "台本済",
        "画像済", "動画済", "ナレ済", "編集済", "投稿済", "分析済",
    ]
    header_html = "".join(
        f'<th style="text-align:{"left" if i == 0 else "center"};">{c}</th>'
        for i, c in enumerate(header_cols)
    )

    rows_html = ""
    for owner in sorted(owner_stats.keys()):
        stats = owner_stats[owner]
        rows_html += (
            f"<tr>"
            f'<td class="cell-name">{html_escape(owner)}</td>'
            f'<td class="cell-center">{stats["accounts"]}</td>'
            f'<td class="cell-center">{stats["contents"]}</td>'
            f'<td class="cell-center">{stats["script"]}</td>'
            f'<td class="cell-center">{stats["midjourney"]}</td>'
            f'<td class="cell-center">{stats["kling_ai"]}</td>'
            f'<td class="cell-center">{stats["eleven_labo"]}</td>'
            f'<td class="cell-center">{stats["capcut"]}</td>'
            f'<td class="cell-center">{stats["posted"]}</td>'
            f'<td class="cell-center">{stats["kpi"]}</td>'
            f"</tr>"
        )

    st.markdown(
        '<div class="app-table"><table>'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ステップ別完了率チャート
    st.markdown("### ステップ別完了率")

    step_labels_ordered = [
        ("strategy", "戦略設計"),
        ("ideas", "企画生成"),
        ("script", "台本生成"),
        ("midjourney", "MJ画像"),
        ("kling_ai", "Kling動画"),
        ("eleven_labo", "ナレーション"),
        ("vrew", "キャプション"),
        ("capcut", "動画編集"),
        ("posted", "投稿"),
        ("kpi", "数値分析"),
        ("improvement", "改善"),
    ]

    step_rates = []
    for key, label in step_labels_ordered:
        if key == "strategy":
            done = sum(1 for s in summaries if s["strategy_done"])
            total = total_accounts
        elif key == "ideas":
            done = sum(1 for s in summaries if s["ideas_done"])
            total = total_accounts
        elif key in ("kpi",):
            done = sum(s["counts"].get(key, 0) for s in summaries)
            total = total_contents
        else:
            done = sum(s["counts"].get(key, 0) for s in summaries)
            total = total_contents

        rate = (done / total * 100) if total > 0 else 0
        step_rates.append({"step": label, "rate": round(rate, 1), "done": done, "total": total})

    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=[s["step"] for s in reversed(step_rates)],
            x=[s["rate"] for s in reversed(step_rates)],
            orientation="h",
            text=[f'{s["rate"]}% ({s["done"]}/{s["total"]})' for s in reversed(step_rates)],
            textposition="auto",
            marker_color=[
                "rgba(234,135,104,0.8)" if s["rate"] < 30
                else "rgba(245,158,11,0.8)" if s["rate"] < 70
                else "rgba(16,185,129,0.8)"
                for s in reversed(step_rates)
            ],
        ))
        fig.update_layout(
            xaxis_title="完了率 (%)",
            xaxis_range=[0, 100],
            height=400,
            margin=dict(l=0, r=20, t=10, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        # Plotlyがない場合はシンプルなテキスト表示
        for s in step_rates:
            st.progress(s["rate"] / 100, text=f'{s["step"]}: {s["rate"]}% ({s["done"]}/{s["total"]})')


# ─── Tab 2: 詳細 ────────────────────────────────
def _render_detail(project_states, progress_data, ended_set):
    """詳細タブを描画"""

    # サイドバーに担当者フィルター
    with st.sidebar:
        st.markdown("### フィルター")
        filter_owner = st.selectbox(
            "担当者",
            ["全員"] + _MEMBERS,
            key="progress_filter_owner",
        )

    # アクティブプロジェクトのみ
    active_projects = {
        pname: state
        for pname, state in project_states.items()
        if pname not in ended_set
    }

    if filter_owner != "全員":
        active_projects = {
            pname: state
            for pname, state in active_projects.items()
            if _get_owner(state) == filter_owner
        }

    if not active_projects:
        st.info("該当するプロジェクトがありません。")
        return

    st.markdown(f"**{len(active_projects)}件のアカウント**")

    # アカウント別アコーディオン
    for pname in sorted(active_projects.keys()):
        state = active_projects[pname]
        owner = _get_owner(state)
        auto = ProgressManager.detect_auto_steps(state)

        # ヘッダーに進捗サマリーを表示
        ideas_count = auto["ideas_count"]
        progress = progress_data.get(pname, {}).get("contents", {})
        posted_count = sum(
            1 for i in range(ideas_count)
            if progress.get(str(i), {}).get("steps", {}).get("posted", {}).get("done")
        )
        header = f"{pname}  [{owner}]  -  {ideas_count}企画 / {posted_count}投稿済"

        with st.expander(header):
            if ideas_count == 0:
                st.caption("企画がまだ生成されていません。")
                continue

            _render_content_table(pname, auto, progress_data)


def _render_content_table(pname: str, auto: dict, progress_data: dict):
    """
    コンテンツ一覧テーブルを描画（チェックボックス + KPI入力）
    """
    ideas = auto["ideas"]
    scripts = auto["scripts"]
    progress = progress_data.get(pname, {}).get("contents", {})

    for i, idea in enumerate(ideas):
        idx = str(i)
        title = idea.get("title", f"企画{i+1}")
        # 30文字に切り詰め
        display_title = title[:30] + "..." if len(title) > 30 else title

        script_done = scripts.get(idx, False)
        content_progress = progress.get(idx, {})
        steps = content_progress.get("steps", {})
        kpi_records = content_progress.get("kpi_records", [])

        # 各コンテンツ行
        cols = st.columns([0.4, 2.5, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8])

        with cols[0]:
            st.caption(f"#{i+1}")

        with cols[1]:
            st.caption(display_title)

        with cols[2]:
            # 台本（自動検出）
            if script_done:
                st.markdown(
                    '<span style="color:#10b981;font-weight:bold;">&#10003;</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span style="color:#d1d5db;">&#9675;</span>',
                    unsafe_allow_html=True,
                )

        # 手動ステップのチェックボックス
        manual_step_cols = [
            ("midjourney", 3),
            ("kling_ai", 4),
            ("eleven_labo", 5),
            ("vrew", 6),
            ("capcut", 7),
            ("posted", 8),
        ]
        for step_key, col_idx in manual_step_cols:
            with cols[col_idx]:
                current = steps.get(step_key, {}).get("done", False)
                new_val = st.checkbox(
                    ProgressManager.STEP_LABELS.get(step_key, step_key),
                    value=current,
                    key=f"chk_{pname}_{idx}_{step_key}",
                    label_visibility="collapsed",
                )
                if new_val != current:
                    # 担当者をsession_stateから取得
                    updater = st.session_state.get("progress_updater", "")
                    pm = ProgressManager(pname)
                    pm.update_step(idx, step_key, new_val, updater)
                    _invalidate_cache()
                    st.rerun()

        # KPI列
        with cols[9]:
            kpi_label = f"{len(kpi_records)}件" if kpi_records else "-"
            if st.button(
                f"KPI({kpi_label})",
                key=f"kpi_btn_{pname}_{idx}",
                use_container_width=True,
            ):
                st.session_state[f"kpi_open_{pname}_{idx}"] = True

        # 改善列
        with cols[10]:
            imp_done = steps.get("improvement", {}).get("done", False)
            imp_new = st.checkbox(
                "改善",
                value=imp_done,
                key=f"chk_{pname}_{idx}_improvement",
                label_visibility="collapsed",
            )
            if imp_new != imp_done:
                updater = st.session_state.get("progress_updater", "")
                pm = ProgressManager(pname)
                pm.update_step(idx, "improvement", imp_new, updater)
                _invalidate_cache()
                st.rerun()

        # KPI入力フォーム（展開時のみ）
        if st.session_state.get(f"kpi_open_{pname}_{idx}"):
            _render_kpi_form(pname, idx, kpi_records)

    # ヘッダー行は上位のタブで表示


def _render_kpi_form(pname: str, content_idx: str, kpi_records: list):
    """KPI入力フォームと履歴を描画"""
    with st.container(border=True):
        st.markdown(f"**KPI記録 - コンテンツ#{int(content_idx)+1}**")

        with st.form(f"kpi_form_{pname}_{content_idx}", clear_on_submit=True):
            kpi_cols = st.columns(5)
            with kpi_cols[0]:
                views = st.number_input("再生数", min_value=0, value=0, key=f"kpi_views_{pname}_{content_idx}")
            with kpi_cols[1]:
                likes = st.number_input("いいね", min_value=0, value=0, key=f"kpi_likes_{pname}_{content_idx}")
            with kpi_cols[2]:
                comments = st.number_input("コメント", min_value=0, value=0, key=f"kpi_comments_{pname}_{content_idx}")
            with kpi_cols[3]:
                saves = st.number_input("保存数", min_value=0, value=0, key=f"kpi_saves_{pname}_{content_idx}")
            with kpi_cols[4]:
                shares = st.number_input("シェア", min_value=0, value=0, key=f"kpi_shares_{pname}_{content_idx}")

            recorder = st.selectbox(
                "記録者",
                _MEMBERS,
                key=f"kpi_recorder_{pname}_{content_idx}",
            )

            col_sub, col_close = st.columns(2)
            with col_sub:
                submitted = st.form_submit_button("記録", use_container_width=True, type="primary")
            with col_close:
                closed = st.form_submit_button("閉じる", use_container_width=True)

        if submitted:
            kpi = {
                "views": views,
                "likes": likes,
                "comments": comments,
                "saves": saves,
                "shares": shares,
            }
            pm = ProgressManager(pname)
            pm.add_kpi_record(content_idx, kpi, recorder)
            _invalidate_cache()
            st.session_state[f"kpi_open_{pname}_{content_idx}"] = False
            st.rerun()

        if closed:
            st.session_state[f"kpi_open_{pname}_{content_idx}"] = False
            st.rerun()

        # 履歴表示
        if kpi_records:
            with st.expander(f"過去の記録（{len(kpi_records)}件）"):
                for rec in reversed(kpi_records):
                    try:
                        dt = datetime.fromisoformat(rec["recorded_at"])
                        date_str = dt.strftime("%m/%d %H:%M")
                    except Exception:
                        date_str = rec.get("recorded_at", "")
                    by = rec.get("recorded_by", "")
                    st.caption(
                        f"{date_str} ({by}) - "
                        f"再生:{rec.get('views', 0)} "
                        f"いいね:{rec.get('likes', 0)} "
                        f"コメント:{rec.get('comments', 0)} "
                        f"保存:{rec.get('saves', 0)} "
                        f"シェア:{rec.get('shares', 0)}"
                    )


# ─── メイン ──────────────────────────────────
def main():
    st.set_page_config(
        page_title="進捗管理 - SNS Automation",
        page_icon="▲",
        layout="wide",
    )

    # 共通CSS注入
    inject_styles()

    render_feedback_form()

    # サイドバーに更新者選択
    with st.sidebar:
        st.markdown("### 操作者")
        updater = st.selectbox(
            "あなたの名前",
            _MEMBERS,
            key="progress_updater",
        )

    render_page_header("進捗管理", "戦略設計から投稿・分析まで、全工程の進捗を一元管理。")

    # 更新ボタン
    col1, col2 = st.columns([8, 1])
    with col2:
        if st.button("更新", use_container_width=True):
            _invalidate_cache()
            st.rerun()

    st.markdown("---")

    # データ読み込み
    project_states, progress_data, ended_set = _load_all_data()

    if not project_states:
        st.info("プロジェクトがまだ作成されていません。「アカウント管理」ページからプロジェクトを作成してください。")
        return

    # タブ切り替え
    tab_dashboard, tab_detail = st.tabs(["ダッシュボード", "詳細"])

    with tab_dashboard:
        _render_dashboard(project_states, progress_data, ended_set)

    with tab_detail:
        # コンテンツテーブルのヘッダー説明
        st.caption(
            "台本: 自動検出 | MJ〜投稿・改善: チェックボックスで手動更新 | "
            "分析: KPIボタンで数値入力"
        )
        col_labels = st.columns([0.4, 2.5, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8])
        labels = ["#", "タイトル", "台本", "MJ", "Kling", "11LABO", "Vrew", "CapCut", "投稿", "分析", "改善"]
        for col, label in zip(col_labels, labels):
            with col:
                st.markdown(f"**{label}**")
        st.markdown("---")
        _render_detail(project_states, progress_data, ended_set)


if __name__ == "__main__":
    main()
