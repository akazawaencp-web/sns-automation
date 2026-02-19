"""
SNS Automation Web UI - メインアプリ

Streamlitベースのマルチページアプリケーション
"""

import streamlit as st
from pathlib import Path
from sns_automation.utils import StateManager
from sns_automation.web.components import render_feedback_form, inject_styles, inject_feature_card_styles


def main():
    """メインアプリケーション"""

    # ページ設定
    st.set_page_config(
        page_title="SNS Automation Platform",
        page_icon="▲",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 共通CSS注入
    inject_styles()
    inject_feature_card_styles()

    # ヘッダー
    st.markdown('<div class="main-header">SNS Automation Platform</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="main-subtitle">'
        'SNSアカウント構築・運用を自動化するオールインワンシステム'
        '</p>',
        unsafe_allow_html=True
    )

    # 統計情報
    st.markdown('<div class="section-header">ダッシュボード</div>', unsafe_allow_html=True)

    # 状態ディレクトリから全プロジェクトを取得
    state_dir = Path.home() / ".sns-automation" / "states"
    state_dir.mkdir(parents=True, exist_ok=True)

    state_files = list(state_dir.glob("*.json"))
    total_projects = len(state_files)

    # 統計情報を表示 - vertical_alignmentで高さ揃え
    col1, col2, col3, col4 = st.columns(4, vertical_alignment="top")

    # 完了したプロジェクト数（Chapter 3完了）
    completed = sum(1 for f in state_files if _is_completed(f))
    # 総企画数
    total_ideas = _count_total_ideas(state_files)
    # 総台本数
    total_scripts = _count_total_scripts(state_files)

    with col1:
        st.metric(
            label="管理中のアカウント",
            value=total_projects,
            delta="現在管理しているプロジェクト数",
            delta_color="off"
        )

    with col2:
        st.metric(
            label="コンテンツ生成完了",
            value=completed,
            delta="Chapter 3まで完了したアカウント",
            delta_color="off"
        )

    with col3:
        st.metric(
            label="総企画数",
            value=total_ideas,
            delta="生成された企画の総数",
            delta_color="off"
        )

    with col4:
        st.metric(
            label="総台本数",
            value=total_scripts,
            delta="作成された台本の総数",
            delta_color="off"
        )

    st.markdown("---")

    # 機能紹介
    st.markdown('<div class="section-header">主要機能</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2, vertical_alignment="top")

    with col1:
        st.markdown("""
        <div class="feature-card-container">
            <h3>アカウント管理</h3>
            <p>最大60アカウントを一元管理。進捗状況を可視化し、効率的な運用をサポート。</p>
            <ul>
                <li>プロジェクト作成・削除</li>
                <li>進捗状況の可視化</li>
                <li>データ永続化による中断・再開</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card-container">
            <h3>コンテンツ量産</h3>
            <p>企画20案を自動生成。訴求タイプの分析、台本のプレビュー、音声生成まで一気通貫。</p>
            <ul>
                <li>企画の傾向分析（6種類の訴求タイプ）</li>
                <li>台本の品質チェック（文字数・時間）</li>
                <li>音声の自動生成と再生</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card-container">
            <h3>戦略設計</h3>
            <p>対話形式でペルソナ、Pain、USPを定義。勝ち筋コンセプトを自動生成。</p>
            <ul>
                <li>ペルソナの詳細化（10項目）</li>
                <li>20個のPain抽出</li>
                <li>USP＆プロフィール文作成</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="feature-card-container">
            <h3>競合分析</h3>
            <p>Instagram動画から静止画を抽出し、画像分析。横断分析で鉄則を自動抽出。</p>
            <ul>
                <li>動画から5枚の静止画を自動抽出</li>
                <li>Claude Visionで画像分析</li>
                <li>横断分析で成功パターンを発見</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


    st.markdown("---")

    # クイックスタート
    st.markdown('<div class="section-header">クイックスタート</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-card-container">
        <h3>使い方</h3>
        <ol>
            <li><strong>左サイドバー</strong>から「アカウント管理」に移動</li>
            <li>新規プロジェクトを作成</li>
            <li><strong>戦略設計</strong>でペルソナ・Painを定義</li>
            <li><strong>コンテンツ量産</strong>で企画・台本を自動生成</li>
            <li>音声ファイルをダウンロードして投稿</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    # フィードバックフォーム
    render_feedback_form()

    # フッター
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #999; font-size: 0.9rem; margin-top: 2rem;">'
        'Powered by Claude API'
        '</p>',
        unsafe_allow_html=True
    )


def _is_completed(state_file: Path) -> bool:
    """
    プロジェクトが完了しているか判定

    Args:
        state_file: 状態ファイルのパス

    Returns:
        完了している場合True
    """
    import json

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        return state.get("last_chapter") == 3 and state.get("last_step") == "completed"
    except:
        return False


def _count_total_ideas(state_files: list) -> int:
    """
    全プロジェクトの総企画数をカウント

    Args:
        state_files: 状態ファイルのリスト

    Returns:
        総企画数
    """
    import json

    total = 0
    for state_file in state_files:
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            if state.get("last_chapter") == 3:
                ideas = state.get("data", {}).get("ideas", [])
                total += len(ideas)
        except:
            continue

    return total


def _count_total_scripts(state_files: list) -> int:
    """
    全プロジェクトの総台本数をカウント

    Args:
        state_files: 状態ファイルのリスト

    Returns:
        総台本数
    """
    import json

    total = 0
    for state_file in state_files:
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            if state.get("last_chapter") == 3:
                scripts = state.get("data", {}).get("scripts", [])
                total += len(scripts)
        except:
            continue

    return total


if __name__ == "__main__":
    main()
