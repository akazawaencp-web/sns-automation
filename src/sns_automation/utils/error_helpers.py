"""
エラーメッセージヘルパー

ユーザーフレンドリーなエラーメッセージと解決方法を提供
"""

from rich.console import Console
from rich.panel import Panel

console = Console()


def show_config_not_found_error():
    """config.yamlが見つからない場合のエラーメッセージ"""
    console.print(Panel(
        "[bold red]❌ エラー: config.yaml が見つかりません[/bold red]\n\n"
        "[bold yellow]💡 解決方法:[/bold yellow]\n"
        "1. 以下のコマンドを実行してconfig.yamlを作成してください:\n"
        "   [cyan]sns-automation init[/cyan]\n\n"
        "2. config.yamlを編集してAPI Keyを設定してください:\n"
        "   - Claude API Key: [dim]Anthropic Consoleから取得[/dim]\n"
        "   - ElevenLabs API Key: [dim]ElevenLabs Dashboardから取得[/dim]\n\n"
        "3. Google Sheets APIの認証情報を配置してください:\n"
        "   - Service Accountキーを [dim]credentials/[/dim] に配置",
        title="設定エラー",
        border_style="red",
    ))


def show_api_key_missing_error(service: str):
    """API Keyが設定されていない場合のエラーメッセージ"""
    console.print(Panel(
        f"[bold red]❌ エラー: {service} API Key が設定されていません[/bold red]\n\n"
        "[bold yellow]💡 解決方法:[/bold yellow]\n"
        "1. config.yamlを開いてください\n\n"
        "2. 以下のセクションにAPI Keyを設定してください:\n"
        f"   [cyan]api_keys:\n"
        f"     {service.lower()}: YOUR_API_KEY_HERE[/cyan]\n\n"
        "3. API Keyの取得方法:\n"
        f"   - Claude API: https://console.anthropic.com/\n"
        f"   - ElevenLabs API: https://elevenlabs.io/app/speech-synthesis",
        title="API Key エラー",
        border_style="red",
    ))


def show_chapter_result_not_found_error(chapter: int):
    """Chapterの結果ファイルが見つからない場合のエラーメッセージ"""
    console.print(Panel(
        f"[bold red]❌ エラー: Chapter {chapter} の結果が見つかりません[/bold red]\n\n"
        "[bold yellow]💡 解決方法:[/bold yellow]\n"
        f"先に Chapter {chapter} を実行してください:\n\n"
        f"{'1. 戦略設計を実行:' if chapter == 1 else '1. コンテンツ生成を実行:'}\n"
        f"   [cyan]{'sns-automation strategy create' if chapter == 1 else 'sns-automation content generate'}[/cyan]\n\n"
        "2. 実行が完了すると、結果ファイルが自動的に保存されます:\n"
        f"   [dim]output/chapter{chapter}_result.json[/dim]",
        title=f"Chapter {chapter} エラー",
        border_style="red",
    ))


def show_file_not_found_error(file_path: str, suggestion: str = ""):
    """ファイルが見つからない場合のエラーメッセージ"""
    message = (
        f"[bold red]❌ エラー: ファイルが見つかりません[/bold red]\n\n"
        f"[bold]ファイルパス:[/bold] {file_path}\n\n"
    )

    if suggestion:
        message += f"[bold yellow]💡 解決方法:[/bold yellow]\n{suggestion}"
    else:
        message += (
            "[bold yellow]💡 解決方法:[/bold yellow]\n"
            "1. ファイルパスが正しいか確認してください\n"
            "2. ファイルが存在するか確認してください"
        )

    console.print(Panel(
        message,
        title="ファイルエラー",
        border_style="red",
    ))


def show_invalid_input_error(expected: str, got: str = ""):
    """入力が不正な場合のエラーメッセージ"""
    message = f"[bold red]❌ エラー: 入力が不正です[/bold red]\n\n"

    if got:
        message += f"[bold]期待される入力:[/bold] {expected}\n"
        message += f"[bold]実際の入力:[/bold] {got}\n\n"
    else:
        message += f"[bold]期待される入力:[/bold] {expected}\n\n"

    message += (
        "[bold yellow]💡 解決方法:[/bold yellow]\n"
        "正しい形式で入力し直してください"
    )

    console.print(Panel(
        message,
        title="入力エラー",
        border_style="red",
    ))


def show_api_error(service: str, error_message: str):
    """API呼び出しエラーのメッセージ"""
    console.print(Panel(
        f"[bold red]❌ エラー: {service} API の呼び出しに失敗しました[/bold red]\n\n"
        f"[bold]エラー詳細:[/bold]\n{error_message}\n\n"
        "[bold yellow]💡 解決方法:[/bold yellow]\n"
        "1. インターネット接続を確認してください\n"
        "2. API Keyが正しく設定されているか確認してください\n"
        "3. API Keyの有効期限が切れていないか確認してください\n"
        "4. API利用枠が残っているか確認してください",
        title=f"{service} APIエラー",
        border_style="red",
    ))


def show_success_message(title: str, message: str):
    """成功メッセージ"""
    console.print(Panel(
        f"[bold green]✅ {message}[/bold green]",
        title=title,
        border_style="green",
    ))


def show_warning_message(title: str, message: str):
    """警告メッセージ"""
    console.print(Panel(
        f"[bold yellow]⚠️  {message}[/bold yellow]",
        title=title,
        border_style="yellow",
    ))
