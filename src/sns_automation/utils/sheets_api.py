"""
Google Sheets API wrapper
"""

import logging
from typing import List, Dict, Any, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetsAPI:
    """Google Sheets APIのラッパークラス"""

    def __init__(self, config: Dict[str, Any]):
        """
        初期化

        Args:
            config: 設定辞書
        """
        sheets_config = config.get("google_sheets", {})
        credentials_path = sheets_config.get("credentials_path")
        if not credentials_path:
            raise ValueError("google_sheets.credentials_path が設定されていません")

        self._service: Optional[Resource] = None
        self.authenticate(credentials_path)

    def authenticate(self, credentials_path: str) -> None:
        """
        Service Account認証を実行

        Args:
            credentials_path: Service Account JSONファイルパス

        Raises:
            FileNotFoundError: 認証ファイルが存在しない場合
            ValueError: 認証に失敗した場合
        """
        try:
            credentials = Credentials.from_service_account_file(
                credentials_path, scopes=SCOPES
            )
            self._service = build("sheets", "v4", credentials=credentials)
            logger.info("Google Sheets API認証に成功しました")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"認証ファイルが見つかりません: {credentials_path}"
            )
        except Exception as e:
            raise ValueError(f"Google Sheets API認証に失敗しました: {e}")

    @property
    def service(self) -> Resource:
        """認証済みサービスを返す"""
        if self._service is None:
            raise RuntimeError("認証が完了していません。authenticate()を実行してください")
        return self._service

    def get_sheet(self, spreadsheet_id: str, sheet_name: str) -> Any:
        """
        シートのメタデータを取得

        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名

        Returns:
            シートのプロパティ情報

        Raises:
            ValueError: 指定されたシートが見つからない場合
            HttpError: API呼び出しに失敗した場合
        """
        spreadsheet = (
            self.service.spreadsheets()
            .get(spreadsheetId=spreadsheet_id)
            .execute()
        )

        for sheet in spreadsheet.get("sheets", []):
            properties = sheet.get("properties", {})
            if properties.get("title") == sheet_name:
                return sheet

        raise ValueError(
            f"シート '{sheet_name}' がスプレッドシート '{spreadsheet_id}' に見つかりません"
        )

    def write_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_index: int,
        values: List[Any],
    ) -> None:
        """
        指定した行にデータを書き込む

        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            row_index: 行インデックス（1始まり）
            values: 値のリスト
        """
        range_notation = f"{sheet_name}!A{row_index}"
        body = {"values": [values]}

        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()

        logger.info(
            "行 %d に %d 個の値を書き込みました (sheet=%s)",
            row_index,
            len(values),
            sheet_name,
        )

    def write_range(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        start_cell: str,
        values: List[List[Any]],
    ) -> None:
        """
        指定範囲にデータを書き込む

        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            start_cell: 開始セル（例: "A1"）
            values: 2次元配列の値
        """
        range_notation = f"{sheet_name}!{start_cell}"
        body = {"values": values}

        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()

        logger.info(
            "範囲 %s に %d 行を書き込みました (sheet=%s)",
            start_cell,
            len(values),
            sheet_name,
        )

    def append_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        rows: List[List[Any]],
    ) -> None:
        """
        シート末尾に行を追加

        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            rows: 追加する行のリスト（2次元配列）
        """
        range_notation = f"{sheet_name}!A1"
        body = {"values": rows}

        self.service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()

        logger.info(
            "%d 行を追加しました (sheet=%s)",
            len(rows),
            sheet_name,
        )

    def read_range(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        range_notation: str,
    ) -> List[List[Any]]:
        """
        指定範囲のデータを読み込む

        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            range_notation: 範囲（例: "A1:C10"）

        Returns:
            2次元配列のデータ（データがない場合は空リスト）
        """
        full_range = f"{sheet_name}!{range_notation}"

        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=full_range)
            .execute()
        )

        values = result.get("values", [])
        logger.info(
            "範囲 %s から %d 行を読み込みました (sheet=%s)",
            range_notation,
            len(values),
            sheet_name,
        )
        return values

    def batch_update(
        self,
        spreadsheet_id: str,
        data: List[Dict[str, Any]],
    ) -> None:
        """
        複数範囲を一括更新する（バッチ更新）

        Args:
            spreadsheet_id: スプレッドシートID
            data: 更新データのリスト。各要素は {"range": "Sheet1!A1:B2", "values": [[...]]} 形式
        """
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": data,
        }

        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body,
        ).execute()

        logger.info(
            "%d 個の範囲をバッチ更新しました",
            len(data),
        )
