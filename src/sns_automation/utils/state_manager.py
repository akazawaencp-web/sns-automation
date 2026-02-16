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


def get_state_manager(project_name: str = "default"):
    """
    環境に応じた StateManager を取得

    Streamlit Cloud環境ではSheetsStateManagerを使用し、
    ローカル環境または初期化失敗時はStateManagerを使用する

    Args:
        project_name: プロジェクト名

    Returns:
        StateManager または SheetsStateManager のインスタンス
    """
    # Streamlit Cloud環境を検出
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "google_service_account" in st.secrets:
            # SheetsStateManagerを試す
            try:
                logger.info("Streamlit Cloud環境を検出、SheetsStateManagerを使用します")
                return SheetsStateManager(project_name)
            except Exception as e:
                # エラーが出てもアプリは動作し続ける（フォールバック）
                logger.warning(f"SheetsStateManager初期化失敗、StateManagerにフォールバック: {e}")
                import traceback
                logger.warning(traceback.format_exc())
    except ImportError:
        logger.info("Streamlit未検出、ローカルStateManagerを使用します")

    # ローカル環境 or SheetsStateManager失敗時
    return StateManager(project_name)


class StateManager:
    """セッション状態を管理するクラス（ローカル + Google Sheets）"""

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

        # Google Sheets クライアントを初期化（オプショナル）
        self.sheets_client = None
        self.spreadsheet = None
        self._init_sheets()

    def _init_sheets(self) -> None:
        """Google Sheets APIを初期化（失敗しても続行）"""
        try:
            import streamlit as st
            import gspread
            from google.oauth2.service_account import Credentials

            # Streamlit Secretsから認証情報を取得
            if not hasattr(st, "secrets") or "google_service_account" not in st.secrets:
                logger.info("Google Sheets認証情報が見つかりません（ローカル環境）")
                return

            service_account_info = dict(st.secrets["google_service_account"])
            spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]

            # Google Sheets APIに接続
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            credentials = Credentials.from_service_account_info(
                service_account_info, scopes=scope
            )
            self.sheets_client = gspread.authorize(credentials)
            self.spreadsheet = self.sheets_client.open_by_key(spreadsheet_id)

            logger.info("Google Sheets APIの初期化に成功しました")

        except Exception as e:
            logger.warning(f"Google Sheets APIの初期化に失敗（ローカルファイルのみ使用）: {e}")

    def save_state(
        self,
        chapter: int,
        step: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        状態を保存（ローカル + Google Sheets）

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

        # ローカルファイルに保存
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        logger.info(f"状態をローカルに保存しました: {self.state_file}")

        # Google Sheetsにも保存（失敗しても続行）
        self._save_to_sheets(state)

    def _save_to_sheets(self, state: Dict[str, Any]) -> None:
        """Google Sheetsに状態を保存（失敗してもエラーを出さない）"""
        if not self.spreadsheet:
            return

        try:
            # シートを取得または作成
            try:
                sheet = self.spreadsheet.worksheet("sns_automation_states")
            except:
                sheet = self.spreadsheet.add_worksheet(
                    title="sns_automation_states", rows=1000, cols=10
                )
                # ヘッダー行を追加
                sheet.append_row([
                    "project_name", "last_chapter", "last_step",
                    "data_json", "metadata_json", "updated_at"
                ])

            # 既存の行を探す
            all_records = sheet.get_all_records()
            row_index = None
            for i, record in enumerate(all_records):
                if record.get("project_name") == self.project_name:
                    row_index = i + 2  # ヘッダー行があるので+2
                    break

            # データをJSON文字列に変換
            data_json = json.dumps(state["data"], ensure_ascii=False)
            metadata_json = json.dumps(state["metadata"], ensure_ascii=False)

            row_data = [
                self.project_name,
                state["last_chapter"],
                state["last_step"],
                data_json,
                metadata_json,
                state["updated_at"]
            ]

            if row_index:
                # 既存の行を更新
                sheet.update(f"A{row_index}:F{row_index}", [row_data])
            else:
                # 新しい行を追加
                sheet.append_row(row_data)

            logger.info(f"状態をGoogle Sheetsに保存しました: {self.project_name}")

        except Exception as e:
            logger.warning(f"Google Sheetsへの保存に失敗（ローカルのみ）: {e}")

    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        状態を読み込む（Google Sheets → ローカルファイルの順）

        Returns:
            状態辞書（存在しない場合はNone）
        """
        # まずGoogle Sheetsから読み込みを試みる
        state = self._load_from_sheets()
        if state:
            logger.info(f"状態をGoogle Sheetsから読み込みました: {self.project_name}")
            return state

        # Google Sheetsが使えない場合はローカルファイルから読み込む
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            logger.info(f"状態をローカルファイルから読み込みました: {self.state_file}")
            return state
        except Exception as e:
            logger.error(f"状態の読み込みに失敗しました: {e}")
            return None

    def _load_from_sheets(self) -> Optional[Dict[str, Any]]:
        """Google Sheetsから状態を読み込む（失敗したらNoneを返す）"""
        if not self.spreadsheet:
            return None

        try:
            sheet = self.spreadsheet.worksheet("sns_automation_states")
            all_records = sheet.get_all_records()

            for record in all_records:
                if record.get("project_name") == self.project_name:
                    # JSONをパース
                    data = json.loads(record["data_json"])
                    metadata = json.loads(record["metadata_json"])

                    state = {
                        "project_name": self.project_name,
                        "last_chapter": record["last_chapter"],
                        "last_step": record["last_step"],
                        "data": data,
                        "metadata": metadata,
                        "updated_at": record["updated_at"],
                    }
                    return state

            return None

        except Exception as e:
            logger.warning(f"Google Sheetsからの読み込みに失敗: {e}")
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
        全てのプロジェクト（アカウント）一覧を取得（ローカル + Google Sheets）

        Returns:
            プロジェクト名のリスト
        """
        projects = set()

        # ローカルファイルから取得
        if self.state_dir.exists():
            for state_file in self.state_dir.glob("*.json"):
                projects.add(state_file.stem)

        # Google Sheetsからも取得
        if self.spreadsheet:
            try:
                sheet = self.spreadsheet.worksheet("sns_automation_states")
                all_records = sheet.get_all_records()
                for record in all_records:
                    name = record.get("project_name")
                    if name:
                        projects.add(str(name))
            except Exception as e:
                logger.warning(f"Google Sheetsからのプロジェクト一覧取得に失敗: {e}")

        return sorted(projects)


# class SheetsStateManager:
#      """
#      Google Sheetsを使った状態管理クラス（Streamlit Cloud用）
# 
#      StateManagerと同じインターフェースを提供し、
#      データをGoogle Sheetsに保存する
#      """
# 
#      def __init__(self, project_name: str = "default"):
#          """
#          初期化
# 
#          Args:
#              project_name: プロジェクト名（アカウント名など）
#          """
#          self.project_name = project_name
# 
#          try:
#              import streamlit as st
#              import gspread
#              from google.oauth2.service_account import Credentials
# 
#              # Streamlit Secretsから認証情報を取得
#              service_account_info = dict(st.secrets["google_service_account"])
#              spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
# 
#              # Google Sheets APIに接続
#              scope = [
#                  "https://www.googleapis.com/auth/spreadsheets",
#                  "https://www.googleapis.com/auth/drive",
#              ]
#              credentials = Credentials.from_service_account_info(
#                  service_account_info, scopes=scope
#              )
#              self.client = gspread.authorize(credentials)
#              self.spreadsheet = self.client.open_by_key(spreadsheet_id)
# 
#              # シートを取得または作成
#              try:
#                  self.projects_sheet = self.spreadsheet.worksheet("projects")
#              except gspread.exceptions.WorksheetNotFound:
#                  self.projects_sheet = self.spreadsheet.add_worksheet(
#                      title="projects", rows=1000, cols=10
#                  )
#                  # ヘッダー行を追加
#                  self.projects_sheet.append_row(
#                      ["project_name", "last_chapter", "last_step", "updated_at"]
#                  )
# 
#              try:
#                  self.data_sheet = self.spreadsheet.worksheet("project_data")
#              except gspread.exceptions.WorksheetNotFound:
#                  self.data_sheet = self.spreadsheet.add_worksheet(
#                      title="project_data", rows=1000, cols=5
#                  )
#                  # ヘッダー行を追加
#                  self.data_sheet.append_row(
#                      ["project_name", "data_json", "metadata_json"]
#                  )
# 
#              logger.info(f"Google Sheets StateManagerを初期化しました: {project_name}")
# 
#          except Exception as e:
#              logger.error(f"Google Sheets StateManagerの初期化に失敗: {e}")
#              raise
# 
#      def save_state(
#          self,
#          chapter: int,
#          step: str,
#          data: Dict[str, Any],
#          metadata: Optional[Dict[str, Any]] = None,
#      ) -> None:
#          """
#          状態をGoogle Sheetsに保存
# 
#          Args:
#              chapter: チャプター番号
#              step: ステップ名
#              data: 保存するデータ
#              metadata: 追加のメタデータ
#          """
#          try:
#              updated_at = datetime.now().isoformat()
# 
#              # projectsシートを更新
#              all_records = self.projects_sheet.get_all_records()
#              row_index = None
# 
#              for i, record in enumerate(all_records):
#                  if record.get("project_name") == self.project_name:
#                      row_index = i + 2  # ヘッダー行があるので+2
# 
#              if row_index:
#                  # 既存の行を更新
#                  self.projects_sheet.update(
#                      f"A{row_index}:D{row_index}",
#                      [[self.project_name, chapter, step, updated_at]],
#                  )
#              else:
#                  # 新しい行を追加
#                  self.projects_sheet.append_row(
#                      [self.project_name, chapter, step, updated_at]
#                  )
# 
#              # project_dataシートを更新
#              data_json = json.dumps(data, ensure_ascii=False)
#              metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
# 
#              all_data_records = self.data_sheet.get_all_records()
#              data_row_index = None
# 
#              for i, record in enumerate(all_data_records):
#                  if record.get("project_name") == self.project_name:
#                      data_row_index = i + 2
# 
#              if data_row_index:
#                  self.data_sheet.update(
#                      f"A{data_row_index}:C{data_row_index}",
#                      [[self.project_name, data_json, metadata_json]],
#                  )
#              else:
#                  self.data_sheet.append_row(
#                      [self.project_name, data_json, metadata_json]
#                  )
# 
#              logger.info(f"状態をGoogle Sheetsに保存しました: {self.project_name}")
# 
#          except Exception as e:
#              logger.error(f"Google Sheetsへの保存に失敗: {e}")
#              raise
# 
#      def load_state(self) -> Optional[Dict[str, Any]]:
#          """
#          Google Sheetsから状態を読み込む
# 
#          Returns:
#              状態辞書（存在しない場合はNone）
#          """
#          try:
#              # projectsシートから基本情報を取得
#              all_records = self.projects_sheet.get_all_records()
#              project_record = None
# 
#              for record in all_records:
#                  if record.get("project_name") == self.project_name:
#                      project_record = record
#                      break
# 
#              if not project_record:
#                  return None
# 
#              # project_dataシートからデータを取得
#              all_data_records = self.data_sheet.get_all_records()
#              data_record = None
# 
#              for record in all_data_records:
#                  if record.get("project_name") == self.project_name:
#                      data_record = record
#                      break
# 
#              if not data_record:
#                  return None
# 
#              # JSONをパース
#              data = json.loads(data_record["data_json"])
#              metadata = json.loads(data_record["metadata_json"])
# 
#              state = {
#                  "project_name": self.project_name,
#                  "last_chapter": project_record["last_chapter"],
#                  "last_step": project_record["last_step"],
#                  "data": data,
#                  "metadata": metadata,
#                  "updated_at": project_record["updated_at"],
#              }
# 
#              logger.info(f"状態をGoogle Sheetsから読み込みました: {self.project_name}")
#              return state
# 
#          except Exception as e:
#              logger.error(f"Google Sheetsからの読み込みに失敗: {e}")
#              return None
# 
#      def has_state(self) -> bool:
#          """
#          保存された状態が存在するかチェック
# 
#          Returns:
#              存在する場合True
#          """
#          try:
#              all_records = self.projects_sheet.get_all_records()
#              for record in all_records:
#                  if record.get("project_name") == self.project_name:
#                      return True
#              return False
#          except Exception as e:
#              logger.error(f"状態の存在チェックに失敗: {e}")
#              return False
# 
#      def delete_state(self) -> None:
#          """状態を削除"""
#          try:
#              # projectsシートから削除
#              all_records = self.projects_sheet.get_all_records()
#              for i, record in enumerate(all_records):
#                  if record.get("project_name") == self.project_name:
#                      self.projects_sheet.delete_rows(i + 2)
#                      break
# 
#              # project_dataシートから削除
#              all_data_records = self.data_sheet.get_all_records()
#              for i, record in enumerate(all_data_records):
#                  if record.get("project_name") == self.project_name:
#                      self.data_sheet.delete_rows(i + 2)
#                      break
# 
#              logger.info(f"状態をGoogle Sheetsから削除しました: {self.project_name}")
# 
#          except Exception as e:
#              logger.error(f"Google Sheetsからの削除に失敗: {e}")
# 
#      def get_summary(self) -> Optional[str]:
#          """
#          状態のサマリーを取得
# 
#          Returns:
#              サマリー文字列（存在しない場合はNone）
#          """
#          state = self.load_state()
#          if not state:
#              return None
# 
#          chapter = state.get("last_chapter")
#          step = state.get("last_step")
#          updated_at = state.get("updated_at", "")
# 
#          # 日時をフォーマット
#          try:
#              dt = datetime.fromisoformat(updated_at)
#              formatted_date = dt.strftime("%Y-%m-%d %H:%M")
#          except:
#              formatted_date = updated_at
# 
#          # ステップ名を日本語に変換
#          step_names = {
#              "user_input": "基本情報収集",
#              "concept_generation": "コンセプト20案生成",
#              "persona_definition": "ペルソナ定義",
#              "pain_extraction": "脳内独り言抽出",
#              "usp_future_definition": "USP & Future定義",
#              "profile_creation": "プロフィール文作成",
#              "final_check": "最終確認リスト",
#              "idea_generation": "企画生成",
#              "script_generation": "台本生成",
#          }
# 
#          step_name_jp = step_names.get(step, step)
# 
#          summary = (
#              f"プロジェクト: {self.project_name}\n"
#              f"最終更新: {formatted_date}\n"
#              f"進捗: Chapter {chapter} - {step_name_jp}"
#          )
# 
#          return summary
#
#     def list_all_projects(self) -> list:
#         """
#         全てのプロジェクト（アカウント）一覧を取得
#
#         Returns:
#             プロジェクト名のリスト
#         """
#         try:
#             all_records = self.projects_sheet.get_all_records()
#             projects = [record["project_name"] for record in all_records]
#             return sorted(projects)
#         except Exception as e:
#             logger.error(f"プロジェクト一覧の取得に失敗: {e}")
#             return []
