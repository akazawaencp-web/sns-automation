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
from sns_automation.web.components import render_feedback_form, inject_styles, render_page_header, render_loading


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

    # 共通CSS注入
    inject_styles()

    # フィードバックフォーム
    render_feedback_form()

    render_page_header("戦略設計", "ステップバイステップで戦略を設計します。各項目を入力して、自動生成を活用してください。")

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

    # プログレスバー（3ステップに統合）
    total_steps = 3
    current_step = st.session_state.strategy_step
    # 旧ステップ番号との互換性（4以上は3に統合）
    display_step = min(current_step, 3)

    st.progress(display_step / total_steps, text=f"ステップ {display_step} / {total_steps}")

    # ステップごとの処理
    if current_step == 1:
        _render_step1_basic_info()
    elif current_step == 2:
        _render_step2_concept_generation()
    elif current_step >= 3:
        _render_step3_confirmation(selected_project, project_state)


def _render_step1_basic_info():
    """ステップ1: ターゲットの選定"""
    st.markdown("### ステップ1: ターゲットの選定")

    # 固定条件の表示
    st.info("**固定条件**: 20代男性・営業職")

    st.markdown("以下から1つ選択してください：")

    # ラジオボタンを2列グリッドで表示
    st.markdown("""
        <style>
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 0.3rem 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # ターゲット選択肢
    target_options = [
        "M&A仲介",
        "医薬品メーカー (MR)",
        "不動産仲介",
        "ハウスメーカー",
        "生命保険(外資大手_営業職)",
        "銀行",
        "証券",
        "人材紹介会社(キャリアアドバイザー)",
        "人材紹介会社(リクルーティングアドバイザー)",
        "部品メーカー",
        "食品メーカー",
        "飲料メーカー",
        "総合電気メーカー",
        "繊維商社",
        "鉄鋼商社",
        "医療機器メーカー",
        "医薬品卸(MS)",
        "損害保険",
        "生命保険(国内大手_総合職)",
        "不動産賃貸",
        "人材派遣会社",
        "自動車ディーラー",
        "SaaS",
        "SIer",
        "ITコンサル",
        "Webマーケティング",
        "その他（自分で入力）",
    ]

    # デフォルトの選択を設定
    default_index = 0
    saved_target = st.session_state.strategy_data.get("target", "")
    if saved_target in target_options:
        default_index = target_options.index(saved_target)

    selected_target = st.radio(
        "ターゲット",
        options=target_options,
        index=default_index,
        label_visibility="collapsed",
    )

    # 「その他」選択時のテキスト入力
    custom_target = ""
    if selected_target == "その他（自分で入力）":
        custom_target = st.text_input(
            "ターゲットを入力",
            value=st.session_state.strategy_data.get("custom_target", ""),
            placeholder="例: 建設業界の現場監督",
        )

    # 次へボタン
    if st.button("次へ →", use_container_width=True, type="primary"):
        # 「その他」の場合は入力値を使用
        if selected_target == "その他（自分で入力）":
            if not custom_target:
                st.warning("ターゲットを入力してください")
                st.stop()
            final_target = custom_target
            st.session_state.strategy_data["custom_target"] = custom_target
        else:
            final_target = selected_target

        # 固定値を設定
        st.session_state.strategy_data["role"] = "元業界人・キャリアチェンジ経験者"
        st.session_state.strategy_data["service"] = "業界のリアルと後悔しないキャリア選択を発信"
        st.session_state.strategy_data["target"] = final_target

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
            if st.button("次へ（残りを一括生成）→", type="primary", use_container_width=True):
                # 選択したコンセプトを保存
                st.session_state.strategy_data["selected_concept"] = concepts[selected_concept_index]
                st.session_state.strategy_data["selected_concept_index"] = selected_concept_index

                # ステップ3〜6を一括自動生成
                success = _batch_generate_steps_3_to_6()

                if success:
                    # ファイルに永続化
                    _save_strategy_data(
                        st.session_state.current_project,
                        3,  # 最終確認ステップ
                        st.session_state.strategy_data
                    )
                    st.session_state.strategy_step = 3
                    st.rerun()
                else:
                    st.error("一括生成中にエラーが発生しました。もう一度お試しください。")

    else:
        # コンセプト生成ボタン
        if st.button("勝ち筋コンセプト20案を生成", type="primary", use_container_width=True):
            loading = st.empty()
            try:
                claude = ClaudeAPI()

                variables = {
                    "role": st.session_state.strategy_data["role"],
                    "service": st.session_state.strategy_data["service"],
                    "target": st.session_state.strategy_data["target"],
                }

                render_loading(loading, "コンセプト20案を生成中", "AIが勝ち筋を分析しています...")

                prompt_data = load_prompt(
                    chapter="chapter1",
                    prompt_name="concept_generation",
                    variables=variables,
                )

                response = claude.generate_text(
                    prompt=prompt_data["user"],
                    system_prompt=prompt_data.get("system"),
                    temperature=prompt_data.get("temperature", 0.9),
                    max_tokens=prompt_data.get("max_tokens", 4000),
                )

                concepts = _parse_concepts(response)

                loading.empty()
                if concepts:
                    st.session_state.strategy_data["concepts"] = concepts
                    st.rerun()
                else:
                    st.error("コンセプトの生成に失敗しました。もう一度お試しください。")

            except FileNotFoundError:
                loading.empty()
                error_helpers.show_config_not_found_error()
            except Exception as e:
                loading.empty()
                st.error(f"エラーが発生しました: {e}")

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


def _batch_generate_steps_3_to_6() -> bool:
    """
    ステップ3〜6（ペルソナ → Pain → USP+Future → プロフィール）を一括生成する。

    Returns:
        成功した場合True
    """
    steps = [
        ("ペルソナを生成中", "persona"),
        ("Painを抽出中", "pains"),
        ("USP＋Futureを生成中", "usp_future"),
        ("プロフィール文を生成中", "profiles"),
    ]
    loading = st.empty()

    try:
        claude = ClaudeAPI()

        for step_idx, (step_label, step_key) in enumerate(steps):
            render_loading(loading, f"{step_label} ({step_idx+1}/4)", "AIが戦略を組み立てています...")

            if step_key == "persona" and not st.session_state.strategy_data.get("persona"):
                prompt_data = load_prompt(
                    chapter="chapter1",
                    prompt_name="persona_definition",
                    variables={"concept": st.session_state.strategy_data["selected_concept"]},
                )
                response = claude.generate_text(
                    prompt=prompt_data["user"],
                    system_prompt=prompt_data.get("system"),
                    temperature=prompt_data.get("temperature", 0.7),
                    max_tokens=prompt_data.get("max_tokens", 3000),
                )
                if not response:
                    loading.empty()
                    st.error("ペルソナの生成に失敗しました")
                    return False
                st.session_state.strategy_data["persona"] = response

            elif step_key == "pains" and not st.session_state.strategy_data.get("pains"):
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
                pains = _parse_pains(response) if response else []
                if not pains:
                    loading.empty()
                    st.error("Painの生成に失敗しました")
                    return False
                st.session_state.strategy_data["pains"] = pains

            elif step_key == "usp_future" and not st.session_state.strategy_data.get("usp_future"):
                pains = st.session_state.strategy_data.get("pains", [])
                pains_text = "\n".join([f"{i+1}. {pain}" for i, pain in enumerate(pains)])
                prompt_data = load_prompt(
                    chapter="chapter1",
                    prompt_name="usp_future_generation",
                    variables={
                        "pains": pains_text,
                        "service": st.session_state.strategy_data["service"],
                    },
                )
                response = claude.generate_text(
                    prompt=prompt_data["user"],
                    system_prompt=prompt_data.get("system"),
                    temperature=prompt_data.get("temperature", 0.8),
                    max_tokens=prompt_data.get("max_tokens", 2000),
                )
                if not response:
                    loading.empty()
                    st.error("USP＋Futureの生成に失敗しました")
                    return False
                st.session_state.strategy_data["usp_future"] = response

            elif step_key == "profiles" and not st.session_state.strategy_data.get("profiles"):
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
                profiles = _parse_profiles(response) if response else []
                if not profiles:
                    loading.empty()
                    st.error("プロフィール文の生成に失敗しました")
                    return False
                st.session_state.strategy_data["profiles"] = profiles

        loading.empty()
        return True

    except Exception as e:
        loading.empty()
        st.error(f"一括生成中にエラーが発生しました: {e}")
        return False


def _render_step3_confirmation(project_name: str, project_state: dict):
    """ステップ3: 最終確認と保存（旧ステップ7）"""
    st.subheader("ステップ3: 最終確認")

    st.markdown("全ての生成が完了しました。内容を確認して、保存してください。")

    # 基本情報
    with st.expander("基本情報", expanded=True):
        st.markdown(f"**役割:** {st.session_state.strategy_data.get('role', '')}")
        st.markdown(f"**サービス:** {st.session_state.strategy_data.get('service', '')}")
        st.markdown(f"**ターゲット:** {st.session_state.strategy_data.get('target', '')}")

    # コンセプト
    with st.expander("勝ち筋コンセプト", expanded=True):
        st.markdown(f"**選択したコンセプト:** {st.session_state.strategy_data.get('selected_concept', '')}")

    # ペルソナ
    with st.expander("ペルソナ"):
        persona_text = st.session_state.strategy_data.get("persona", "")
        st.text_area("ペルソナ内容", value=persona_text, height=300, disabled=True, label_visibility="collapsed")

    # Pain
    with st.expander("Pain（20個）"):
        pains = st.session_state.strategy_data.get("pains", [])
        for i, pain in enumerate(pains, 1):
            st.markdown(f"{i}. {pain}")

    # USP+Future
    with st.expander("USP＋Future"):
        usp_future_text = st.session_state.strategy_data.get("usp_future", "")
        st.text_area("USP＋Future内容", value=usp_future_text, height=200, disabled=True, label_visibility="collapsed")

    # プロフィール選択
    profiles = st.session_state.strategy_data.get("profiles", [])
    if profiles:
        with st.expander("プロフィール文（1つ選択）", expanded=True):
            selected_profile_index = st.radio(
                "採用するプロフィール文を選択してください",
                range(len(profiles)),
                format_func=lambda i: f"案{i+1}",
                key="selected_profile_radio",
            )
            st.text_area(
                "プロフィール文プレビュー",
                value=profiles[selected_profile_index],
                height=150,
                disabled=True,
                label_visibility="collapsed",
            )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("← コンセプト選択に戻る", use_container_width=True):
            st.session_state.strategy_step = 2
            st.rerun()

    with col2:
        if st.button("保存して完了", type="primary", use_container_width=True):
            # プロフィール選択を保存
            if profiles:
                st.session_state.strategy_data["selected_profile"] = profiles[selected_profile_index]
                st.session_state.strategy_data["selected_profile_index"] = selected_profile_index

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
                    **project_state.get("metadata", {}),
                }
            )

            st.success("戦略設計を保存しました！")
            st.balloons()

            # セッションをリセット
            st.session_state.strategy_step = 1
            st.session_state.strategy_data = {}

            st.info("次は「コンテンツ量産」ページで企画・台本を生成してください。")

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


if __name__ == "__main__":
    main()
