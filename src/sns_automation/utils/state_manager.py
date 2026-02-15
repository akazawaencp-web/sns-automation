"""
状態管理モジュール

セッションの進捗を保存・復元し、中断・再開を可能にする
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StateManager:
    """セッション状態を管理するクラス"""

    def __init__(self, project_name: str = "default"):
        """
        初期化

        Args:
            project_name: プロジェクト名（アカウント名など）
        """
        self.project_name = project_name
        self.state_dir = Path.home() / ".sns-automation" / "states"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"{project_name}.json"

    def save_state(
        self,
        chapter: int,
        step: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        状態を保存

        Args:
            chapter: チャプター番号（1, 3）
            step: ステップ名（例: "concept_generation", "persona_definition"）
            data: 保存するデータ
            metadata: 追加のメタデータ
        """
        state = {
            "project_name": self.project_name,
            "last_chapter": chapter,
            "last_step": step,
            "data": data,
            "metadata": metadata or {},
            "updated_at": datetime.now().isoformat(),
        }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        logger.info(f"状態を保存しました: {self.state_file}")

    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        状態を読み込む

        Returns:
            状態辞書（存在しない場合はNone）
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            logger.info(f"状態を読み込みました: {self.state_file}")
            return state
        except Exception as e:
            logger.error(f"状態の読み込みに失敗しました: {e}")
            return None

    def has_state(self) -> bool:
        """
        保存された状態が存在するかチェック

        Returns:
            存在する場合True
        """
        return self.state_file.exists()

    def delete_state(self) -> None:
        """状態を削除"""
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info(f"状態を削除しました: {self.state_file}")

    def get_summary(self) -> Optional[str]:
        """
        状態のサマリーを取得

        Returns:
            サマリー文字列（存在しない場合はNone）
        """
        state = self.load_state()
        if not state:
            return None

        chapter = state.get("last_chapter")
        step = state.get("last_step")
        updated_at = state.get("updated_at", "")

        # 日時をフォーマット
        try:
            dt = datetime.fromisoformat(updated_at)
            formatted_date = dt.strftime("%Y-%m-%d %H:%M")
        except:
            formatted_date = updated_at

        # ステップ名を日本語に変換
        step_names = {
            "user_input": "基本情報収集",
            "concept_generation": "コンセプト20案生成",
            "persona_definition": "ペルソナ定義",
            "pain_extraction": "脳内独り言抽出",
            "usp_future_definition": "USP & Future定義",
            "profile_creation": "プロフィール文作成",
            "final_check": "最終確認リスト",
            "idea_generation": "企画生成",
            "script_generation": "台本生成",
        }

        step_name_jp = step_names.get(step, step)

        summary = (
            f"プロジェクト: {self.project_name}\n"
            f"最終更新: {formatted_date}\n"
            f"進捗: Chapter {chapter} - {step_name_jp}"
        )

        return summary

    def list_all_projects(self) -> list:
        """
        全てのプロジェクト（アカウント）一覧を取得

        Returns:
            プロジェクト名のリスト
        """
        if not self.state_dir.exists():
            return []

        projects = []
        for state_file in self.state_dir.glob("*.json"):
            project_name = state_file.stem
            projects.append(project_name)

        return sorted(projects)
