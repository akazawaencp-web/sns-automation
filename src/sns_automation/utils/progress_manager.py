"""
コンテンツ進捗管理モジュール

StateManagerとは独立したデータストアで、
Midjourney〜改善アクションまでの手動ステップとKPIを追跡する。
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProgressManager:
    """コンテンツ進捗管理（StateManagerとは独立）"""

    MANUAL_STEPS = [
        "midjourney",
        "kling_ai",
        "eleven_labo",
        "vrew",
        "capcut",
        "posted",
        "improvement",
    ]

    STEP_LABELS = {
        "midjourney": "Midjourney モデル画像",
        "kling_ai": "Kling AI 動画素材",
        "eleven_labo": "ELEVEN LABO ナレーション",
        "vrew": "Vrew キャプション",
        "capcut": "CapCut 動画編集",
        "posted": "投稿",
        "improvement": "改善アクション",
    }

    # 全11ステップのラベル（自動+手動）
    ALL_STEP_LABELS = {
        "strategy": "戦略設計",
        "ideas": "企画生成",
        "script": "台本生成",
        **STEP_LABELS,
    }

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.progress_dir = Path.home() / ".sns-automation" / "progress"
        self.progress_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.progress_dir / f"{project_name}.json"

        self.spreadsheet = None
        self._init_sheets()

    def _init_sheets(self) -> None:
        """Google Sheets APIを初期化（失敗しても続行）"""
        try:
            import streamlit as st
            import gspread
            from google.oauth2.service_account import Credentials

            if not hasattr(st, "secrets") or "google_service_account" not in st.secrets:
                return

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
            self.spreadsheet = client.open_by_key(spreadsheet_id)
        except Exception as e:
            logger.warning(f"ProgressManager: Google Sheets初期化失敗: {e}")

    def _empty_content(self) -> dict:
        """空のコンテンツ進捗データを生成"""
        return {
            "steps": {
                step: {"done": False, "updated_at": None, "updated_by": None}
                for step in self.MANUAL_STEPS
            },
            "kpi_records": [],
        }

    def load_progress(self) -> dict:
        """
        進捗データを読み込む（Sheets → ローカル フォールバック）

        Returns:
            進捗データ辞書
        """
        # Google Sheetsから試行
        data = self._load_from_sheets()
        if data is not None:
            return data

        # ローカルファイルから読み込み
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"ローカル進捗データの読み込みに失敗: {e}")

        # 新規データを返す
        return {
            "project_name": self.project_name,
            "updated_at": None,
            "contents": {},
        }

    def _load_from_sheets(self) -> Optional[dict]:
        """Google Sheetsから進捗データを読み込む"""
        if not self.spreadsheet:
            return None
        try:
            sheet = self.spreadsheet.worksheet("content_progress")
            all_records = sheet.get_all_records()
            for record in all_records:
                if record.get("project_name") == self.project_name:
                    contents = json.loads(record.get("progress_json", "{}") or "{}")
                    return {
                        "project_name": self.project_name,
                        "updated_at": record.get("updated_at", ""),
                        "contents": contents,
                    }
        except Exception as e:
            logger.warning(f"Google Sheetsからの進捗読み込みに失敗: {e}")
        return None

    def save_progress(self, data: dict) -> None:
        """
        進捗データを保存（ローカル + Sheets 両方）

        Args:
            data: 進捗データ辞書
        """
        data["updated_at"] = datetime.now().isoformat()

        # ローカルに保存
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ローカル進捗データの保存に失敗: {e}")

        # Google Sheetsに保存
        self._save_to_sheets(data)

    def _save_to_sheets(self, data: dict) -> None:
        """Google Sheetsに進捗データを保存"""
        if not self.spreadsheet:
            return
        try:
            try:
                sheet = self.spreadsheet.worksheet("content_progress")
            except Exception:
                sheet = self.spreadsheet.add_worksheet(
                    title="content_progress", rows=200, cols=3
                )
                sheet.append_row(["project_name", "progress_json", "updated_at"])

            progress_json = json.dumps(data.get("contents", {}), ensure_ascii=False)

            # 既存行を探す
            all_records = sheet.get_all_records()
            row_index = None
            for i, record in enumerate(all_records):
                if record.get("project_name") == self.project_name:
                    row_index = i + 2
                    break

            row_data = [self.project_name, progress_json, data.get("updated_at", "")]

            if row_index:
                sheet.update(f"A{row_index}:C{row_index}", [row_data])
            else:
                sheet.append_row(row_data)

            logger.info(f"進捗データをGoogle Sheetsに保存: {self.project_name}")
        except Exception as e:
            logger.warning(f"Google Sheetsへの進捗保存に失敗: {e}")

    def update_step(
        self, content_idx: str, step_key: str, done: bool, updated_by: str
    ) -> None:
        """
        手動ステップの完了状態を更新

        Args:
            content_idx: コンテンツインデックス（文字列）
            step_key: ステップキー（MANUAL_STEPSのいずれか）
            done: 完了状態
            updated_by: 更新者名
        """
        data = self.load_progress()
        contents = data.setdefault("contents", {})

        if content_idx not in contents:
            contents[content_idx] = self._empty_content()

        contents[content_idx]["steps"][step_key] = {
            "done": done,
            "updated_at": datetime.now().isoformat() if done else None,
            "updated_by": updated_by if done else None,
        }

        self.save_progress(data)

    def add_kpi_record(
        self, content_idx: str, kpi: dict, recorded_by: str
    ) -> None:
        """
        KPIレコードを追加

        Args:
            content_idx: コンテンツインデックス（文字列）
            kpi: KPIデータ（views, likes, comments, saves, shares）
            recorded_by: 記録者名
        """
        data = self.load_progress()
        contents = data.setdefault("contents", {})

        if content_idx not in contents:
            contents[content_idx] = self._empty_content()

        record = {
            "recorded_at": datetime.now().isoformat(),
            "recorded_by": recorded_by,
            **kpi,
        }
        contents[content_idx]["kpi_records"].append(record)

        self.save_progress(data)

    def get_content_progress(self, content_idx: str) -> dict:
        """特定コンテンツの進捗データを取得"""
        data = self.load_progress()
        return data.get("contents", {}).get(content_idx, self._empty_content())

    @staticmethod
    def detect_auto_steps(project_state: dict) -> dict:
        """
        StateManagerデータからステップ1-3の完了を自動判定

        Args:
            project_state: StateManager.load_state()の結果

        Returns:
            {
                "strategy_done": bool,
                "ideas_done": bool,
                "ideas_count": int,
                "scripts": {content_idx_str: bool},  # 各コンテンツの台本有無
                "ideas": list,   # 企画リスト
                "scripts_list": list,  # 台本リスト
            }
        """
        if not project_state:
            return {
                "strategy_done": False,
                "ideas_done": False,
                "ideas_count": 0,
                "scripts": {},
                "ideas": [],
                "scripts_list": [],
            }

        last_chapter = project_state.get("last_chapter", 0)
        data = project_state.get("data", {})

        strategy_done = last_chapter >= 1
        ideas = data.get("ideas", [])
        ideas_done = len(ideas) > 0
        scripts_list = data.get("scripts", [])

        # 各コンテンツ（企画）に対応する台本の有無をチェック
        scripts_by_idx = {}
        for script in scripts_list:
            idx = script.get("idea_index")
            if idx is not None:
                scripts_by_idx[str(idx)] = True

        return {
            "strategy_done": strategy_done,
            "ideas_done": ideas_done,
            "ideas_count": len(ideas),
            "scripts": scripts_by_idx,
            "ideas": ideas,
            "scripts_list": scripts_list,
        }
