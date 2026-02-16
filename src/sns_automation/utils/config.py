"""
設定ファイルの読み込みと管理
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# グローバル設定キャッシュ
_config_cache: Optional[Dict[str, Any]] = None


def find_config_file() -> Path:
    """
    設定ファイルを検索する

    検索順序:
    1. 環境変数 SNS_AUTOMATION_CONFIG
    2. カレントディレクトリの config.yaml
    3. ホームディレクトリの .sns-automation/config.yaml

    Returns:
        設定ファイルパス

    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
    """
    # 環境変数から
    env_config = os.environ.get("SNS_AUTOMATION_CONFIG")
    if env_config:
        config_path = Path(env_config)
        if config_path.exists():
            return config_path

    # カレントディレクトリ
    current_config = Path.cwd() / "config.yaml"
    if current_config.exists():
        return current_config

    # ホームディレクトリ
    home_config = Path.home() / ".sns-automation" / "config.yaml"
    if home_config.exists():
        return home_config

    raise FileNotFoundError(
        "設定ファイルが見つかりません。以下のいずれかに config.yaml を配置してください:\n"
        "1. 環境変数 SNS_AUTOMATION_CONFIG で指定\n"
        "2. カレントディレクトリ\n"
        "3. ~/.sns-automation/config.yaml"
    )


def load_config(config_path: Optional[Path] = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    設定ファイルを読み込む

    Args:
        config_path: 設定ファイルパス（省略時は自動検索）
        force_reload: キャッシュを無視して再読み込みするか

    Returns:
        設定辞書

    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        yaml.YAMLError: YAMLパースエラー
    """
    global _config_cache

    # キャッシュがあれば返す
    if _config_cache is not None and not force_reload:
        return _config_cache

    # Streamlit環境でconfig.yamlが無い場合はデフォルト設定を返す
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            # Streamlit環境の場合、最小限の設定で起動
            _config_cache = {
                "api_keys": {},
                "google_sheets": {
                    "credentials_path": "",
                    "default_spreadsheet_id": "",
                    "sheets": {}
                },
                "paths": {}
            }
            return _config_cache
    except ImportError:
        pass

    # 設定ファイルを検索
    if config_path is None:
        config_path = find_config_file()

    # 読み込み
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # バリデーション
    validate_config(config)

    # キャッシュに保存
    _config_cache = config

    return config


def validate_config(config: Dict[str, Any]) -> None:
    """
    設定ファイルのバリデーション

    Args:
        config: 設定辞書

    Raises:
        ValueError: 必須項目が不足している場合
    """
    # 必須項目のチェック
    required_keys = ["api_keys", "google_sheets", "paths"]

    for key in required_keys:
        if key not in config:
            raise ValueError(f"設定ファイルに {key} が定義されていません")

    # API Keyのチェック
    if "claude" not in config["api_keys"]:
        raise ValueError("Claude API Keyが設定されていません")

    # Google Sheets設定のチェック
    sheets_config = config["google_sheets"]
    if "credentials_path" not in sheets_config:
        raise ValueError("Google Sheets認証ファイルパスが設定されていません")

    if "default_spreadsheet_id" not in sheets_config:
        raise ValueError("デフォルトのスプレッドシートIDが設定されていません")


def get_config() -> Dict[str, Any]:
    """
    キャッシュされた設定を取得

    Returns:
        設定辞書

    Raises:
        RuntimeError: 設定が読み込まれていない場合
    """
    global _config_cache

    if _config_cache is None:
        # 自動的に読み込みを試みる
        try:
            load_config()
        except FileNotFoundError:
            # Streamlit環境でconfig.yamlが無い場合はデフォルト設定を返す
            _config_cache = {
                "api_keys": {},
                "google_sheets": {
                    "credentials_path": "",
                    "default_spreadsheet_id": "",
                    "sheets": {}
                },
                "paths": {}
            }

    return _config_cache


def get_api_key(service: str) -> str:
    """
    API Keyを取得

    Args:
        service: サービス名（claude, elevenlabs等）

    Returns:
        API Key

    Raises:
        ValueError: API Keyが設定されていない場合
    """
    # Streamlit環境では st.secrets から優先的に取得
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "api_keys" in st.secrets:
            api_keys = st.secrets["api_keys"]
            if service in api_keys:
                return api_keys[service]
    except (ImportError, FileNotFoundError, KeyError):
        pass  # Streamlit環境でない、またはsecretsが設定されていない

    # config.yamlから取得（ローカル環境）
    config = get_config()
    api_keys = config.get("api_keys", {})

    if service not in api_keys:
        raise ValueError(f"{service} のAPI Keyが設定されていません")

    return api_keys[service]


def get_spreadsheet_id() -> str:
    """
    デフォルトのスプレッドシートIDを取得

    Returns:
        スプレッドシートID
    """
    config = get_config()
    return config["google_sheets"]["default_spreadsheet_id"]


def get_sheet_name(sheet_type: str) -> str:
    """
    シート名を取得

    Args:
        sheet_type: シートタイプ（strategy, analysis, ideas, scripts）

    Returns:
        シート名
    """
    config = get_config()
    sheets = config["google_sheets"].get("sheets", {})
    return sheets.get(sheet_type, sheet_type)
