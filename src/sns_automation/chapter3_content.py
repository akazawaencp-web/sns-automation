"""
Chapter 3: コンテンツ量産の自動化

このモジュールは、コンテンツ量産プロセスを自動化します：
- 企画20本の自動生成
- 台本作成
- 音声生成（ElevenLabs）
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import click
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table

from sns_automation.utils import (
    ClaudeAPI,
    SheetsAPI,
    ElevenLabsAPI,
    load_config,
    load_prompt,
    ScriptLinter,
    StateManager,
    IdeaAnalyzer,
    ScriptPreviewer,
    error_helpers,
)
from sns_automation.utils.config import get_spreadsheet_id, get_sheet_name

logger = logging.getLogger(__name__)
console = Console()


class ContentAutomation:
    """Chapter 3: コンテンツ量産の自動化クラス"""

    def __init__(self, config: Optional[Dict[str, Any]] = None, project_name: str = "default"):
        """
        初期化

        Args:
            config: 設定辞書（省略時はStreamlit環境としてst.secretsから取得）
            project_name: プロジェクト名（アカウント名など）
        """
        self.config = config
        self.claude = ClaudeAPI(config)

        # Google Sheets API（オプショナル）
        try:
            if config is not None:
                self.sheets = SheetsAPI(config)
            else:
                self.sheets = None
                logger.info("Streamlit環境のため、Google Sheets APIは無効化されています")
        except Exception as e:
            logger.warning(f"Google Sheets APIの初期化に失敗しました: {e}")
            logger.warning("スプレッドシートへの書き込みはスキップされます")
            self.sheets = None

        # ElevenLabs API（Streamlit環境では無効化）
        if config is not None:
            self.elevenlabs = ElevenLabsAPI(config)
        else:
            self.elevenlabs = None
            logger.info("Streamlit環境のため、ElevenLabs APIは無効化されています")

        self.state_manager = StateManager(project_name)
        self.project_name = project_name

    def _load_chapter_result(self, chapter: int) -> Dict[str, Any]:
        """
        Chapter の結果ファイルを読み込む

        Args:
            chapter: チャプター番号 (1 or 2)

        Returns:
            結果辞書

        Raises:
            FileNotFoundError: 結果ファイルが見つからない場合
        """
        output_dir = Path(self.config.get("paths", {}).get("output", "./output"))
        result_path = output_dir / f"chapter{chapter}_result.json"

        if not result_path.exists():
            raise FileNotFoundError(
                f"Chapter {chapter} の結果ファイルが見つかりません: {result_path}\n"
                f"先に Chapter {chapter} を実行してください。"
            )

        with open(result_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_ideas(
        self, strategy_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        企画を自動生成（追加生成も可能）

        Args:
            strategy_data: Chapter 1の戦略データ

        Returns:
            企画リスト（累積）
        """
        console.print(Panel("Step 1: 企画の生成", style="bold cyan"))

        # Chapter 1 のデータを整形
        persona = strategy_data.get("persona", {})
        if isinstance(persona, dict):
            persona_text = persona.get("raw_text", "未設定")
        else:
            persona_text = str(persona)

        pains_list = strategy_data.get("pains", [])
        pains = "\n".join(f"{i}. {p}" for i, p in enumerate(pains_list, 1))

        all_ideas = []  # 累積企画リスト
        round_num = 1   # 生成ラウンド番号

        while True:
            # 現在のラウンドの開始番号
            start_no = (round_num - 1) * 20 + 1
            end_no = round_num * 20

            console.print(f"\n[bold yellow]企画 {start_no}-{end_no} を生成中...[/bold yellow]")

            prompt_data = load_prompt(
                chapter="chapter3",
                prompt_name="idea_generation",
                variables={
                    "persona": persona_text,
                    "pains": pains,
                },
            )

            console.print("[dim]Claude APIで企画を生成中...[/dim]")
            response = self.claude.generate_text(
                prompt=prompt_data["user"],
                system_prompt=prompt_data.get("system"),
                temperature=prompt_data.get("temperature", 0.9),
                max_tokens=prompt_data.get("max_tokens", 8000),
            )

            # レスポンスをパースして企画リストを構築
            new_ideas = self._parse_ideas(response)

            # 番号を振り直し（累積番号に変更）
            for i, idea in enumerate(new_ideas):
                idea["no"] = str(start_no + i)

            # 累積リストに追加
            all_ideas.extend(new_ideas)

            # 全ての企画を表示（累積）
            console.print(f"\n[bold green]合計 {len(all_ideas)}本の企画を生成しました:[/bold green]\n")

            table = Table(title=f"企画一覧（合計{len(all_ideas)}投稿分）", show_lines=True)
            table.add_column("No", style="bold cyan", width=4, justify="center")
            table.add_column("企画タイトル（フック）", style="yellow", width=40)
            table.add_column("狙い・内容の要約", style="green", width=50)

            for idea in all_ideas:
                table.add_row(
                    idea.get("no", ""),
                    idea.get("title", ""),
                    idea.get("summary", ""),
                )

            console.print(table)

            # 企画の傾向分析
            analyzer = IdeaAnalyzer()
            analysis = analyzer.analyze_ideas(all_ideas)
            analyzer.show_analysis_report(analysis)

            # バランスが悪い場合は作り直しを提案
            if analyzer.should_regenerate(analysis) and round_num == 1:  # 初回のみ提案
                console.print("\n[bold yellow]📊 企画の傾向が偏っています。作り直しますか？[/bold yellow]")
                console.print("  [1] この企画で進める")
                console.print("  [2] 作り直す（新しい20案を生成）")

                regenerate_choice = click.prompt("番号を入力", type=int, default=1)

                if regenerate_choice == 2:
                    console.print("\n[cyan]新しい企画を生成します...[/cyan]\n")
                    all_ideas = []  # リセット
                    continue

            # 次のアクションを確認
            console.print("\n[bold yellow]次のアクションを選んでください:[/bold yellow]")
            console.print(f"  [1] この{len(all_ideas)}案から選択する")
            console.print(f"  [2] 追加で20個生成（{end_no + 1}-{end_no + 20}を生成）")

            action = click.prompt("番号を入力", type=int, default=1)

            if action == 1:
                break
            else:
                console.print(f"\n[cyan]追加で20個の企画を生成します（{end_no + 1}-{end_no + 20}）...[/cyan]\n")
                round_num += 1
                continue

        return all_ideas

    def _parse_ideas(self, response: str) -> List[Dict[str, Any]]:
        """
        Claude APIのレスポンスから企画情報をパースする

        マークダウンテーブル形式をパース：
        | No | 企画タイトル（フック） | 狙い・内容の要約 |
        |---|---|---|
        | 1 | タイトル1 | 要約1 |

        Args:
            response: APIレスポンステキスト

        Returns:
            企画リスト
        """
        ideas: List[Dict[str, Any]] = []

        for line in response.split("\n"):
            line = line.strip()

            # 空行またはヘッダー行・区切り行をスキップ
            if not line or line.startswith("|---|") or line.startswith("| No |"):
                continue

            # テーブル行をパース（| No | タイトル | 要約 |）
            if line.startswith("|") and line.endswith("|"):
                parts = [p.strip() for p in line.split("|")[1:-1]]  # 先頭と末尾の空文字を除外

                if len(parts) >= 3:
                    try:
                        no = parts[0].strip()
                        # 番号が整数であることを確認（ヘッダー行を除外）
                        int(no)

                        title = parts[1].strip()
                        summary = parts[2].strip()

                        # 例示（（例：...）を除外）
                        if title.startswith("（例："):
                            continue

                        ideas.append({
                            "no": no,
                            "title": title,
                            "summary": summary,
                            "raw_text": line,
                        })
                    except ValueError:
                        # 番号でない行はスキップ
                        continue

        # パースで取れなかった場合、番号付きリストとしてフォールバック
        if not ideas:
            logger.warning("テーブルパースに失敗。フォールバックパースを実行します。")
            for line in response.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # "1. タイトル" または "1) タイトル" の形式をパース
                for i in range(1, 21):
                    for prefix in [f"{i}.", f"{i})"]:
                        if line.startswith(prefix):
                            title = line[len(prefix):].strip()
                            ideas.append({
                                "no": str(i),
                                "title": title,
                                "summary": "",
                                "raw_text": line,
                            })
                            break

        return ideas

    def generate_script(
        self, idea: Dict[str, Any], strategy_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        台本を生成（自動改善ループ付き）

        Args:
            idea: 企画情報
            strategy_data: Chapter 1の戦略データ

        Returns:
            台本辞書
        """
        # Chapter 1のデータを整形
        persona = strategy_data.get("persona", {})
        if isinstance(persona, dict):
            persona_text = persona.get("raw_text", "未設定")
        else:
            persona_text = str(persona)

        pains_list = strategy_data.get("pains", [])
        pains = "\n".join(f"{i}. {p}" for i, p in enumerate(pains_list, 1))

        # 企画情報を整形
        idea_title = idea.get("title", "")
        idea_summary = idea.get("summary", "")

        prompt_data = load_prompt(
            chapter="chapter3",
            prompt_name="script_generation",
            variables={
                "persona": persona_text,
                "pains": pains,
                "idea_title": idea_title,
                "idea_summary": idea_summary,
            },
        )

        linter = ScriptLinter()
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            attempt += 1

            # 台本を生成
            response = self.claude.generate_text(
                prompt=prompt_data["user"],
                system_prompt=prompt_data.get("system"),
                temperature=prompt_data.get("temperature", 0.7),
                max_tokens=prompt_data.get("max_tokens", 5000),
            )

            # ナレーション全文を抽出
            narration = self._extract_narration(response)

            # 品質チェック
            lint_result = linter.check_script(
                script_text=response,
                narration=narration,
            )

            # エラーがなければ完了
            if lint_result["error_count"] == 0:
                if attempt > 1:
                    console.print(f"  [green]✅ 自動改善完了（試行{attempt}回目）[/green]")
                break

            # 最大試行回数に達した場合は警告して終了
            if attempt >= max_attempts:
                console.print(f"  [yellow]⚠️  最大試行回数（{max_attempts}回）に達しました[/yellow]")
                console.print(f"  [yellow]   エラー: {lint_result['error_count']}件、警告: {lint_result['warning_count']}件[/yellow]")
                break

            # エラーがある場合は修正を試みる
            console.print(f"  [yellow]🔄 品質エラー検出（試行{attempt}回目）: {lint_result['error_count']}件[/yellow]")
            console.print(f"  [dim]   自動修正を試みます...[/dim]")

            # エラーメッセージを収集
            error_messages = []
            for error in lint_result["errors"][:3]:  # 最初の3件のみ
                error_messages.append(f"- [{error['context']}] {error['message']}")

            # 修正プロンプトを作成
            fix_prompt = (
                f"以下の台本に品質エラーがあります。修正してください。\n\n"
                f"【エラー内容】\n" + "\n".join(error_messages) + "\n\n"
                f"【元の台本】\n{response}\n\n"
                f"【修正後の台本】\n"
                f"※元のフォーマット（Midjourneyプロンプト、台本表、ナレーション全文）を維持してください。"
            )

            # 修正版を生成
            prompt_data["user"] = fix_prompt

        script = {
            "idea_title": idea_title,
            "full_script": response,
            "narration": narration,
            "quality_score": {
                "error_count": lint_result["error_count"],
                "warning_count": lint_result["warning_count"],
                "attempts": attempt,
            }
        }

        return script

    def _extract_narration(self, script_text: str) -> str:
        """
        台本テキストからナレーション全文を抽出する

        Args:
            script_text: 台本テキスト

        Returns:
            ナレーション全文
        """
        narration_lines: List[str] = []
        in_narration_section = False
        in_code_block = False

        for line in script_text.split("\n"):
            stripped = line.strip()

            # 「ナレーション全文」セクションの検出
            if "ナレーション全文" in stripped and stripped.startswith("#"):
                in_narration_section = True
                continue

            if in_narration_section:
                if stripped.startswith("```") and not in_code_block:
                    in_code_block = True
                    continue
                if stripped.startswith("```") and in_code_block:
                    in_code_block = False
                    in_narration_section = False
                    continue
                if in_code_block:
                    narration_lines.append(line)

        narration = "\n".join(narration_lines).strip()

        # ナレーション全文セクションが見つからない場合、テーブルからナレーション列を抽出
        if not narration:
            for line in script_text.split("\n"):
                line = line.strip()
                if line.startswith("|") and not line.startswith("|---") and not line.startswith("| 時間"):
                    parts = [p.strip() for p in line.split("|")]
                    parts = [p for p in parts if p]
                    if len(parts) >= 2:
                        narration_lines.append(parts[1])

            narration = " ".join(narration_lines).strip()

        return narration

    def generate_audio_from_script(
        self, script: Dict[str, Any], output_path: Path
    ) -> Path:
        """
        台本から音声を生成

        Args:
            script: 台本情報
            output_path: 出力パス

        Returns:
            生成された音声ファイルパス
        """
        narration = script.get("narration", "")

        if not narration:
            logger.warning(
                "ナレーションテキストが空です（企画: %s）。音声生成をスキップします。",
                script.get("idea_title", "不明"),
            )
            return output_path

        output_path = Path(output_path)
        generated = self.elevenlabs.generate_audio(
            text=narration,
            output_path=output_path,
        )

        return generated

    def write_ideas_to_sheet(self, ideas: List[Dict[str, Any]]) -> None:
        """
        企画をGoogle Sheetsに書き込む

        Args:
            ideas: 企画リスト
        """
        if self.sheets is None:
            logger.info("Google Sheets APIが利用できません。スプレッドシートへの書き込みをスキップします")
            return

        console.print("[dim]企画タイトル表をスプレッドシートに書き込み中...[/dim]")

        spreadsheet_id = get_spreadsheet_id()
        sheet_name = get_sheet_name("ideas")

        # ヘッダー行
        rows: List[List[Any]] = [
            ["#", "タイトル", "コンテンツタイプ", "対応するPain", "概要", "フック", "推定効果"]
        ]

        for i, idea in enumerate(ideas, 1):
            rows.append([
                i,
                idea.get("title", ""),
                idea.get("content_type", ""),
                idea.get("pain", ""),
                idea.get("summary", ""),
                idea.get("hook", ""),
                idea.get("expected_effect", ""),
            ])

        self.sheets.write_range(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            start_cell="A1",
            values=rows,
        )

        console.print(f"[green]企画タイトル表に{len(ideas)}本の企画を書き込みました（シート: {sheet_name}）[/green]")

    def write_scripts_to_sheet(self, scripts: List[Dict[str, Any]]) -> None:
        """
        台本をGoogle Sheetsに書き込む

        Args:
            scripts: 台本リスト
        """
        if self.sheets is None:
            logger.info("Google Sheets APIが利用できません。スプレッドシートへの書き込みをスキップします")
            return

        console.print("[dim]台本表をスプレッドシートに書き込み中...[/dim]")

        spreadsheet_id = get_spreadsheet_id()
        sheet_name = get_sheet_name("scripts")

        # ヘッダー行
        rows: List[List[Any]] = [
            ["#", "企画タイトル", "台本全文", "ナレーション"]
        ]

        for i, script in enumerate(scripts, 1):
            rows.append([
                i,
                script.get("idea_title", ""),
                script.get("full_script", ""),
                script.get("narration", ""),
            ])

        self.sheets.write_range(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            start_cell="A1",
            values=rows,
        )

        console.print(f"[green]台本表に{len(scripts)}本の台本を書き込みました（シート: {sheet_name}）[/green]")

    def run(self) -> Dict[str, Any]:
        """
        Chapter 3の全プロセスを実行

        Returns:
            生成結果
        """
        console.print(Panel(
            "[bold]Chapter 3: コンテンツ量産[/bold]\n\n"
            "企画生成 → 台本作成 → 音声生成を自動化します。",
            title="SNS Automation",
            border_style="bold blue",
        ))

        # Chapter 1 の結果を読み込む
        try:
            strategy_data = self._load_chapter_result(1)
            console.print("[green]✅ Chapter 1 の結果を読み込みました[/green]")
        except FileNotFoundError as e:
            error_helpers.show_chapter_result_not_found_error(1)
            return {}

        # Step 1: 企画20本を生成
        ideas = self.generate_ideas(strategy_data)

        if not ideas:
            console.print("[bold red]企画の生成に失敗しました。[/bold red]")
            return {}

        # 企画タイトル表に書き込み
        try:
            self.write_ideas_to_sheet(ideas)
        except Exception as e:
            console.print(f"[bold red]企画タイトル表への書き込みに失敗しました: {e}[/bold red]")
            console.print("[yellow]処理は続行します。[/yellow]")

        # Step 2: ユーザーに採用する企画を選択させる
        console.print(Panel("Step 2: 企画の選択", style="bold cyan"))
        console.print("[bold yellow]採用する企画の番号をカンマ区切りで入力してください[/bold yellow]")
        console.print(f"（例: 1,3,5,10 / 全て選択する場合は all）\n")

        while True:
            selection = click.prompt("企画番号を入力")
            selection = selection.strip()

            if selection.lower() == "all":
                selected_indices = list(range(len(ideas)))
                break

            try:
                selected_indices = []
                for part in selection.split(","):
                    idx = int(part.strip()) - 1
                    if 0 <= idx < len(ideas):
                        selected_indices.append(idx)
                    else:
                        console.print(f"[red]番号 {idx + 1} は範囲外です（1-{len(ideas)}）[/red]")
                        selected_indices = []
                        break

                if selected_indices:
                    break
            except ValueError:
                console.print("[red]数字をカンマ区切りで入力してください（例: 1,3,5）[/red]")

        selected_ideas = [ideas[i] for i in selected_indices]
        console.print(f"\n[bold green]{len(selected_ideas)}本の企画を選択しました:[/bold green]")
        for idx in selected_indices:
            console.print(f"  {idx + 1}. {ideas[idx].get('title', '(タイトルなし)')}")

        # Step 3: 選択された企画から台本を生成
        console.print(Panel("Step 3: 台本の生成", style="bold cyan"))

        scripts: List[Dict[str, Any]] = []
        linter = ScriptLinter()
        total_errors = 0
        total_warnings = 0

        with Progress() as progress:
            task = progress.add_task(
                "台本を生成中...",
                total=len(selected_ideas),
            )
            for idea in selected_ideas:
                script = self.generate_script(idea, strategy_data)

                # 品質チェック
                lint_result = linter.check_script(
                    script_text=script.get("full_script", ""),
                    narration=script.get("narration", ""),
                )

                # エラー・警告をカウント
                total_errors += lint_result["error_count"]
                total_warnings += lint_result["warning_count"]

                # エラーがある場合は表示
                if lint_result["error_count"] > 0:
                    console.print(f"\n[bold red]⚠️  台本にエラーがあります: {script.get('idea_title', '')}[/bold red]")
                    for error in lint_result["errors"]:
                        console.print(f"  ❌ [{error['context']}] {error['message']}")
                        console.print(f"     💡 {error['suggestion']}")
                elif lint_result["warning_count"] > 0:
                    console.print(f"\n[bold yellow]⚠️  台本に警告があります: {script.get('idea_title', '')}[/bold yellow]")
                    for warning in lint_result["warnings"][:2]:  # 最初の2件のみ表示
                        console.print(f"  ⚠️  [{warning['context']}] {warning['message']}")

                scripts.append(script)
                progress.update(task, advance=1)

        console.print(f"\n[bold green]{len(scripts)}本の台本を生成しました[/bold green]")
        if total_errors > 0:
            console.print(f"[bold red]品質チェック: {total_errors}件のエラー、{total_warnings}件の警告[/bold red]")
        elif total_warnings > 0:
            console.print(f"[bold yellow]品質チェック: {total_warnings}件の警告[/bold yellow]")
        else:
            console.print(f"[bold green]品質チェック: ✅ 全ての基準をクリア[/bold green]")

        # 台本のプレビューを表示
        console.print("\n" + "=" * 60)
        console.print("[bold cyan]📊 台本プレビュー（推定時間・文字数チェック）[/bold cyan]")
        console.print("=" * 60)

        previewer = ScriptPreviewer()
        for i, script in enumerate(scripts):
            console.print(f"\n[bold yellow]台本 {i+1}/{len(scripts)}:[/bold yellow]")
            preview = previewer.preview_script(script)
            previewer.show_preview(preview, script.get("idea_title", ""))

        # Step 4: 音声の生成
        console.print(Panel("Step 4: 音声の生成（ElevenLabs）", style="bold cyan"))
        output_dir = Path(self.config.get("paths", {}).get("output", "./output"))
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_paths: List[str] = []
        with Progress() as progress:
            task = progress.add_task(
                "音声を生成中...",
                total=len(scripts),
            )
            for i, script in enumerate(scripts):
                audio_filename = f"script_{i + 1:03d}.mp3"
                audio_path = audio_dir / audio_filename

                try:
                    generated_path = self.generate_audio_from_script(script, audio_path)
                    audio_paths.append(str(generated_path))
                    console.print(f"  [green]音声生成完了: {audio_filename}[/green]")
                except Exception as e:
                    logger.error("音声生成に失敗 (企画: %s): %s", script.get("idea_title", ""), e)
                    console.print(f"  [red]音声生成失敗: {audio_filename} - {e}[/red]")
                    audio_paths.append("")

                progress.update(task, advance=1)

        console.print(f"[bold green]{sum(1 for p in audio_paths if p)}本の音声を生成しました[/bold green]")

        # Step 5: 台本表に書き込み
        try:
            self.write_scripts_to_sheet(scripts)
        except Exception as e:
            console.print(f"[bold red]台本表への書き込みに失敗しました: {e}[/bold red]")
            console.print("[yellow]JSONファイルへの保存は続行します。[/yellow]")

        # Step 6: 結果をJSONファイルに保存
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "chapter3_result.json"

        result = {
            "ideas": ideas,
            "selected_indices": [i + 1 for i in selected_indices],
            "selected_ideas": selected_ideas,
            "scripts": scripts,
            "audio_paths": audio_paths,
        }

        # _rules フィールドを除去（保存時に不要）
        for idea in result["ideas"]:
            idea.pop("_rules", None)
        for idea in result["selected_ideas"]:
            idea.pop("_rules", None)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        console.print(f"\n[bold green]結果をJSONファイルに保存しました: {output_path}[/bold green]")

        # 状態を保存（中断・再開機能）
        self.state_manager.save_state(
            chapter=3,
            step="completed",
            data=result,
            metadata={
                "project_name": self.project_name,
                "total_ideas": len(ideas),
                "total_scripts": len(scripts),
            }
        )

        # 完了メッセージ
        console.print(Panel(
            "[bold green]Chapter 3: コンテンツ量産が完了しました！[/bold green]\n\n"
            f"生成企画数: {len(ideas)}本\n"
            f"選択企画数: {len(selected_ideas)}本\n"
            f"台本数: {len(scripts)}本\n"
            f"音声ファイル数: {sum(1 for p in audio_paths if p)}本\n"
            f"\n保存先: {output_path}\n"
            f"[dim]プロジェクト: {self.project_name}[/dim]",
            title="完了",
            border_style="bold green",
        ))

        return result


def main():
    """メイン関数"""
    config = load_config()
    automation = ContentAutomation(config)
    result = automation.run()
    return result


if __name__ == "__main__":
    main()
