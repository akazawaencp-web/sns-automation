"""
コンテンツ量産ページ

企画生成と台本生成を表形式で統合
"""

import streamlit as st
from pathlib import Path
import json
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import io
import streamlit.components.v1 as components

from sns_automation.utils import (
    load_config,
    IdeaAnalyzer,
    ScriptPreviewer,
    error_helpers,
    StateManager,
)
from sns_automation.chapter3_content import ContentAutomation
from sns_automation.web.components import render_feedback_form


def _create_copy_button(text: str, button_text: str = "📋 コピー", key: str = None):
    """
    クリップボードにコピーするボタンを作成

    Args:
        text: コピーするテキスト
        button_text: ボタンに表示するテキスト
        key: ボタンの一意なキー
    """
    # テキストをJavaScript文字列として安全にエスケープ
    import html
    escaped_text = html.escape(text).replace("'", "\\'").replace("\n", "\\n").replace("\r", "")

    # ユニークなボタンID
    button_id = f"copy_btn_{hash(key or text) % 1000000}"

    html_code = f"""
    <div style="display: inline-block;">
        <button
            id="{button_id}"
            onclick="copyToClipboard_{button_id}()"
            style="
                background-color: #f0f2f6;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
            "
            onmouseover="this.style.backgroundColor='#e0e2e6'"
            onmouseout="this.style.backgroundColor='#f0f2f6'"
        >
            {button_text}
        </button>
    </div>
    <script>
    function copyToClipboard_{button_id}() {{
        const text = '{escaped_text}';
        const decodedText = text.replace(/&lt;/g, '<')
                                 .replace(/&gt;/g, '>')
                                 .replace(/&amp;/g, '&')
                                 .replace(/&quot;/g, '"')
                                 .replace(/&#x27;/g, "'")
                                 .replace(/\\\\n/g, '\\n');

        navigator.clipboard.writeText(decodedText).then(function() {{
            const btn = document.getElementById('{button_id}');
            const originalText = btn.innerHTML;
            btn.innerHTML = '✅ コピーしました！';
            btn.style.backgroundColor = '#d4edda';
            btn.style.borderColor = '#c3e6cb';
            setTimeout(function() {{
                btn.innerHTML = originalText;
                btn.style.backgroundColor = '#f0f2f6';
                btn.style.borderColor = '#d0d0d0';
            }}, 2000);
        }}, function(err) {{
            console.error('コピー失敗:', err);
            alert('コピーに失敗しました');
        }});
    }}
    </script>
    """

    components.html(html_code, height=40)


def main():
    st.set_page_config(
        page_title="コンテンツ量産 - SNS Automation",
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

        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border-radius: 1rem !important;
            border: 1px solid #d0d0d0 !important;
            background-color: white !important;
        }

        /* 新規追加行のハイライト */
        .dataframe tbody tr.new-row {
            background-color: #fff9e6 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # フィードバックフォーム
    render_feedback_form()

    st.markdown('<div class="page-header">コンテンツ量産</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">企画を生成して、複数選択で一括台本作成。効率的なワークフロー。</div>', unsafe_allow_html=True)

    st.markdown("---")

    # プロジェクト選択（StateManager経由でローカル + Google Sheetsの両方から取得）
    sm = StateManager()
    project_names = sm.list_all_projects()

    if not project_names:
        st.warning("プロジェクトが作成されていません。「アカウント管理」ページから新規作成してください。")
        return

    # プロジェクト選択
    selected_project = st.selectbox(
        "プロジェクトを選択",
        project_names,
        key="selected_project",
    )

    if not selected_project:
        st.info("プロジェクトを選択してください")
        return

    # 選択したプロジェクトの状態を読み込み（Google Sheets → ローカルの順）
    state_manager = StateManager(selected_project)
    project_state = state_manager.load_state()

    if not project_state:
        st.error(f"プロジェクト「{selected_project}」の読み込みに失敗しました")
        return

    # Chapter 1の完了チェック
    if project_state.get("last_chapter", 0) < 1:
        st.error(
            "先に戦略設計（Chapter 1）を完了してください。\\n\\n"
            "「戦略設計」ページでペルソナ・Painを定義してから、このページに戻ってきてください。"
        )
        return

    st.success(f"プロジェクト「{selected_project}」を選択中")

    st.markdown("---")

    # 企画生成セクション
    _render_content_section(selected_project, project_state)


def _render_content_section(project_name: str, project_state: dict):
    """
    コンテンツ生成セクションを描画

    Args:
        project_name: プロジェクト名
        project_state: プロジェクト状態
    """
    # 既存の企画を表示
    existing_ideas = project_state.get("data", {}).get("ideas", [])

    # 企画生成ボタン
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("企画を生成（20案）", type="primary", use_container_width=True):
            st.session_state.start_idea_generation = True
            st.session_state.regenerate_ideas = False
            st.session_state.add_more_ideas = False
            st.rerun()

    with col2:
        if existing_ideas and st.button("➕ 追加で20案生成", use_container_width=True):
            st.session_state.start_idea_generation = False
            st.session_state.regenerate_ideas = False
            st.session_state.add_more_ideas = True
            st.rerun()

    with col3:
        if existing_ideas:
            # CSVダウンロード
            csv = _export_to_csv(project_state)
            st.download_button(
                label="📥 CSV出力",
                data=csv,
                file_name=f"{project_name}_企画一覧.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # 企画生成処理
    if st.session_state.get("start_idea_generation") or st.session_state.get("regenerate_ideas") or st.session_state.get("add_more_ideas"):
        _generate_ideas(project_name, project_state)
        return

    if not existing_ideas:
        st.info("企画がまだ生成されていません。「企画を生成（20案）」ボタンから20案を自動生成してください。")
        return

    st.markdown("---")

    # 企画統計情報
    st.subheader(f"企画一覧（{len(existing_ideas)}件）")

    # IdeaAnalyzerで分析
    analyzer = IdeaAnalyzer()
    analysis = analyzer.analyze_ideas(existing_ideas)

    # 訴求タイプ分布グラフ（コンパクト版）
    with st.expander("📊 訴求タイプ分布を見る"):
        appeal_types = list(analysis["appeal_distribution"].keys())
        counts = list(analysis["appeal_distribution"].values())

        fig = go.Figure(data=[
            go.Bar(
                x=appeal_types,
                y=counts,
                marker_color=['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a'],
            )
        ])

        fig.update_layout(
            title="企画の訴求タイプ分布",
            xaxis_title="訴求タイプ",
            yaxis_title="件数",
            height=350,
        )

        st.plotly_chart(fig, use_container_width=True)

        # バランス判定
        if analysis["is_balanced"]:
            st.success("バランスの良い企画構成です")
        else:
            st.warning("企画の傾向に偏りがあります")
            for warning in analysis["warnings"]:
                st.markdown(f"- {warning}")

    st.markdown("---")

    # 新規追加企画の開始位置を取得
    newly_added_start = st.session_state.get("newly_added_start_index", None)

    # 企画一覧を表形式で表示
    _render_ideas_table(project_name, project_state, existing_ideas, newly_added_start)


def _render_ideas_table(project_name: str, project_state: dict, ideas: list, newly_added_start: int):
    """
    企画一覧をカード形式で表示

    Args:
        project_name: プロジェクト名
        project_state: プロジェクト状態
        ideas: 企画リスト
        newly_added_start: 新規追加の開始位置
    """
    # セッション状態で選択状態を管理
    if f"selected_ideas_{project_name}" not in st.session_state:
        st.session_state[f"selected_ideas_{project_name}"] = set()

    selected_ideas_key = f"selected_ideas_{project_name}"

    # 全選択/全解除ボタン
    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        if st.button("☑️ 全選択", use_container_width=True, key=f"select_all_{project_name}"):
            st.session_state[selected_ideas_key] = set(range(len(ideas)))
            st.rerun()

    with col2:
        if st.button("☐ 全解除", use_container_width=True, key=f"deselect_all_{project_name}"):
            st.session_state[selected_ideas_key] = set()
            st.rerun()

    with col3:
        selected_count = len(st.session_state[selected_ideas_key])
        if selected_count > 0:
            st.info(f"📌 {selected_count}件の企画を選択中")

    st.markdown("---")

    # 各企画をカードで表示
    for i, idea in enumerate(ideas):
        # 台本情報を取得
        script_key = f"script_{i}"
        script = project_state.get("data", {}).get(script_key)

        if script:
            # 台本が生成済み
            previewer = ScriptPreviewer()
            preview = previewer.preview_script(script)

            status_icon = "✅"
            status_text = "生成済み"
            status_color = "#4CAF50"
            narration_length = preview['narration_length']
            estimated_duration = f"{preview['estimated_duration']:.1f}秒"
            slide_count = preview['slide_count']
        else:
            # 台本未生成
            status_icon = "⚪"
            status_text = "未生成"
            status_color = "#9E9E9E"
            narration_length = "-"
            estimated_duration = "-"
            slide_count = "-"

        # 新規追加マーク
        is_new = newly_added_start is not None and i >= newly_added_start
        new_badge = "🆕 " if is_new else ""

        # カードのヘッダー
        title_full = idea.get("title", "（タイトルなし）")
        summary_full = idea.get("summary", "（要約なし）")

        # カード表示
        with st.container():
            # カードヘッダー（チェックボックス + タイトル + ステータス）
            col_check, col_title, col_status = st.columns([0.5, 6, 2])

            with col_check:
                is_selected = i in st.session_state[selected_ideas_key]
                if st.checkbox(
                    "",
                    value=is_selected,
                    key=f"checkbox_{project_name}_{i}",
                    label_visibility="collapsed",
                ):
                    if i not in st.session_state[selected_ideas_key]:
                        st.session_state[selected_ideas_key].add(i)
                        st.rerun()
                else:
                    if i in st.session_state[selected_ideas_key]:
                        st.session_state[selected_ideas_key].discard(i)
                        st.rerun()

            with col_title:
                # 完全なタイトルを表示
                st.markdown(f"**{new_badge}No.{idea.get('no', i+1)}**")
                st.markdown(f"**📌 企画タイトル:** {title_full}")
                st.markdown(f"**🎯 狙い・内容:** {summary_full}")

            with col_status:
                st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{status_icon} {status_text}</span>", unsafe_allow_html=True)

            # 台本情報（生成済みの場合のみ）
            if script:
                with st.expander("📊 台本情報を見る"):
                    col_info1, col_info2, col_info3 = st.columns(3)

                    with col_info1:
                        st.metric("ナレーション文字数", f"{narration_length}文字")

                    with col_info2:
                        st.metric("推定読み上げ時間", estimated_duration)

                    with col_info3:
                        st.metric("スライド枚数", f"{slide_count}枚")

            # カード間のスペース
            st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 選択された企画を取得
    selected_indices = sorted(list(st.session_state[selected_ideas_key]))

    # 台本一括生成ボタン
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button(
            f"📄 選択した企画の台本を生成（{len(selected_indices)}件）",
            type="primary",
            disabled=len(selected_indices) == 0,
            use_container_width=True,
        ):
            st.session_state.generating_scripts = True
            st.session_state.selected_idea_indices = selected_indices
            st.rerun()

    with col2:
        if st.button(
            f"📄 選択した企画の台本を生成（{len(selected_indices)}件）",
            type="primary",
            disabled=len(selected_indices) == 0,
            use_container_width=True,
            key=f"generate_scripts_{project_name}",
        ):
            st.session_state.generating_scripts = True
            st.session_state.selected_idea_indices = selected_indices
            st.rerun()

    with col3:
        # 新規追加マーククリア
        if newly_added_start is not None:
            if st.button(
                "✅ 新規マーククリア",
                use_container_width=True,
                key=f"clear_new_mark_{project_name}",
            ):
                del st.session_state["newly_added_start_index"]
                st.rerun()

    # 台本一括生成処理
    if st.session_state.get("generating_scripts"):
        _generate_multiple_scripts(project_name, project_state, ideas, st.session_state.selected_idea_indices)
        return  # 生成中は以降の表示をスキップ

    # 生成済み台本の詳細を表示
    st.markdown("---")
    st.subheader("📚 生成済み台本の詳細")

    # 生成済み台本を収集
    generated_scripts = []
    for i, idea in enumerate(ideas):
        script_key = f"script_{i}"
        script = project_state.get("data", {}).get(script_key)
        if script:
            generated_scripts.append({
                "index": i,
                "idea": idea,
                "script": script,
            })

    if not generated_scripts:
        st.info("まだ台本が生成されていません。企画を選択して「台本を生成」ボタンをクリックしてください。")
    else:
        st.markdown(f"**{len(generated_scripts)}件の台本が生成されています**")

        # 各台本をexpanderで表示
        for item in generated_scripts:
            idx = item["index"]
            idea = item["idea"]
            script = item["script"]

            # ステータスバッジ
            quality = script.get("quality_score", {})
            error_count = quality.get("error_count", 0)
            attempts = quality.get("attempts", 1)

            if error_count == 0:
                status_badge = "✅ 品質OK"
            else:
                status_badge = f"⚠️ エラー{error_count}件"

            with st.expander(f"**No.{idea.get('no')}** {idea.get('title', '（タイトルなし）')} — {status_badge} （試行{attempts}回）"):
                st.markdown(f"**狙い・内容:** {idea.get('summary', '（要約なし）')}")
                _display_script_details(script)


def _display_script_details(script: dict):
    """
    台本の詳細を表示

    Args:
        script: 台本辞書
    """
    st.markdown("---")
    st.markdown("**📄 台本情報**")

    # プレビュー情報
    previewer = ScriptPreviewer()
    preview = previewer.preview_script(script)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("ナレーション文字数", f"{preview['narration_length']}文字")

    with col2:
        st.metric("推定読み上げ時間", f"{preview['estimated_duration']:.1f}秒")

    with col3:
        st.metric("スライド枚数", f"{preview['slide_count']}枚")

    # 警告表示
    if preview["has_issues"]:
        st.warning("品質チェックで問題が検出されました")

        if preview["time_warning"]:
            st.markdown(f"- {preview['time_warning']}")

        for warning in preview["slide_warnings"]:
            st.markdown(f"- {warning}")
    else:
        st.success("全ての品質基準を満たしています")

    # 台本の各セクションを抽出
    full_script = script.get("full_script", "")
    sections = _parse_script_sections(full_script)

    # Midjourneyプロンプト
    st.markdown("---")
    st.markdown("**🎨 Midjourneyプロンプト**")
    if sections.get("midjourney"):
        # 日本語説明と英語プロンプトを分離
        mj_sections = _extract_midjourney_sections(sections["midjourney"])

        # デバッグ情報（一時的）
        with st.expander("🔍 デバッグ情報"):
            st.write("日本語セクション:", mj_sections["ja"][:100] if mj_sections["ja"] else "なし")
            st.write("英語セクション:", mj_sections["en"][:100] if mj_sections["en"] else "なし")

        # 日本語プロンプト（見出しなし）
        if mj_sections["ja"]:
            # コピーボタンを配置
            _create_copy_button(mj_sections["ja"], "📋 日本語をコピー", key="mj_ja")

            st.markdown(
                f"""
                <div style="
                    background-color: #f0f2f6;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    border: 1px solid #d0d0d0;
                    font-family: monospace;
                    font-size: 14px;
                    line-height: 1.6;
                    word-wrap: break-word;
                    white-space: pre-wrap;
                    margin-bottom: 1rem;
                ">{mj_sections["ja"]}</div>
                """,
                unsafe_allow_html=True,
            )

        # 英語プロンプト（見出しなし）
        if mj_sections["en"]:
            # コピーボタンを配置
            _create_copy_button(mj_sections["en"], "📋 英語をコピー", key="mj_en")

            st.markdown(
                f"""
                <div style="
                    background-color: #f0f2f6;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    border: 1px solid #d0d0d0;
                    font-family: monospace;
                    font-size: 14px;
                    line-height: 1.6;
                    word-wrap: break-word;
                    white-space: pre-wrap;
                ">{mj_sections["en"]}</div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Midjourneyプロンプトが見つかりません")

    # ナレーション全文
    st.markdown("---")
    st.markdown("**🎙️ ナレーション全文**")
    narration = script.get("narration", sections.get("narration", ""))
    if narration:
        # コピーボタンを配置
        _create_copy_button(narration, "📋 ナレーションをコピー", key="narration")

        st.text_area(
            "ナレーションテキスト",
            narration,
            height=200,
            disabled=True,
            label_visibility="collapsed",
        )
    else:
        st.info("ナレーションが見つかりません")

    # スライド別詳細（台本表）
    st.markdown("---")
    st.markdown("**📊 スライド別詳細**")
    if sections.get("slides"):
        # HTMLテーブルで表示（折り返し対応）
        _display_slides_table(sections["slides"])
    else:
        st.info("スライド情報が見つかりません")

    # 台本全文（折りたたみ）
    with st.expander("📝 台本全文（Markdown）を見る"):
        st.code(full_script, language="markdown")


def _generate_multiple_scripts(project_name: str, project_state: dict, ideas: list, selected_indices: list):
    """
    複数の企画から台本を一括生成

    Args:
        project_name: プロジェクト名
        project_state: プロジェクト状態
        ideas: 企画リスト
        selected_indices: 選択された企画のインデックスリスト
    """
    st.subheader(f"台本を一括生成中...（{len(selected_indices)}件）")

    # デバッグ情報を表示
    debug_expander = st.expander("🔍 デバッグ情報を見る")

    generated_count = 0
    skipped_count = 0
    error_count = 0

    try:
        # Chapter 1のデータを取得
        chapter1_data = project_state.get("data", {})

        # ContentAutomationを初期化（Streamlit環境ではst.secretsから自動取得）
        automation = ContentAutomation(project_name=project_name)

        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()

        with debug_expander:
            st.write(f"選択された企画インデックス: {selected_indices}")

        # 各企画の台本を生成
        for i, idx in enumerate(selected_indices):
            idea = ideas[idx]
            script_key = f"script_{idx}"

            status_text.text(f"台本を生成中 ({i+1}/{len(selected_indices)}): {idea.get('title', '（タイトルなし）')}")
            progress = int((i / len(selected_indices)) * 100)
            progress_bar.progress(progress)

            with debug_expander:
                st.write(f"--- 企画 #{idx+1} ---")
                st.write(f"script_key: {script_key}")

            # 既に台本が生成されている場合はスキップ
            if script_key in project_state.get("data", {}):
                with debug_expander:
                    st.write("→ スキップ（既に生成済み）")
                skipped_count += 1
                continue

            try:
                # 台本を生成
                with debug_expander:
                    st.write("→ 台本を生成中...")

                script = automation.generate_script(idea, chapter1_data)

                with debug_expander:
                    st.write("→ 生成成功")
                    st.write(f"  - 台本文字数: {len(script.get('full_script', ''))}")
                    st.write(f"  - ナレーション文字数: {len(script.get('narration', ''))}")

                    # 台本全文をデバッグ表示（Midjourneyセクションの確認用）
                    full_script_text = script.get('full_script', '')
                    if 'midjourney' in full_script_text.lower():
                        st.write("**📝 台本全文（Midjourneyセクションのみ）:**")
                        # Midjourneyセクションだけを抽出して表示
                        import re
                        mj_section_match = re.search(
                            r'(##?\s*.*?midjourney.*?)(##?\s*(?:台本表|ナレーション))',
                            full_script_text,
                            re.DOTALL | re.IGNORECASE
                        )
                        if mj_section_match:
                            st.code(mj_section_match.group(1), language="markdown")

                # プロジェクト状態を更新
                if "data" not in project_state:
                    project_state["data"] = {}

                project_state["data"][script_key] = script
                generated_count += 1

                with debug_expander:
                    st.write("→ プロジェクト状態に保存完了")

            except Exception as e:
                error_count += 1
                with debug_expander:
                    st.error(f"→ エラー: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        # StateManagerで状態を保存（ローカル + Google Sheets）
        with debug_expander:
            st.write(f"--- StateManagerで保存中 ---")
            st.write(f"プロジェクト名: {project_name}")

        state_manager = StateManager(project_name)
        state_manager.save_state(
            chapter=3,
            step="script_generation",
            data=project_state.get("data", {}),
            metadata=project_state.get("metadata", {}),
        )

        with debug_expander:
            st.write("→ ローカルファイル + Google Sheetsに保存完了")

        progress_bar.progress(100)
        status_text.text("完了！")

        # 結果サマリー
        st.success(f"✅ 台本生成完了: {generated_count}件生成、{skipped_count}件スキップ、{error_count}件エラー")

        if generated_count > 0:
            st.balloons()

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        import traceback
        st.code(traceback.format_exc())

    finally:
        # フラグをクリア
        st.session_state.generating_scripts = False
        if "selected_idea_indices" in st.session_state:
            del st.session_state.selected_idea_indices


def _generate_ideas(project_name: str, project_state: dict):
    """
    企画を生成

    Args:
        project_name: プロジェクト名
        project_state: プロジェクト状態
    """
    st.subheader("企画生成中...")

    try:
        # Chapter 1のデータを取得
        chapter1_data = project_state.get("data", {})

        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("企画を生成中...（Claude APIを呼び出しています）")
        progress_bar.progress(10)

        # ContentAutomationを初期化（Streamlit環境ではst.secretsから自動取得）
        automation = ContentAutomation(project_name=project_name)

        progress_bar.progress(20)

        # 企画を生成（20案）
        # 追加生成時は既存企画を渡してネタ被りを回避
        existing_ideas = None
        if st.session_state.get("add_more_ideas"):
            existing_ideas = project_state.get("data", {}).get("ideas", [])

        ideas = _generate_ideas_non_interactive(automation, chapter1_data, progress_bar, status_text, existing_ideas=existing_ideas)

        if ideas:
            # プロジェクト状態を更新
            if "ideas" not in project_state["data"]:
                project_state["data"]["ideas"] = []

            # 追加生成の場合
            if st.session_state.get("add_more_ideas"):
                # 新規追加の開始位置を記録
                st.session_state["newly_added_start_index"] = len(project_state["data"]["ideas"])

                # 番号を振り直し
                start_no = len(project_state["data"]["ideas"]) + 1
                for i, idea in enumerate(ideas):
                    idea["no"] = str(start_no + i)
                project_state["data"]["ideas"].extend(ideas)
            else:
                # 新規生成または作り直しの場合は置き換え
                project_state["data"]["ideas"] = ideas
                # 新規追加フラグをクリア
                if "newly_added_start_index" in st.session_state:
                    del st.session_state["newly_added_start_index"]

            # StateManagerで状態を保存（ローカル + Google Sheets）
            state_manager = StateManager(project_name)
            state_manager.save_state(
                chapter=3,
                step="idea_generation",
                data=project_state.get("data", {}),
                metadata=project_state.get("metadata", {}),
            )

            progress_bar.progress(100)
            status_text.text("完了！")

            st.success(f"{len(ideas)}本の企画を生成しました")
            st.balloons()

        else:
            st.error("企画の生成に失敗しました")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        import traceback
        st.code(traceback.format_exc())

    finally:
        # フラグをクリア
        st.session_state.start_idea_generation = False
        st.session_state.regenerate_ideas = False
        st.session_state.add_more_ideas = False


def _generate_ideas_non_interactive(automation: ContentAutomation, strategy_data: dict, progress_bar, status_text, existing_ideas: list = None) -> list:
    """
    企画を非対話的に生成（WebUI用）

    Args:
        automation: ContentAutomationインスタンス
        strategy_data: Chapter 1の戦略データ
        progress_bar: Streamlitプログレスバー
        status_text: Streamlitステータステキスト
        existing_ideas: 既存の企画リスト（追加生成時にネタ被りを避けるため）

    Returns:
        企画リスト
    """
    from sns_automation.utils import load_prompt

    # Chapter 1のデータを整形
    persona = strategy_data.get("persona", {})
    if isinstance(persona, dict):
        persona_text = persona.get("raw_text", "未設定")
    else:
        persona_text = str(persona)

    pains_list = strategy_data.get("pains", [])
    pains = "\n".join(f"{i}. {p}" for i, p in enumerate(pains_list, 1))

    status_text.text("プロンプトを準備中...")
    progress_bar.progress(30)

    # 追加生成時は既存企画を含むプロンプトを使用
    if existing_ideas:
        existing_titles = "\n".join(
            f"- {idea.get('title', '（タイトルなし）')}"
            for idea in existing_ideas
        )
        prompt_data = load_prompt(
            chapter="chapter3",
            prompt_name="idea_generation_additional",
            variables={
                "persona": persona_text,
                "pains": pains,
                "existing_ideas": existing_titles,
            },
        )
    else:
        prompt_data = load_prompt(
            chapter="chapter3",
            prompt_name="idea_generation",
            variables={
                "persona": persona_text,
                "pains": pains,
            },
        )

    status_text.text("Claude APIで企画を生成中...（数十秒かかります）")
    progress_bar.progress(40)

    # Claude APIを呼び出し
    response = automation.claude.generate_text(
        prompt=prompt_data["user"],
        system_prompt=prompt_data.get("system"),
        temperature=prompt_data.get("temperature", 0.9),
        max_tokens=prompt_data.get("max_tokens", 8000),
    )

    status_text.text("レスポンスを解析中...")
    progress_bar.progress(70)

    # レスポンスをパース
    ideas = automation._parse_ideas(response)

    # 番号を振り直し（1-20）
    for i, idea in enumerate(ideas):
        idea["no"] = str(i + 1)

    status_text.text("企画を保存中...")
    progress_bar.progress(90)

    return ideas


def _extract_midjourney_sections(midjourney_text: str) -> dict:
    """
    Midjourneyプロンプトから日本語説明と英語プロンプトを抽出

    Args:
        midjourney_text: Midjourneyプロンプト全文

    Returns:
        {"ja": "日本語説明", "en": "英語プロンプト"}
    """
    import re

    ja_text = ""
    en_text = ""

    # 日本語訳セクションを抽出
    # パターン: ### 日本語訳 → 改行（複数可） → ```（言語指定可） → 改行 → テキスト → 改行 → ```
    ja_match = re.search(r'###\s*日本語.*?\n+```[^\n]*\n+(.*?)\n+```', midjourney_text, re.DOTALL)
    if ja_match:
        ja_text = ja_match.group(1).strip()

    # 英語セクションを抽出
    # パターン: ### Midjourneyプロンプト（英語）、### 英語、### English など柔軟にマッチ
    en_match = re.search(
        r'###\s*(?:Midjourney.*?(?:英語|English)|英語|English).*?\n+```[^\n]*\n+(.*?)\n+```',
        midjourney_text,
        re.DOTALL | re.IGNORECASE
    )
    if en_match:
        en_text = en_match.group(1).strip()

    # どちらも見つからない場合は、全体を日本語として返す
    if not ja_text and not en_text:
        ja_text = midjourney_text

    return {
        "ja": ja_text,
        "en": en_text,
    }


def _parse_script_sections(full_script: str) -> dict:
    """
    台本全文から各セクションを抽出する

    Args:
        full_script: 台本全文（Markdown形式）

    Returns:
        セクション辞書
    """
    sections = {
        "midjourney": "",
        "narration": "",
        "slides": [],
    }

    lines = full_script.split("\n")
    current_section = None
    in_code_block = False
    code_lines = []
    table_lines = []
    midjourney_lines = []  # Midjourneyセクション全体を保存

    for line in lines:
        stripped = line.strip()

        # セクション判定（レベル2の見出し ## のみ）
        # レベル3の見出し ### はサブセクションとして無視
        if stripped.startswith("## "):
            # Midjourneyセクション：「midjourney」「画像生成」「モデル人物」のいずれかを含む
            if any(keyword in stripped.lower() for keyword in ["midjourney", "画像生成", "モデル人物"]):
                current_section = "midjourney"
                continue
            elif "台本表" in stripped:
                # Midjourneyセクションが終了
                if midjourney_lines:
                    sections["midjourney"] = "\n".join(midjourney_lines).strip()
                    midjourney_lines = []
                current_section = "table"
                continue
            elif "ナレーション" in stripped:
                # Midjourneyセクションが終了
                if midjourney_lines:
                    sections["midjourney"] = "\n".join(midjourney_lines).strip()
                    midjourney_lines = []
                current_section = "narration"
                continue

        # Midjourneyセクションの全行を保存
        if current_section == "midjourney":
            midjourney_lines.append(line)

        # コードブロックの処理
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if not in_code_block and code_lines:
                # コードブロック終了
                if current_section == "narration":
                    sections["narration"] = "\n".join(code_lines).strip()
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # テーブルの処理（| で始まる行）
        if current_section == "table" and stripped.startswith("|"):
            # ヘッダー行とセパレーター行はスキップ
            if "スライドNo" in stripped or "時間" in stripped or stripped.startswith("|---"):
                continue

            # サンプル行もスキップ
            if "例：" in stripped or "..." in stripped:
                continue

            table_lines.append(stripped)

    # テーブル行をパース（新フォーマット対応）
    # | スライドNo | 秒数(目安) | ナレーション/テロップ（CapCut用） | 動画生成指示（日本語） | 動画生成指示（英語・Kling AI用） |
    for line in table_lines:
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]  # 空の要素を削除

        if len(parts) >= 5:
            # 新フォーマット（5列）
            sections["slides"].append({
                "スライドNo": parts[0],
                "秒数(目安)": parts[1],
                "ナレーション/テロップ（CapCut用）": parts[2],
                "動画生成指示（日本語）": parts[3],
                "動画生成指示（英語・Kling AI用）": parts[4],
            })
        elif len(parts) >= 4:
            # 旧フォーマット（4列）
            sections["slides"].append({
                "スライドNo": parts[0],
                "秒数(目安)": parts[1],
                "ナレーション/テロップ（CapCut用）": parts[2],
                "動画生成指示（日本語）": parts[3],
                "動画生成指示（英語・Kling AI用）": "",
            })
        elif len(parts) >= 3:
            # 旧フォーマット（3列: 時間、ナレーション、画像指示）
            sections["slides"].append({
                "スライドNo": f"{len(sections['slides'])+1}",
                "秒数(目安)": parts[0],
                "ナレーション/テロップ（CapCut用）": parts[1],
                "動画生成指示（日本語）": parts[2],
                "動画生成指示（英語・Kling AI用）": "",
            })

    return sections


def _display_slides_table(slides: list):
    """
    スライド別詳細をHTMLテーブルで表示（折り返し対応）

    Args:
        slides: スライド情報のリスト
    """
    if not slides:
        st.info("スライド情報がありません")
        return

    # カラム名を取得（最初のスライドから）
    columns = list(slides[0].keys())

    # HTMLテーブルを生成
    html = """
    <style>
    .slides-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        margin-top: 1rem;
    }
    .slides-table th {
        background-color: #f0f2f6;
        color: #31333F;
        font-weight: 600;
        padding: 12px;
        text-align: left;
        border: 1px solid #d0d0d0;
        white-space: nowrap;
    }
    .slides-table td {
        padding: 12px;
        border: 1px solid #d0d0d0;
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
        background-color: #f0f2f6;
    }
    .col-slide-no {
        width: 80px;
        text-align: center;
    }
    .col-duration {
        width: 80px;
        text-align: center;
    }
    .col-narration {
        width: calc((100% - 160px) / 2);
    }
    .col-video-instruction-ja {
        width: calc((100% - 160px) * 0.35);
    }
    .col-video-instruction-en {
        width: calc((100% - 160px) * 0.15);
    }
    .copy-btn-cell {
        position: absolute;
        top: 4px;
        right: 4px;
        background-color: #f0f2f6;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s;
        opacity: 0.7;
    }
    .copy-btn-cell:hover {
        opacity: 1;
        background-color: #e0e2e6;
    }
    .cell-content-wrapper {
        padding-right: 60px; /* コピーボタンのスペースを確保 */
    }
    </style>
    <table class="slides-table">
    <thead>
    <tr>
    """

    # ヘッダー行を生成
    for col in columns:
        col_class = ""
        if "スライドNo" in col:
            col_class = "col-slide-no"
        elif "秒数" in col:
            col_class = "col-duration"
        elif "ナレーション" in col:
            col_class = "col-narration"
        elif "動画生成指示（日本語）" in col:
            col_class = "col-video-instruction-ja"
        elif "動画生成指示（英語" in col:
            col_class = "col-video-instruction-en"

        # カラム名を短縮
        display_name = col.replace("（CapCut用）", "<br>（CapCut）").replace("（英語・Kling AI用）", "<br>（英語・Kling AI）").replace("（日本語）", "<br>（日本語）")
        html += f'<th class="{col_class}">{display_name}</th>'

    html += """
    </tr>
    </thead>
    <tbody>
    """

    # データ行を生成
    import html as html_module
    for slide_idx, slide in enumerate(slides):
        html += "<tr>"
        for col_idx, col in enumerate(columns):
            value = slide.get(col, "")
            col_class = ""
            needs_copy_btn = False

            if "スライドNo" in col:
                col_class = "col-slide-no"
            elif "秒数" in col:
                col_class = "col-duration"
            elif "ナレーション" in col:
                col_class = "col-narration"
                needs_copy_btn = True
            elif "動画生成指示（日本語）" in col:
                col_class = "col-video-instruction-ja"
                needs_copy_btn = True
            elif "動画生成指示（英語" in col:
                col_class = "col-video-instruction-en"
                needs_copy_btn = True

            # コピーボタンが必要なセル
            if needs_copy_btn and value:
                # HTMLとJavaScriptで安全にエスケープ
                escaped_value_js = html_module.escape(value).replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
                escaped_value_html = html_module.escape(value)  # HTML表示用
                btn_id = f"copy_cell_{slide_idx}_{col_idx}"
                html += f'''
                <td class="{col_class}">
                    <button class="copy-btn-cell" id="{btn_id}" onclick="copyCellContent_{btn_id}()">📋</button>
                    <div class="cell-content-wrapper">{escaped_value_html}</div>
                    <script>
                    function copyCellContent_{btn_id}() {{
                        const text = '{escaped_value_js}';
                        const decodedText = text.replace(/&lt;/g, '<')
                                                 .replace(/&gt;/g, '>')
                                                 .replace(/&amp;/g, '&')
                                                 .replace(/&quot;/g, '"')
                                                 .replace(/&#x27;/g, "'")
                                                 .replace(/\\\\n/g, '\\n');
                        navigator.clipboard.writeText(decodedText).then(function() {{
                            const btn = document.getElementById('{btn_id}');
                            btn.innerHTML = '✅';
                            btn.style.backgroundColor = '#d4edda';
                            setTimeout(function() {{
                                btn.innerHTML = '📋';
                                btn.style.backgroundColor = '#f0f2f6';
                            }}, 1500);
                        }});
                    }}
                    </script>
                </td>
                '''
            else:
                html += f'<td class="{col_class}">{html_module.escape(value)}</td>'
        html += "</tr>"

    html += """
    </tbody>
    </table>
    """

    # st.markdown() は <script> タグを許可しないため、components.html() を使用
    components.html(html, height=600, scrolling=True)


def _export_to_csv(project_state: dict) -> str:
    """
    企画と台本をCSVにエクスポート

    Args:
        project_state: プロジェクト状態

    Returns:
        CSV文字列
    """
    ideas = project_state.get("data", {}).get("ideas", [])

    # DataFrameを作成
    table_data = []

    for i, idea in enumerate(ideas):
        # 台本情報を取得
        script_key = f"script_{i}"
        script = project_state.get("data", {}).get(script_key)

        if script:
            # 台本が生成済み
            previewer = ScriptPreviewer()
            preview = previewer.preview_script(script)

            status = "生成済み"
            narration_length = preview['narration_length']
            estimated_duration = f"{preview['estimated_duration']:.1f}"
            slide_count = preview['slide_count']
            full_script = script.get("full_script", "")
        else:
            # 台本未生成
            status = "未生成"
            narration_length = ""
            estimated_duration = ""
            slide_count = ""
            full_script = ""

        table_data.append({
            "No": idea.get("no", i+1),
            "企画タイトル": idea.get("title", ""),
            "狙い・内容": idea.get("summary", ""),
            "台本状況": status,
            "ナレーション文字数": narration_length,
            "推定読み上げ時間（秒）": estimated_duration,
            "スライド枚数": slide_count,
            "台本全文": full_script,
        })

    df = pd.DataFrame(table_data)

    # CSVに変換
    output = io.StringIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    return output.getvalue()


if __name__ == "__main__":
    main()
