"""
SNS Automation CLI

コマンドラインインターフェース
"""

import click
from pathlib import Path


@click.group()
@click.version_option(version="0.1.0")
def main():
    """SNS Automation - SNSアカウント構築・運用マニュアル自動化システム"""
    pass


@main.command()
def init():
    """設定ファイルを初期化"""
    import shutil

    config_example = Path("config.yaml.example")
    config_target = Path("config.yaml")

    if not config_example.exists():
        # パッケージディレクトリから探す
        package_dir = Path(__file__).parent.parent.parent
        config_example = package_dir / "config.yaml.example"

    if not config_example.exists():
        click.echo("config.yaml.example が見つかりません", err=True)
        raise click.Abort()

    if config_target.exists():
        if not click.confirm(f"{config_target} は既に存在します。上書きしますか？"):
            click.echo("キャンセルしました")
            return

    shutil.copy(config_example, config_target)
    click.echo(f"設定ファイルを作成しました: {config_target}")
    click.echo("\n次のステップ:")
    click.echo("1. config.yaml を編集してAPI Keyを設定してください")
    click.echo("2. Google Sheets API の認証情報を配置してください")


@main.group()
def strategy():
    """Chapter 1: 戦略設計"""
    pass


@strategy.command()
@click.option("--project", "-p", default="default", help="プロジェクト名（アカウント名など）")
def create(project: str):
    """戦略設計プロセスを実行"""
    from sns_automation.chapter1_strategy import StrategyAutomation
    from sns_automation.utils import load_config
    try:
        config = load_config()
        automation = StrategyAutomation(config, project_name=project)
        result = automation.run()
        click.echo(f"Chapter 1: 戦略設計が完了しました（プロジェクト: {project}）")
    except Exception as e:
        click.echo(f"エラー: {e}", err=True)
        raise click.Abort()


@main.command()
@click.argument("video_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def analyze(video_dir: str):
    """
    Chapter 2: 競合分析

    VIDEO_DIR: 動画ファイルが格納されたディレクトリ
    """
    from sns_automation.chapter2_analysis import main as analyze_main
    try:
        result = analyze_main(video_dir)
        click.echo("Chapter 2: 競合分析が完了しました")
    except Exception as e:
        click.echo(f"エラー: {e}", err=True)
        raise click.Abort()


@main.group()
def content():
    """Chapter 3: コンテンツ量産"""
    pass


@content.command()
@click.option("--project", "-p", default="default", help="プロジェクト名（アカウント名など）")
def generate(project: str):
    """コンテンツを生成"""
    from sns_automation.chapter3_content import ContentAutomation
    from sns_automation.utils import load_config
    try:
        config = load_config()
        automation = ContentAutomation(config, project_name=project)
        result = automation.run()
        click.echo(f"Chapter 3: コンテンツ量産が完了しました（プロジェクト: {project}）")
    except Exception as e:
        click.echo(f"エラー: {e}", err=True)
        raise click.Abort()


@content.command()
@click.argument("result_file", type=click.Path(exists=True), default="output/chapter3_result.json")
def lint(result_file: str):
    """
    台本の品質をチェック

    RESULT_FILE: chapter3_result.jsonのパス（デフォルト: output/chapter3_result.json）
    """
    from sns_automation.utils import lint_script_file, ScriptLinter
    from pathlib import Path
    import json

    try:
        result_path = Path(result_file)

        # JSONファイルを読み込み
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        linter = ScriptLinter()
        total_errors = 0
        total_warnings = 0

        click.echo("\n" + "=" * 60)
        click.echo("🔍 台本品質チェック")
        click.echo("=" * 60 + "\n")

        for i, script in enumerate(data.get("scripts", []), 1):
            result = linter.check_script(
                script_text=script.get("full_script", ""),
                narration=script.get("narration", ""),
            )

            click.echo(f"{i}. {script.get('idea_title', '(タイトルなし)')}")

            if result["error_count"] > 0:
                click.echo(f"   ❌ エラー: {result['error_count']}件")
                for error in result["errors"]:
                    click.echo(f"      - [{error['context']}] {error['message']}")
            elif result["warning_count"] > 0:
                click.echo(f"   ⚠️  警告: {result['warning_count']}件")
            else:
                click.echo(f"   ✅ 合格")

            total_errors += result["error_count"]
            total_warnings += result["warning_count"]
            click.echo("")

        # 総合結果
        click.echo("=" * 60)
        if total_errors > 0:
            click.echo(f"❌ 総合結果: {total_errors}件のエラー、{total_warnings}件の警告")
            click.echo("=" * 60)
            raise click.Abort()
        elif total_warnings > 0:
            click.echo(f"⚠️  総合結果: {total_warnings}件の警告")
        else:
            click.echo("✅ 総合結果: 全ての品質基準をクリアしました！")
        click.echo("=" * 60)

    except FileNotFoundError:
        click.echo(f"ファイルが見つかりません: {result_file}", err=True)
        click.echo("先に 'sns-automation content generate' を実行してください")
        raise click.Abort()
    except Exception as e:
        click.echo(f"エラー: {e}", err=True)
        raise click.Abort()


@main.group()
def config():
    """設定管理"""
    pass


@config.command("init")
def init_config():
    """設定ファイルを初期化"""
    import shutil

    config_example = Path("config.yaml.example")
    config_target = Path("config.yaml")

    if not config_example.exists():
        # パッケージディレクトリから探す
        package_dir = Path(__file__).parent.parent.parent
        config_example = package_dir / "config.yaml.example"

    if not config_example.exists():
        click.echo("config.yaml.example が見つかりません", err=True)
        raise click.Abort()

    if config_target.exists():
        if not click.confirm(f"{config_target} は既に存在します。上書きしますか？"):
            click.echo("キャンセルしました")
            return

    shutil.copy(config_example, config_target)
    click.echo(f"設定ファイルを作成しました: {config_target}")
    click.echo("\n次のステップ:")
    click.echo("1. config.yaml を編集してAPI Keyを設定してください")
    click.echo("2. Google Sheets API の認証情報を配置してください")


@config.command()
def show():
    """現在の設定を表示"""
    from sns_automation.utils import load_config
    try:
        config = load_config()
        # API Keyを隠して表示
        safe_config = config.copy()
        if "api_keys" in safe_config:
            for key in safe_config["api_keys"]:
                if safe_config["api_keys"][key]:
                    safe_config["api_keys"][key] = "***" + safe_config["api_keys"][key][-4:]

        import json
        click.echo(json.dumps(safe_config, indent=2, ensure_ascii=False))
    except FileNotFoundError as e:
        click.echo(f"設定ファイルが見つかりません: {e}", err=True)
        click.echo("まず 'sns-automation config init' を実行してください")


@main.command()
@click.option("--port", "-p", default=8501, help="ポート番号（デフォルト: 8501）")
def web(port: int):
    """Web UIを起動"""
    import subprocess
    import sys
    from pathlib import Path

    # Streamlitアプリのパス
    app_path = Path(__file__).parent / "web" / "app.py"

    if not app_path.exists():
        click.echo(f"Web UIが見つかりません: {app_path}", err=True)
        raise click.Abort()

    click.echo(f"🚀 Web UIを起動中... (http://localhost:{port})")
    click.echo("Ctrl+C で終了します\n")

    try:
        # Streamlitを起動
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app_path),
                "--server.port",
                str(port),
                "--server.headless",
                "true",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        click.echo("\nWeb UIを終了しました")
    except subprocess.CalledProcessError as e:
        click.echo(f"エラー: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
