"""
戦略設計ページ（Chapter 1 UI）

ステップバイステップのウィザード形式で戦略設計を実行
"""

import streamlit as st
from pathlib import Path
import json
from datetime import datetime

from sns_automation.utils import (
    load_config,
    ClaudeAPI,
    load_prompt,
    StateManager,
    error_helpers,
)
from sns_automation.web.components import render_feedback_form


def _save_strategy_data(project_name: str, step: int, strategy_data: dict):
    """
    戦略設計のデータを保存する（StateManager経由でローカル + Google Sheets）

    Args:
        project_name: プロジェクト名
        step: 現在のステップ番号
        strategy_data: 戦略データ
    """
    # 既存データを読み込む
    sm = StateManager(project_name)
    state = sm.load_state() or {"project_name": project_name, "data": {}, "metadata": {}}

    # 戦略データを更新
    data = state.get("data", {})
    data["strategy"] = strategy_data
    data["current_step"] = step

    metadata = state.get("metadata", {})

    # StateManagerで保存（ローカル + Google Sheets）
    sm.save_state(
        chapter=1,
        step="strategy_design",
        data=data,
        metadata=metadata,
    )


def main():
    st.set_page_config(
        page_title="戦略設計 - SNS Automation",
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

        .stProgress > div > div {
            background: linear-gradient(135deg, #ea8768 0%, #33b6de 100%) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # フィードバックフォーム
    render_feedback_form()

    st.markdown('<div class="page-header">戦略設計</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">ステップバイステップで戦略を設計します。各項目を入力して、自動生成を活用してください。</div>', unsafe_allow_html=True)

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

    st.success(f"プロジェクト「{selected_project}」を選択中")

    # StateManager.load_state()のdata内にstrategyとcurrent_stepがある
    project_data = project_state.get("data", {})

    # プロジェクト選択が変更されたか確認
    if "current_project" not in st.session_state or st.session_state.current_project != selected_project:
        st.session_state.current_project = selected_project
        # プロジェクトが変更されたら、データを読み込む
        st.session_state.strategy_step = project_data.get("current_step", project_state.get("current_step", 1))
        st.session_state.strategy_data = project_data.get("strategy", project_state.get("strategy", {}))

    # セッション状態の初期化（初回のみ）
    if "strategy_step" not in st.session_state:
        st.session_state.strategy_step = project_data.get("current_step", project_state.get("current_step", 1))

    if "strategy_data" not in st.session_state:
        st.session_state.strategy_data = project_data.get("strategy", project_state.get("strategy", {}))

    st.markdown("---")

    # プログレスバー
    total_steps = 7
    current_step = st.session_state.strategy_step

    st.progress(current_step / total_steps, text=f"ステップ {current_step} / {total_steps}")

    # ステップごとの処理
    if current_step == 1:
        _render_step1_basic_info()
    elif current_step == 2:
        _render_step2_concept_generation()
    elif current_step == 3:
        _render_step3_persona()
    elif current_step == 4:
        _render_step4_pains()
    elif current_step == 5:
        _render_step5_usp_future()
    elif current_step == 6:
        _render_step6_profile()
    elif current_step == 7:
        _render_step7_confirmation(selected_project, project_state)


def _render_step1_basic_info():
    """ステップ1: ターゲット候補の生成と選択"""
    st.markdown("### ステップ1: ターゲットの選定")

    # 固定条件の表示
    st.info("**固定条件**: 20代男性・営業職")

    # 業界キーワード選択
    keyword_options = ["証券", "IT", "商社", "不動産", "保険", "メーカー", "広告", "人材", "SaaS", "銀行"]
    default_idx = 0
    saved_keyword = st.session_state.strategy_data.get("target_keyword", "")
    if saved_keyword in keyword_options:
        default_idx = keyword_options.index(saved_keyword)
    keyword = st.selectbox(
        "業界キーワード",
        keyword_options,
        index=default_idx,
    )

    # ターゲット候補生成ボタン
    col1, col2 = st.columns([3, 1])
    with col1:
        generate_btn = st.button("ターゲット候補を10個生成", use_container_width=True)
    with col2:
        if st.session_state.strategy_data.get("target_candidates"):
            regenerate_btn = st.button("再生成", use_container_width=True)
        else:
            regenerate_btn = False

    # 生成実行
    if generate_btn or regenerate_btn:
        with st.spinner("AIがターゲット候補を生成中..."):
            # キーワードがない場合はデフォルト
            search_keyword = keyword if keyword else "転職を考えている営業職"

            try:
                # 設定を読み込み
                # config = load_config()  # Streamlit Cloud対応: 不要
                claude = ClaudeAPI()

                # プロンプトを読み込み
                prompt_data = load_prompt(
                    chapter="chapter1",
                    prompt_name="target_suggestion",
                    variables={"keyword": search_keyword}
                )

                # Claude APIで生成
                candidates_text = claude.generate_text(
                    prompt=prompt_data["user"],
                    system_prompt=prompt_data.get("system"),
                    temperature=prompt_data.get("temperature", 0.8),
                    max_tokens=prompt_data.get("max_tokens", 2000),
                )

                # 候補をパース
                candidates = _parse_target_candidates(candidates_text)

                if candidates:
                    # セッションに保存
                    st.session_state.strategy_data["target_keyword"] = keyword
                    st.session_state.strategy_data["target_candidates"] = candidates
                    st.session_state.strategy_data["target_candidates_text"] = candidates_text

                    # ファイルに永続化
                    _save_strategy_data(
                        st.session_state.current_project,
                        1,  # 現在のステップ
                        st.session_state.strategy_data
                    )

                    st.success(f"{len(candidates)}個のターゲット候補を生成しました！")
                    st.rerun()
                else:
                    st.error("ターゲット候補の生成に失敗しました。もう一度お試しください。")

            except FileNotFoundError:
                error_helpers.show_config_not_found_error()
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                with st.expander("エラーの詳細"):
                    import traceback
                    st.code(traceback.format_exc(), language="text")

    # ターゲット候補の選択UI
    if st.session_state.strategy_data.get("target_candidates"):
        st.markdown("---")
        st.markdown("### 生成されたターゲット候補")
        st.markdown("以下から1つ選択してください：")

        candidates = st.session_state.strategy_data["target_candidates"]

        # デフォルトの選択を設定
        default_index = 0
        if st.session_state.strategy_data.get("target") in candidates:
            default_index = candidates.index(st.session_state.strategy_data["target"])

        selected_target = st.radio(
            "ターゲット候補",
            options=candidates,
            index=default_index,
            label_visibility="collapsed"
        )

        # 次へボタン
        if st.button("次へ →", use_container_width=True, type="primary"):
            # 固定値を設定
            st.session_state.strategy_data["role"] = "元業界人・キャリアチェンジ経験者"
            st.session_state.strategy_data["service"] = "業界のリアルと後悔しないキャリア選択を発信"
            st.session_state.strategy_data["target"] = selected_target

            # ファイルに永続化
            _save_strategy_data(
                st.session_state.current_project,
                2,  # 次のステップ
                st.session_state.strategy_data
            )

            st.session_state.strategy_step = 2
            st.rerun()


def _render_step2_concept_generation():
    """ステップ2: 勝ち筋コンセプト生成"""
    st.subheader("ステップ2: 勝ち筋コンセプトの生成")

    st.markdown("""
    入力した情報をもとに、勝ち筋コンセプト20案を自動生成します。
    """)

    # 入力情報の確認
    with st.expander("入力した情報を確認"):
        st.markdown(f"**役割:** {st.session_state.strategy_data.get('role', '')}")
        st.markdown(f"**サービス:** {st.session_state.strategy_data.get('service', '')}")
        st.markdown(f"**ターゲット:** {st.session_state.strategy_data.get('target', '')}")

    # コンセプトが既に生成されている場合
    concepts = st.session_state.strategy_data.get("concepts", [])

    if concepts:
        st.success(f"{len(concepts)}案のコンセプトを生成済み")

        # コンセプト一覧を表示
        st.subheader("生成されたコンセプト")

        selected_concept_index = st.radio(
            "採用するコンセプトを選択してください",
            range(len(concepts)),
            format_func=lambda i: f"{i+1}. {concepts[i]}",
            key="selected_concept",
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.strategy_step = 1
                st.rerun()

        with col2:
            if st.button("次へ →", type="primary", use_container_width=True):
                # 選択したコンセプトを保存
                st.session_state.strategy_data["selected_concept"] = concepts[selected_concept_index]
                st.session_state.strategy_data["selected_concept_index"] = selected_concept_index

                # ファイルに永続化
                _save_strategy_data(
                    st.session_state.current_project,
                    3,  # 次のステップ
                    st.session_state.strategy_data
                )

                # 次のステップへ
                st.session_state.strategy_step = 3
                st.rerun()

    else:
        # コンセプト生成ボタン
        if st.button("勝ち筋コンセプト20案を生成", type="primary", use_container_width=True):
            with st.spinner("コンセプトを生成中...（約30秒かかります）"):
                try:
                    # 設定を読み込み
                    # config = load_config()  # Streamlit Cloud対応: 不要
                    claude = ClaudeAPI()

                    # プロンプトを読み込み
                    variables = {
                        "role": st.session_state.strategy_data["role"],
                        "service": st.session_state.strategy_data["service"],
                        "target": st.session_state.strategy_data["target"],
                    }

                    # デバッグ: 変数を表示
                    with st.expander("デバッグ: 送信する変数"):
                        st.json(variables)

                    prompt_data = load_prompt(
                        chapter="chapter1",
                        prompt_name="concept_generation",
                        variables=variables,
                    )

                    # デバッグ: 実際のプロンプトを表示
                    with st.expander("デバッグ: 実際に送信するプロンプト"):
                        st.text_area("User Prompt", prompt_data["user"], height=300)

                    # Claude APIで生成
                    response = claude.generate_text(
                        prompt=prompt_data["user"],
                        system_prompt=prompt_data.get("system"),
                        temperature=prompt_data.get("temperature", 0.9),
                        max_tokens=prompt_data.get("max_tokens", 4000),
                    )

                    # レスポンスをパース
                    concepts = _parse_concepts(response)

                    if concepts:
                        st.session_state.strategy_data["concepts"] = concepts
                        st.success(f"{len(concepts)}案のコンセプトを生成しました！")
                        st.rerun()
                    else:
                        # デバッグ情報を表示
                        st.error("コンセプトの生成に失敗しました。もう一度お試しください。")
                        with st.expander("デバッグ情報（開発者向け）"):
                            st.text("Claude APIのレスポンス（最初の1000文字）:")
                            st.code(response[:1000], language="text")

                except FileNotFoundError:
                    error_helpers.show_config_not_found_error()
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
                    # エラーの詳細を表示
                    with st.expander("エラーの詳細"):
                        import traceback
                        st.code(traceback.format_exc(), language="text")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.strategy_step = 1
                st.rerun()


def _parse_concepts(response: str) -> list:
    """
    Claude APIのレスポンスからコンセプトをパース

    Args:
        response: APIレスポンステキスト

    Returns:
        コンセプトリスト
    """
    import re

    concepts = []

    for line in response.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 番号付きリスト（1. 1) １. １） 1． など）をパース
        # 正規表現: 行頭 + 数字（半角・全角） + ピリオドまたは括弧（半角・全角） + 空白（任意） + テキスト
        match = re.match(r'^[0-9０-９]+[.\)）．。][\s　]*(.+)', line)
        if match:
            concept = match.group(1).strip()
            if concept and len(concepts) < 20:
                concepts.append(concept)

    return concepts


def _parse_target_candidates(response: str) -> list:
    """
    Claude APIのレスポンスからターゲット候補をパース

    Args:
        response: APIレスポンステキスト

    Returns:
        ターゲット候補リスト
    """
    import re

    candidates = []

    for line in response.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 番号付きリスト（1. 1) １. １） 1． など）をパース
        match = re.match(r'^[0-9０-９]+[.\)）．。][\s　]*(.+)', line)
        if match:
            candidate = match.group(1).strip()
            if candidate and len(candidates) < 10:
                candidates.append(candidate)

    return candidates


def _render_step3_persona():
    """ステップ3: ペルソナの詳細化（Claude API自動生成）"""
    st.subheader("ステップ3: ペルソナの詳細化")

    st.markdown(f"""
    選択したコンセプト: **{st.session_state.strategy_data.get('selected_concept', '')}**

    ターゲットのペルソナを、まるで実在する人物かのように生々しく定義します。
    """)

    # ペルソナが既に生成されている場合
    persona_text = st.session_state.strategy_data.get("persona", "")

    if persona_text:
        st.success("ペルソナを生成済み")

        # 生成されたペルソナを表示・編集可能に
        st.subheader("生成されたペルソナ")

        edited_persona = st.text_area(
            "ペルソナの内容（編集可能）",
            value=persona_text,
            height=400,
            help="必要に応じて内容を編集できます"
        )

        # 編集内容を保存
        if edited_persona != persona_text:
            st.session_state.strategy_data["persona"] = edited_persona

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.strategy_step = 2
                st.rerun()

        with col2:
            if st.button("再生成", use_container_width=True):
                # ペルソナをクリアして再生成
                st.session_state.strategy_data["persona"] = ""
                st.rerun()

        with col3:
            if st.button("次へ →", type="primary", use_container_width=True):
                st.session_state.strategy_data["persona"] = edited_persona

                # ファイルに永続化
                _save_strategy_data(
                    st.session_state.current_project,
                    4,  # 次のステップ
                    st.session_state.strategy_data
                )

                st.session_state.strategy_step = 4
                st.rerun()

    else:
        # ペルソナ生成ボタン
        if st.button("ペルソナ10項目を自動生成", type="primary", use_container_width=True):
            with st.spinner("ペルソナを生成中...（約30秒かかります）"):
                try:
                    # 設定を読み込み
                    # config = load_config()  # Streamlit Cloud対応: 不要
                    claude = ClaudeAPI()

                    # プロンプトを読み込み
                    prompt_data = load_prompt(
                        chapter="chapter1",
                        prompt_name="persona_definition",
                        variables={
                            "concept": st.session_state.strategy_data["selected_concept"],
                        },
                    )

                    # Claude APIで生成
                    response = claude.generate_text(
                        prompt=prompt_data["user"],
                        system_prompt=prompt_data.get("system"),
                        temperature=prompt_data.get("temperature", 0.7),
                        max_tokens=prompt_data.get("max_tokens", 3000),
                    )

                    # レスポンスを保存
                    if response:
                        st.session_state.strategy_data["persona"] = response
                        st.success("ペルソナを生成しました！")
                        st.rerun()
                    else:
                        st.error("ペルソナの生成に失敗しました。もう一度お試しください。")

                except FileNotFoundError:
                    error_helpers.show_config_not_found_error()
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
                    # エラーの詳細を表示
                    with st.expander("エラーの詳細"):
                        import traceback
                        st.code(traceback.format_exc(), language="text")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.strategy_step = 2
                st.rerun()


def _render_step4_pains():
    """ステップ4: Painの抽出"""
    st.subheader("ステップ4: Painの抽出（20個）")

    st.markdown("""
    ペルソナが抱える「Pain」（悩み・不安・フラストレーション）を20個抽出します。
    自動生成するか、手動で入力してください。
    """)

    pains = st.session_state.strategy_data.get("pains", [])

    if pains:
        st.success(f"{len(pains)}個のPainを抽出済み")

        # Pain一覧を編集可能なフォームで表示
        with st.form("pains_edit_form"):
            st.subheader("Painリスト（編集可能）")

            edited_pains = []
            for i, pain in enumerate(pains):
                edited_pain = st.text_input(
                    f"{i+1}.",
                    value=pain,
                    key=f"pain_{i}",
                )
                edited_pains.append(edited_pain)

            col1, col2 = st.columns(2)

            with col1:
                back = st.form_submit_button("← 戻る", use_container_width=True)

            with col2:
                submitted = st.form_submit_button("次へ →", type="primary", use_container_width=True)

            if back:
                st.session_state.strategy_step = 3
                st.rerun()

            if submitted:
                # 編集後のPainを保存
                st.session_state.strategy_data["pains"] = [p for p in edited_pains if p]
                st.session_state.strategy_step = 5
                st.rerun()

    else:
        # Pain自動生成ボタン
        if st.button("Painを自動生成（20個）", type="primary", use_container_width=True):
            with st.spinner("Painを生成中...（約30秒かかります）"):
                try:
                    # config = load_config()  # Streamlit Cloud対応: 不要
                    claude = ClaudeAPI()

                    # ペルソナ情報を取得（文字列として保存されている）
                    persona_text = st.session_state.strategy_data.get("persona", "")

                    prompt_data = load_prompt(
                        chapter="chapter1",
                        prompt_name="pain_extraction",
                        variables={
                            "persona": persona_text,
                            "target": st.session_state.strategy_data["target"],
                        },
                    )

                    response = claude.generate_text(
                        prompt=prompt_data["user"],
                        system_prompt=prompt_data.get("system"),
                        temperature=prompt_data.get("temperature", 0.7),
                        max_tokens=prompt_data.get("max_tokens", 3000),
                    )

                    # レスポンスをパース
                    pains = _parse_pains(response)

                    if pains:
                        st.session_state.strategy_data["pains"] = pains
                        st.success(f"{len(pains)}個のPainを生成しました！")
                        st.rerun()
                    else:
                        st.error("Painの生成に失敗しました。もう一度お試しください。")

                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

        st.markdown("---")

        if st.button("← 戻る", use_container_width=True):
            st.session_state.strategy_step = 3
            st.rerun()


def _parse_pains(response: str) -> list:
    """
    Claude APIのレスポンスからPainをパース

    Args:
        response: APIレスポンステキスト

    Returns:
        Painリスト
    """
    pains = []

    for line in response.split("\n"):
        line = line.strip()

        # 番号付きリストをパース
        for i in range(1, 25):
            for prefix in [f"{i}.", f"{i})"]:
                if line.startswith(prefix):
                    pain = line[len(prefix):].strip()
                    if pain:
                        pains.append(pain)
                    break

    return pains[:20]


def _render_step5_usp_future():
    """ステップ5: USP＋Futureの定義（Claude API自動生成）"""
    st.subheader("ステップ5: USP＋Futureの定義")

    st.markdown("""
    ペルソナのPain（20個）をもとに、「USP（常識の破壊）」と「Future（感情的解放）」を自動生成します。
    """)

    # USP+Futureが既に生成されている場合
    usp_future_text = st.session_state.strategy_data.get("usp_future", "")

    if usp_future_text:
        st.success("USP＋Futureを生成済み")

        # 生成されたUSP+Futureを表示・編集可能に
        st.subheader("生成されたUSP＋Future")

        edited_usp_future = st.text_area(
            "USP＋Futureの内容（編集可能）",
            value=usp_future_text,
            height=400,
            help="必要に応じて内容を編集できます"
        )

        # 編集内容を保存
        if edited_usp_future != usp_future_text:
            st.session_state.strategy_data["usp_future"] = edited_usp_future

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.strategy_step = 4
                st.rerun()

        with col2:
            if st.button("再生成", use_container_width=True):
                # USP+Futureをクリアして再生成
                st.session_state.strategy_data["usp_future"] = ""
                st.rerun()

        with col3:
            if st.button("次へ →", type="primary", use_container_width=True):
                st.session_state.strategy_data["usp_future"] = edited_usp_future

                # ファイルに永続化
                _save_strategy_data(
                    st.session_state.current_project,
                    6,  # 次のステップ
                    st.session_state.strategy_data
                )

                st.session_state.strategy_step = 6
                st.rerun()

    else:
        # USP+Future生成ボタン
        if st.button("USP＋Futureを自動生成", type="primary", use_container_width=True):
            with st.spinner("USP＋Futureを生成中...（約30秒かかります）"):
                try:
                    # 設定を読み込み
                    # config = load_config()  # Streamlit Cloud対応: 不要
                    claude = ClaudeAPI()

                    # Painリストを整形
                    pains = st.session_state.strategy_data.get("pains", [])
                    pains_text = "\n".join([f"{i+1}. {pain}" for i, pain in enumerate(pains)])

                    # プロンプトを読み込み
                    prompt_data = load_prompt(
                        chapter="chapter1",
                        prompt_name="usp_future_generation",
                        variables={
                            "pains": pains_text,
                            "service": st.session_state.strategy_data["service"],
                        },
                    )

                    # Claude APIで生成
                    response = claude.generate_text(
                        prompt=prompt_data["user"],
                        system_prompt=prompt_data.get("system"),
                        temperature=prompt_data.get("temperature", 0.8),
                        max_tokens=prompt_data.get("max_tokens", 2000),
                    )

                    # レスポンスを保存
                    if response:
                        st.session_state.strategy_data["usp_future"] = response
                        st.success("USP＋Futureを生成しました！")
                        st.rerun()
                    else:
                        st.error("USP＋Futureの生成に失敗しました。もう一度お試しください。")

                except FileNotFoundError:
                    error_helpers.show_config_not_found_error()
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
                    # エラーの詳細を表示
                    with st.expander("エラーの詳細"):
                        import traceback
                        st.code(traceback.format_exc(), language="text")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.strategy_step = 4
                st.rerun()


def _render_step6_profile():
    """ステップ6: プロフィール文作成"""
    st.subheader("ステップ6: プロフィール文作成")

    st.markdown("""
    SNSアカウントのプロフィール文を自動生成します。3案生成されるので、最も良いものを選択してください。
    """)

    profiles = st.session_state.strategy_data.get("profiles", [])

    if profiles:
        st.success(f"{len(profiles)}案のプロフィール文を生成済み")

        # プロフィール選択
        selected_profile_index = st.radio(
            "採用するプロフィール文を選択してください",
            range(len(profiles)),
            format_func=lambda i: f"案{i+1}",
            key="selected_profile",
        )

        st.text_area(
            "プロフィール文",
            value=profiles[selected_profile_index],
            height=150,
            disabled=True,
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.strategy_step = 5
                st.rerun()

        with col2:
            if st.button("再生成", use_container_width=True):
                # プロフィールをクリアして再生成
                st.session_state.strategy_data["profiles"] = []
                st.rerun()

        with col3:
            if st.button("次へ →", type="primary", use_container_width=True):
                st.session_state.strategy_data["selected_profile"] = profiles[selected_profile_index]
                st.session_state.strategy_data["selected_profile_index"] = selected_profile_index
                st.session_state.strategy_step = 7
                st.rerun()

    else:
        # プロフィール生成ボタン
        if st.button("プロフィール文を生成（3案）", type="primary", use_container_width=True):
            with st.spinner("プロフィール文を生成中...（約20秒かかります）"):
                try:
                    # config = load_config()  # Streamlit Cloud対応: 不要
                    claude = ClaudeAPI()

                    prompt_data = load_prompt(
                        chapter="chapter1",
                        prompt_name="profile_generation",
                        variables={
                            "concept": st.session_state.strategy_data["selected_concept"],
                            "usp_future": st.session_state.strategy_data.get("usp_future", ""),
                            "target": st.session_state.strategy_data["target"],
                        },
                    )

                    response = claude.generate_text(
                        prompt=prompt_data["user"],
                        system_prompt=prompt_data.get("system"),
                        temperature=prompt_data.get("temperature", 0.8),
                        max_tokens=prompt_data.get("max_tokens", 2000),
                    )

                    # レスポンスをパース
                    profiles = _parse_profiles(response)

                    if profiles:
                        st.session_state.strategy_data["profiles"] = profiles
                        st.success(f"{len(profiles)}案のプロフィール文を生成しました！")
                        st.rerun()
                    else:
                        st.error("プロフィール文の生成に失敗しました。もう一度お試しください。")

                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")

        st.markdown("---")

        if st.button("← 戻る", use_container_width=True):
            st.session_state.strategy_step = 5
            st.rerun()


def _parse_profiles(response: str) -> list:
    """
    Claude APIのレスポンスからプロフィール文をパース

    Args:
        response: APIレスポンステキスト

    Returns:
        プロフィール文リスト
    """
    profiles = []
    current_profile = []
    in_profile = False

    for line in response.split("\n"):
        line = line.strip()

        # 案1、案2、案3の開始を検出
        if line.startswith("案1") or line.startswith("案2") or line.startswith("案3"):
            if current_profile:
                profiles.append("\n".join(current_profile))
                current_profile = []
            in_profile = True
            # 案X: の後のテキストを取得
            if ":" in line:
                text = line.split(":", 1)[1].strip()
                if text:
                    current_profile.append(text)
            continue

        if in_profile and line:
            current_profile.append(line)

    # 最後のプロフィールを追加
    if current_profile:
        profiles.append("\n".join(current_profile))

    return profiles[:3]


def _render_step7_confirmation(project_name: str, project_state: dict):
    """ステップ7: 最終確認と保存"""
    st.subheader("ステップ7: 最終確認")

    st.markdown("""
    全ての入力が完了しました！内容を確認して、保存してください。
    """)

    # 入力内容の確認
    st.subheader("入力内容")

    with st.expander("基本情報", expanded=True):
        st.markdown(f"**役割:** {st.session_state.strategy_data.get('role', '')}")
        st.markdown(f"**サービス:** {st.session_state.strategy_data.get('service', '')}")
        st.markdown(f"**ターゲット:** {st.session_state.strategy_data.get('target', '')}")

    with st.expander("勝ち筋コンセプト"):
        st.markdown(f"**選択したコンセプト:** {st.session_state.strategy_data.get('selected_concept', '')}")

    with st.expander("ペルソナ"):
        persona_text = st.session_state.strategy_data.get("persona", "")
        st.text_area("", value=persona_text, height=300, disabled=True)

    with st.expander("Pain（最初の5個のみ表示）"):
        pains = st.session_state.strategy_data.get("pains", [])
        for i, pain in enumerate(pains[:5], 1):
            st.markdown(f"{i}. {pain}")
        if len(pains) > 5:
            st.markdown(f"...他{len(pains) - 5}個")

    with st.expander("USP＋Future"):
        usp_future_text = st.session_state.strategy_data.get("usp_future", "")
        st.text_area("", value=usp_future_text, height=200, disabled=True)

    with st.expander("プロフィール文"):
        st.markdown(st.session_state.strategy_data.get("selected_profile", ""))

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("← 戻る", use_container_width=True):
            st.session_state.strategy_step = 6
            st.rerun()

    with col2:
        if st.button("保存して完了", type="primary", use_container_width=True):
            # StateManagerに保存
            state_manager = StateManager(project_name)

            state_manager.save_state(
                chapter=1,
                step="completed",
                data=st.session_state.strategy_data,
                metadata={
                    "project_name": project_name,
                    "target": st.session_state.strategy_data.get("target", ""),
                    "concept": st.session_state.strategy_data.get("selected_concept", ""),
                }
            )

            st.success("戦略設計を保存しました！")
            st.balloons()

            # セッションをリセット
            st.session_state.strategy_step = 1
            st.session_state.strategy_data = {}

            st.info("次は「コンテンツ量産」ページで企画・台本を生成してください。")


if __name__ == "__main__":
    main()
