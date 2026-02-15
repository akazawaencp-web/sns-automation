"""
Chapter 1: 戦略設計の自動化

このモジュールは、SNS戦略設計プロセスを自動化します：
- 勝ち筋コンセプトの生成
- ペルソナの詳細化
- 脳内独り言（Pain）の抽出
- USPとFutureの定義
- プロフィール文の作成
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sns_automation.utils import ClaudeAPI, SheetsAPI, load_config, load_prompt, StateManager
from sns_automation.utils.config import get_spreadsheet_id, get_sheet_name

logger = logging.getLogger(__name__)
console = Console()


class StrategyAutomation:
    """Chapter 1: 戦略設計の自動化クラス"""

    def __init__(self, config: Dict[str, Any], project_name: str = "default"):
        """
        初期化

        Args:
            config: 設定辞書
            project_name: プロジェクト名（アカウント名など）
        """
        self.config = config
        self.claude = ClaudeAPI(config)
        self.sheets = SheetsAPI(config)
        self.state_manager = StateManager(project_name)
        self.project_name = project_name

    def collect_user_input(self) -> Dict[str, str]:
        """
        ユーザーから基本情報を収集する

        Returns:
            ユーザー入力辞書
        """
        console.print(Panel("Step 1: 基本情報の入力", style="bold cyan"))

        # 役割・肩書き（オプション）
        console.print("[dim]※役割・肩書きは任意です。空欄の場合はEnterを押してください。[/dim]")
        role = click.prompt(
            "あなたの役割・肩書き（例: キャリアアドバイザー）",
            default="",
            show_default=False,
        )

        # サービス・商品（固定値）
        service = "転職支援"
        console.print(f"\n提供するサービス・商品: [bold cyan]{service}[/bold cyan] [dim]（固定）[/dim]")

        # ターゲット層（必須）
        console.print("")
        target = click.prompt(
            "初期ターゲット層を教えてください（例: 30代の営業職、20代のエンジニア）"
        )

        user_input = {
            "role": role.strip() if role else "",
            "service": service,
            "target": target,
        }

        console.print("\n[bold green]入力内容:[/bold green]")
        table = Table(show_header=False)
        table.add_column("項目", style="bold")
        table.add_column("内容")
        if role.strip():
            table.add_row("役割・肩書き", role)
        else:
            table.add_row("役割・肩書き", "[dim]（未設定）[/dim]")
        table.add_row("サービス・商品", service)
        table.add_row("ターゲット層", target)
        console.print(table)

        return user_input

    def generate_concepts(self, user_input: Dict[str, str]) -> List[str]:
        """
        勝ち筋コンセプト20案を生成

        Args:
            user_input: ユーザー入力

        Returns:
            コンセプトリスト
        """
        console.print(Panel("Step 2: 勝ち筋コンセプト20案の生成", style="bold cyan"))

        prompt_data = load_prompt(
            chapter="chapter1",
            prompt_name="concept_ideas",
            variables=user_input,
        )

        console.print("[dim]Claude APIでコンセプトを生成中...[/dim]")
        response = self.claude.generate_text(
            prompt=prompt_data["user"],
            system_prompt=prompt_data.get("system"),
            temperature=prompt_data.get("temperature", 0.9),
            max_tokens=prompt_data.get("max_tokens", 3000),
        )

        # レスポンスを行ごとに分割してコンセプトを抽出
        # 対応フォーマット: "案1：...", "1. ...", "1) ..."
        concepts = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # マニュアル形式「案1：」「案2：」をチェック
            for i in range(1, 21):
                if line.startswith(f"案{i}：") or line.startswith(f"案{i}:"):
                    # コロンの後ろを取得
                    if "：" in line:
                        concept = line.split("：", 1)[1].strip()
                    else:
                        concept = line.split(":", 1)[1].strip()
                    concepts.append(concept)
                    break

            # 一般的な番号付きリスト「1. 」「1) 」もサポート
            if len(concepts) < 21:  # まだ見つかっていない場合
                for i in range(1, 21):
                    prefixes = [f"{i}.", f"{i})"]
                    for prefix in prefixes:
                        if line.startswith(prefix):
                            concept = line[len(prefix):].strip()
                            if concept and concept not in concepts:
                                concepts.append(concept)
                            break

        # それでも足りなければ、応答全体から非空行を取得
        if len(concepts) == 0:
            concepts = [line.strip() for line in response.strip().split("\n") if line.strip()]

        console.print(f"\n[bold green]{len(concepts)}個のコンセプトを生成しました:[/bold green]\n")
        for i, concept in enumerate(concepts, 1):
            console.print(f"  {i}. {concept}")

        return concepts

    def define_persona(self, concept: str, user_input: Dict[str, str]) -> Dict[str, Any]:
        """
        ペルソナ10項目を定義

        Args:
            concept: 選択されたコンセプト
            user_input: ユーザー入力

        Returns:
            ペルソナ辞書
        """
        console.print(Panel("Step 3: ペルソナの定義", style="bold cyan"))

        prompt_data = load_prompt(
            chapter="chapter1",
            prompt_name="persona_definition",
            variables={
                "concept": concept,
                **user_input,
            },
        )

        console.print("[dim]Claude APIでペルソナを生成中...[/dim]")
        response = self.claude.generate_text(
            prompt=prompt_data["user"],
            system_prompt=prompt_data.get("system"),
            temperature=prompt_data.get("temperature", 0.7),
            max_tokens=prompt_data.get("max_tokens", 4000),
        )

        persona = {
            "concept": concept,
            "raw_text": response,
        }

        console.print(f"\n[bold green]ペルソナを生成しました:[/bold green]\n")
        console.print(response)

        return persona

    def extract_pains(self, persona: Dict[str, Any]) -> List[str]:
        """
        脳内独り言（Pain）20個を抽出

        Args:
            persona: ペルソナ情報

        Returns:
            Painリスト
        """
        console.print(Panel("Step 4: 脳内独り言（Pain）の抽出", style="bold cyan"))

        prompt_data = load_prompt(
            chapter="chapter1",
            prompt_name="pain_extraction",
            variables={
                "persona": persona["raw_text"],
                "concept": persona["concept"],
            },
        )

        console.print("[dim]Claude APIでPainを抽出中...[/dim]")
        response = self.claude.generate_text(
            prompt=prompt_data["user"],
            system_prompt=prompt_data.get("system"),
            temperature=prompt_data.get("temperature", 0.8),
            max_tokens=prompt_data.get("max_tokens", 3000),
        )

        # レスポンスからPainを抽出
        pains = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            for i in range(1, 21):
                for prefix in [f"{i}. ", f"{i}) "]:
                    if line.startswith(prefix):
                        pain = line[len(prefix):].strip()
                        pains.append(pain)
                        break

        if len(pains) == 0:
            pains = [line.strip() for line in response.strip().split("\n") if line.strip()]

        console.print(f"\n[bold green]{len(pains)}個のPainを抽出しました:[/bold green]\n")
        for i, pain in enumerate(pains, 1):
            console.print(f"  {i}. {pain}")

        return pains

    def define_usp_future(
        self, persona: Dict[str, Any], pains: List[str]
    ) -> Dict[str, str]:
        """
        ターゲットの常識を破壊する & 最高の感情を引き出す

        Args:
            persona: ペルソナ情報
            pains: Painリスト

        Returns:
            USPとFutureの辞書
        """
        console.print(Panel("Step 5: ターゲットの常識を破壊する & 最高の感情を引き出す", style="bold cyan"))

        pains_text = "\n".join(f"{i}. {p}" for i, p in enumerate(pains, 1))

        prompt_data = load_prompt(
            chapter="chapter1",
            prompt_name="usp_future",
            variables={
                "persona": persona["raw_text"],
                "pains": pains_text,
                "concept": persona["concept"],
            },
        )

        console.print("[dim]Claude APIでUSPとFutureを生成中...[/dim]")
        response = self.claude.generate_text(
            prompt=prompt_data["user"],
            system_prompt=prompt_data.get("system"),
            temperature=prompt_data.get("temperature", 0.7),
            max_tokens=prompt_data.get("max_tokens", 3000),
        )

        usp_future = {
            "raw_text": response,
            "concept": persona["concept"],
        }

        console.print(f"\n[bold green]常識の破壊と感情的解放を生成しました:[/bold green]\n")
        console.print(response)

        return usp_future

    def create_profiles(
        self, persona: Dict[str, Any], usp_future: Dict[str, str], pains: List[str]
    ) -> List[str]:
        """
        プロフィール文3案を作成

        Args:
            persona: ペルソナ情報
            usp_future: USPとFuture
            pains: Painリスト（20個）

        Returns:
            プロフィール文リスト
        """
        console.print(Panel("Step 6: プロフィール文の作成", style="bold cyan"))

        # 20個の独り言から3つを選択
        console.print("\n[bold yellow]20個の独り言から、プロフィール文に使用する「最も心が痛む独り言」ベスト3を選択してください:[/bold yellow]\n")
        for i, pain in enumerate(pains, 1):
            console.print(f"{i:2d}. {pain}")

        console.print("\n[dim]※番号を3つ選択してください（カンマ区切り、例: 1,5,12）[/dim]")
        while True:
            selected_indices = click.prompt("番号を入力", type=str)
            try:
                indices = [int(i.strip()) for i in selected_indices.split(",")]
                if len(indices) != 3:
                    console.print("[red]ちょうど3つ選択してください。[/red]")
                    continue
                if any(i < 1 or i > len(pains) for i in indices):
                    console.print(f"[red]1〜{len(pains)}の範囲で選択してください。[/red]")
                    continue
                selected_pains = [pains[i-1] for i in indices]
                break
            except ValueError:
                console.print("[red]正しい形式で入力してください（例: 1,5,12）[/red]")

        # 選択した3つをテキストに変換
        pains_text = "\n".join(f"{i}. {p}" for i, p in enumerate(selected_pains, 1))

        console.print(f"\n[green]選択した3つの独り言:[/green]")
        console.print(pains_text)

        # 再生成ループ
        while True:
            prompt_data = load_prompt(
                chapter="chapter1",
                prompt_name="profile_creation",
                variables={
                    "persona": persona["raw_text"],
                    "pains": pains_text,
                    "usp_future": usp_future["raw_text"],
                    "concept": persona["concept"],
                },
            )

            console.print("\n[dim]Claude APIでプロフィール文を生成中...[/dim]")
            response = self.claude.generate_text(
                prompt=prompt_data["user"],
                system_prompt=prompt_data.get("system"),
                temperature=prompt_data.get("temperature", 0.8),
                max_tokens=prompt_data.get("max_tokens", 2000),
            )

            # レスポンスからプロフィール案を抽出（```で囲まれた部分）
            profiles = []
            in_code_block = False
            current_profile = []
            for line in response.split("\n"):
                if line.strip().startswith("```") and not in_code_block:
                    in_code_block = True
                    current_profile = []
                    continue
                if line.strip().startswith("```") and in_code_block:
                    in_code_block = False
                    if current_profile:
                        profiles.append("\n".join(current_profile).strip())
                    current_profile = []
                    continue
                if in_code_block:
                    current_profile.append(line)

            # コードブロックが見つからなかった場合、全体を1つのプロフィールとして扱う
            if len(profiles) == 0:
                profiles = [response.strip()]

            console.print(f"\n[bold green]{len(profiles)}案のプロフィール文を生成しました:[/bold green]\n")
            for i, profile in enumerate(profiles, 1):
                console.print(Panel(profile, title=f"案{i}", border_style="green"))

            # 次のアクションを確認
            console.print("\n[bold yellow]次のアクションを選んでください:[/bold yellow]")
            console.print("  [1] この3案から選択する")
            console.print("  [2] 再度作成（新しい3案を生成）")

            action = click.prompt("番号を入力", type=int, default=1)

            if action == 1:
                break
            else:
                console.print("\n[cyan]新しいプロフィール文を生成します...[/cyan]\n")
                continue

        # 3案から1つを選択
        console.print("\n[bold yellow]どの案でいきますか？[/bold yellow]")
        console.print("  [1] A案：共感・代弁型")
        console.print("  [2] B案：提言・扇動型")
        console.print("  [3] C案：権威・解決型")

        while True:
            selected_index = click.prompt("番号を入力", type=int, default=1)
            if 1 <= selected_index <= len(profiles):
                break
            console.print(f"[red]1〜{len(profiles)}の範囲で選択してください。[/red]")

        selected_profile = profiles[selected_index - 1]
        console.print(f"\n[green]案{selected_index}を選択しました。最終確認リストに進みます...[/green]")

        return profiles, selected_profile

    def final_check(self, selected_profile: str) -> str:
        """
        最終確認リストでチェック

        Args:
            selected_profile: 選択したプロフィール文

        Returns:
            確認結果
        """
        console.print(Panel("Step 7: 最終確認リスト", style="bold cyan"))

        prompt_data = load_prompt(
            chapter="chapter1",
            prompt_name="final_checklist",
            variables={
                "selected_profile": selected_profile,
            },
        )

        console.print("[dim]Claude APIで最終確認を実行中...[/dim]")
        response = self.claude.generate_text(
            prompt=prompt_data["user"],
            system_prompt=prompt_data.get("system"),
            temperature=prompt_data.get("temperature", 0.5),
            max_tokens=prompt_data.get("max_tokens", 2000),
        )

        console.print(f"\n[bold green]最終確認リストの結果:[/bold green]\n")
        console.print(Panel(response, border_style="cyan"))

        return response

    def save_to_sheet(self, data: Dict[str, Any]) -> None:
        """
        結果をGoogle Sheetsに保存

        Args:
            data: 保存するデータ
        """
        console.print(Panel("Step 8: Google Sheetsへの保存", style="bold cyan"))

        spreadsheet_id = get_spreadsheet_id()
        sheet_name = get_sheet_name("strategy")

        rows = []

        # ヘッダー行
        rows.append(["項目", "内容"])

        # 基本情報
        user_input = data.get("user_input", {})
        rows.append(["役割", user_input.get("role", "")])
        rows.append(["サービス", user_input.get("service", "")])
        rows.append(["ターゲット", user_input.get("target", "")])
        rows.append(["", ""])

        # 選択されたコンセプト
        rows.append(["選択コンセプト", data.get("selected_concept", "")])
        rows.append(["", ""])

        # コンセプト20案
        rows.append(["--- コンセプト20案 ---", ""])
        for i, concept in enumerate(data.get("concepts", []), 1):
            rows.append([f"コンセプト{i}", concept])
        rows.append(["", ""])

        # ペルソナ
        rows.append(["--- ペルソナ ---", ""])
        persona = data.get("persona", {})
        rows.append(["ペルソナ詳細", persona.get("raw_text", "")])
        rows.append(["", ""])

        # Pain
        rows.append(["--- 脳内独り言（Pain） ---", ""])
        for i, pain in enumerate(data.get("pains", []), 1):
            rows.append([f"Pain{i}", pain])
        rows.append(["", ""])

        # USP & Future
        rows.append(["--- USP & Future ---", ""])
        usp_future = data.get("usp_future", {})
        rows.append(["USP & Future", usp_future.get("raw_text", "")])
        rows.append(["", ""])

        # プロフィール文
        rows.append(["--- プロフィール文 ---", ""])
        for i, profile in enumerate(data.get("profiles", []), 1):
            rows.append([f"プロフィール案{i}", profile])

        self.sheets.write_range(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            start_cell="A1",
            values=rows,
        )

        console.print(f"[bold green]Google Sheetsに保存しました（シート: {sheet_name}）[/bold green]")

    def run(self) -> Dict[str, Any]:
        """
        Chapter 1の全プロセスを実行

        Returns:
            生成されたデータ
        """
        console.print(Panel(
            "[bold]Chapter 1: 戦略設計[/bold]\n\nSNSアカウントの戦略設計を自動化します。",
            title="SNS Automation",
            border_style="bold blue",
        ))

        # Step 1: ユーザー入力の収集
        user_input = self.collect_user_input()

        # Step 2: コンセプト20案の生成（再生成ループ）
        while True:
            concepts = self.generate_concepts(user_input)

            # 選択 or 再生成の確認
            console.print("\n[bold yellow]次のアクションを選んでください:[/bold yellow]")
            console.print("  [1] この20案から選択する")
            console.print("  [2] 再度作成（新しい20案を生成）")

            while True:
                action = click.prompt("番号を入力", type=int, default=1)
                if action in [1, 2]:
                    break
                console.print("[red]1 または 2 を入力してください[/red]")

            if action == 1:
                # 選択に進む
                break
            else:
                # 再生成
                console.print("\n[cyan]新しいコンセプト案を生成します...[/cyan]\n")
                continue

        # Step 3: コンセプトの選択とペルソナ定義
        console.print("\n[bold yellow]上記のコンセプトから1つ選んでください:[/bold yellow]")
        while True:
            choice = click.prompt("番号を入力（1-20）", type=int)
            if 1 <= choice <= len(concepts):
                break
            console.print(f"[red]1から{len(concepts)}の範囲で入力してください[/red]")

        selected_concept = concepts[choice - 1]
        console.print(f"\n[bold green]選択: {selected_concept}[/bold green]\n")

        persona = self.define_persona(selected_concept, user_input)

        # Step 4: Pain抽出
        pains = self.extract_pains(persona)

        # Step 5: USP & Future定義
        usp_future = self.define_usp_future(persona, pains)

        # Step 6: プロフィール文作成
        profiles, selected_profile = self.create_profiles(persona, usp_future, pains)

        # Step 7: 最終確認リスト
        final_check_result = self.final_check(selected_profile)

        # 全データをまとめる
        data = {
            "user_input": user_input,
            "concepts": concepts,
            "selected_concept": selected_concept,
            "persona": persona,
            "pains": pains,
            "usp_future": usp_future,
            "profiles": profiles,
            "selected_profile": selected_profile,
            "final_check_result": final_check_result,
        }

        # Step 8: Google Sheetsへの保存
        try:
            self.save_to_sheet(data)
        except Exception as e:
            console.print(f"[bold red]Google Sheetsへの保存に失敗しました: {e}[/bold red]")
            console.print("[yellow]JSONファイルへの保存は続行します。[/yellow]")

        # JSONファイルへの保存
        output_dir = Path(self.config.get("paths", {}).get("output", "./output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "chapter1_result.json"

        # persona と usp_future のraw_textを含むデータをJSON化
        json_data = {
            "user_input": user_input,
            "concepts": concepts,
            "selected_concept": selected_concept,
            "persona": {
                "concept": persona["concept"],
                "raw_text": persona["raw_text"],
            },
            "pains": pains,
            "usp_future": {
                "concept": usp_future["concept"],
                "raw_text": usp_future["raw_text"],
            },
            "profiles": profiles,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        console.print(f"\n[bold green]結果をJSONファイルに保存しました: {output_path}[/bold green]")

        # 状態を保存（中断・再開機能）
        self.state_manager.save_state(
            chapter=1,
            step="completed",
            data=json_data,
            metadata={
                "project_name": self.project_name,
                "target": user_input.get("target", ""),
                "concept": selected_concept,
            }
        )

        # 完了メッセージ
        console.print(Panel(
            "[bold green]Chapter 1: 戦略設計が完了しました！[/bold green]\n\n"
            f"コンセプト: {selected_concept}\n"
            f"Pain: {len(pains)}個\n"
            f"プロフィール案: {len(profiles)}案\n"
            f"\n保存先: {output_path}\n"
            f"[dim]プロジェクト: {self.project_name}[/dim]",
            title="完了",
            border_style="bold green",
        ))

        return data


def main():
    """メイン関数"""
    config = load_config()
    automation = StrategyAutomation(config)
    result = automation.run()
    return result


if __name__ == "__main__":
    main()
