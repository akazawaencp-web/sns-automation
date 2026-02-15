"""
Chapter 2: 競合分析の自動化

このモジュールは、競合分析プロセスを自動化します：
- 動画から静止画の抽出
- AI画像分析
- 分析結果のスプレッドシート記入
- 横断分析（鉄則抽出）
"""

import json
import logging
from typing import Dict, List, Any
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from sns_automation.utils import (
    ClaudeAPI,
    SheetsAPI,
    load_config,
    extract_frames,
    batch_extract,
    load_prompt,
)

logger = logging.getLogger(__name__)
console = Console()

# Chapter 1 の結果を保存するデフォルトパス
CHAPTER1_RESULT_PATH = Path("output/chapter1_result.json")

# 競合分析シート名
ANALYSIS_SHEET_NAME = "競合分析"

# スプレッドシートの列マッピング（D〜H列 = 競合1〜5）
COMPETITOR_COLUMNS = ["D", "E", "F", "G", "H"]
RULES_COLUMN = "I"


class AnalysisAutomation:
    """Chapter 2: 競合分析の自動化クラス"""

    def __init__(self, config: Dict[str, Any]):
        """
        初期化

        Args:
            config: 設定辞書
        """
        self.config = config
        self.claude = ClaudeAPI(config)
        self.sheets = SheetsAPI(config)
        self.spreadsheet_id = config["google_sheets"]["default_spreadsheet_id"]
        self.scoring_criteria: str = ""

    def _load_chapter1_result(self) -> Dict[str, Any]:
        """
        Chapter 1 の結果を読み込む

        Returns:
            Chapter 1 の結果辞書
        """
        output_path = self.config.get("paths", {}).get(
            "chapter1_result", str(CHAPTER1_RESULT_PATH)
        )
        result_path = Path(output_path)

        if not result_path.exists():
            logger.warning(
                "Chapter 1 の結果ファイルが見つかりません: %s. デフォルト値を使用します。",
                result_path,
            )
            return {"concept": "未設定", "persona": "未設定"}

        with open(result_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def analyze_video(self, video_path: Path) -> Dict[str, Any]:
        """
        動画を分析する

        Args:
            video_path: 動画ファイルパス

        Returns:
            分析結果辞書
        """
        console.print(f"  [cyan]動画を分析中: {video_path.name}[/cyan]")

        # 動画からフレームを抽出
        frames_dir = video_path.parent / "frames" / video_path.stem
        frame_paths = extract_frames(video_path, frames_dir, num_frames=5)

        logger.info("%d 枚のフレームを抽出しました: %s", len(frame_paths), video_path.name)

        # プロンプトテンプレートを読み込み
        prompt_data = load_prompt(
            "chapter2",
            "image_analysis",
            variables={
                "competitor_name": video_path.parent.name,
                "video_number": video_path.stem,
                "scoring_criteria": self.scoring_criteria,
            },
        )

        # Claude Vision API で画像分析
        analysis_text = self.claude.generate_with_images(
            prompt=prompt_data["user"],
            image_paths=frame_paths,
            system_prompt=prompt_data.get("system"),
            temperature=prompt_data.get("temperature", 0.3),
            max_tokens=prompt_data.get("max_tokens", 5000),
        )

        return {
            "video_name": video_path.name,
            "video_path": str(video_path),
            "frame_count": len(frame_paths),
            "analysis": analysis_text,
        }

    def analyze_competitor(
        self, video_dir: Path, competitor_name: str
    ) -> Dict[str, Any]:
        """
        競合1社を分析する

        Args:
            video_dir: 動画ディレクトリ
            competitor_name: 競合名

        Returns:
            分析結果辞書
        """
        console.print(f"\n[bold green]競合分析: {competitor_name}[/bold green]")

        # video_dir 内の動画ファイルを取得
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}
        video_files = sorted(
            f
            for f in video_dir.iterdir()
            if f.is_file() and f.suffix.lower() in video_extensions
        )

        if not video_files:
            logger.warning("動画ファイルが見つかりません: %s", video_dir)
            return {
                "competitor_name": competitor_name,
                "video_count": 0,
                "analyses": [],
            }

        console.print(f"  {len(video_files)} 本の動画を検出しました")

        analyses = []
        with Progress() as progress:
            task = progress.add_task(
                f"  {competitor_name} の動画を分析中...",
                total=len(video_files),
            )
            for video_file in video_files:
                result = self.analyze_video(video_file)
                analyses.append(result)
                progress.update(task, advance=1)

        return {
            "competitor_name": competitor_name,
            "video_count": len(video_files),
            "analyses": analyses,
        }

    def cross_analysis(self, all_analyses: List[Dict[str, Any]]) -> List[str]:
        """
        横断分析（鉄則抽出）

        Args:
            all_analyses: 全競合の分析結果

        Returns:
            鉄則リスト
        """
        console.print("\n[bold yellow]横断分析（鉄則抽出）を実行中...[/bold yellow]")

        # Chapter 1 の結果を読み込む
        ch1_result = self._load_chapter1_result()

        # 全分析結果をテキストにまとめる
        analyses_text = ""
        for competitor_data in all_analyses:
            name = competitor_data["competitor_name"]
            analyses_text += f"\n## 競合: {name}\n"
            for video_analysis in competitor_data.get("analyses", []):
                analyses_text += f"\n### {video_analysis['video_name']}\n"
                analyses_text += video_analysis["analysis"] + "\n"

        # プロンプトテンプレートを読み込み
        prompt_data = load_prompt(
            "chapter2",
            "cross_analysis",
            variables={
                "all_analyses": analyses_text,
                "concept": ch1_result.get("concept", "未設定"),
                "persona": ch1_result.get("persona", "未設定"),
            },
        )

        # Claude API で横断分析
        cross_result = self.claude.generate_text(
            prompt=prompt_data["user"],
            system_prompt=prompt_data.get("system"),
            temperature=prompt_data.get("temperature", 0.5),
            max_tokens=prompt_data.get("max_tokens", 6000),
        )

        # 鉄則をリストとして抽出（テーブル行やナンバリングされた項目をパース）
        rules = []
        for line in cross_result.split("\n"):
            line = line.strip()
            # テーブル行（| 1 | 鉄則 | ... |）またはナンバリング行を検出
            if line.startswith("|") and not line.startswith("|---") and not line.startswith("| #"):
                parts = [p.strip() for p in line.split("|")]
                # 最初と最後の空要素を除外、番号列の次が鉄則
                parts = [p for p in parts if p]
                if len(parts) >= 2 and parts[0].isdigit():
                    rules.append(parts[1])
            elif line and line[0].isdigit() and "." in line[:4]:
                # "1. 鉄則" 形式
                rule_text = line.split(".", 1)[1].strip()
                if rule_text:
                    rules.append(rule_text)

        # パースで鉄則が抽出できなかった場合、全文を1要素として返す
        if not rules:
            rules = [cross_result]

        console.print(f"  [green]{len(rules)} 個の鉄則を抽出しました[/green]")

        return rules

    def write_to_sheet(
        self, analyses: List[Dict[str, Any]], rules: List[str]
    ) -> None:
        """
        分析結果をGoogle Sheetsに書き込む

        Args:
            analyses: 分析結果リスト
            rules: 鉄則リスト
        """
        console.print("\n[bold blue]スプレッドシートに書き込み中...[/bold blue]")

        batch_data = []

        # 各競合の分析結果を列（D〜H列）に記入
        for i, competitor_data in enumerate(analyses):
            if i >= len(COMPETITOR_COLUMNS):
                logger.warning(
                    "競合数が列数を超えています。最初の%d社のみ書き込みます。",
                    len(COMPETITOR_COLUMNS),
                )
                break

            col = COMPETITOR_COLUMNS[i]
            name = competitor_data["competitor_name"]

            # ヘッダー行（1行目）に競合名
            values = [[name]]

            # 各動画の分析結果を行に追加
            for video_analysis in competitor_data.get("analyses", []):
                values.append([video_analysis["video_name"]])
                # 分析テキストを適切な長さに分割
                analysis_text = video_analysis["analysis"]
                values.append([analysis_text])

            batch_data.append(
                {
                    "range": f"{ANALYSIS_SHEET_NAME}!{col}1",
                    "values": values,
                }
            )

        # 鉄則をI列に記入
        rules_values = [["鉄則一覧"]]
        for j, rule in enumerate(rules, 1):
            rules_values.append([f"{j}. {rule}"])

        batch_data.append(
            {
                "range": f"{ANALYSIS_SHEET_NAME}!{RULES_COLUMN}1",
                "values": rules_values,
            }
        )

        # バッチ更新で一括書き込み
        self.sheets.batch_update(self.spreadsheet_id, batch_data)

        console.print(
            f"  [green]{len(analyses)} 社の分析結果と{len(rules)}個の鉄則を書き込みました[/green]"
        )

    def run(self, video_dir: Path) -> Dict[str, Any]:
        """
        Chapter 2の全プロセスを実行

        Args:
            video_dir: 動画ディレクトリ

        Returns:
            分析結果
        """
        video_dir = Path(video_dir).resolve()
        console.print("[bold magenta]===== Chapter 2: 競合分析 開始 =====[/bold magenta]\n")

        # Chapter 1 の結果を読み込み
        ch1_result = self._load_chapter1_result()
        console.print("[dim]Chapter 1 の結果を読み込みました[/dim]")

        # 1. 採点基準を生成
        console.print("\n[bold yellow]採点基準を生成中...[/bold yellow]")
        scoring_prompt = load_prompt(
            "chapter2",
            "scoring_criteria",
            variables={
                "concept": ch1_result.get("concept", "未設定"),
                "persona": ch1_result.get("persona", "未設定"),
            },
        )
        self.scoring_criteria = self.claude.generate_text(
            prompt=scoring_prompt["user"],
            system_prompt=scoring_prompt.get("system"),
            temperature=scoring_prompt.get("temperature", 0.5),
            max_tokens=scoring_prompt.get("max_tokens", 5000),
        )
        console.print("  [green]採点基準を生成しました[/green]")

        # 2. 競合ディレクトリを検出（video_dir 直下のサブディレクトリ = 各競合）
        competitor_dirs = sorted(
            d for d in video_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        )

        if not competitor_dirs:
            # サブディレクトリがない場合、video_dir 自体を1つの競合として扱う
            console.print(
                "[yellow]サブディレクトリが見つかりません。"
                "ディレクトリ全体を1つの競合として分析します。[/yellow]"
            )
            competitor_dirs = [video_dir]

        console.print(f"\n{len(competitor_dirs)} 社の競合を検出しました")

        # 3. 各競合の動画を分析
        all_analyses: List[Dict[str, Any]] = []
        for competitor_dir in competitor_dirs:
            competitor_name = competitor_dir.name
            result = self.analyze_competitor(competitor_dir, competitor_name)
            all_analyses.append(result)

        # 4. 横断分析（鉄則抽出）
        rules = self.cross_analysis(all_analyses)

        # 5. スプレッドシートに書き込み
        self.write_to_sheet(all_analyses, rules)

        # 6. 結果をJSONファイルに保存
        output_dir = Path(
            self.config.get("paths", {}).get("output", "output")
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "chapter2_result.json"

        result = {
            "scoring_criteria": self.scoring_criteria,
            "competitors": all_analyses,
            "rules": rules,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        console.print(f"\n[dim]結果を保存しました: {output_path}[/dim]")
        console.print(
            "[bold magenta]===== Chapter 2: 競合分析 完了 =====[/bold magenta]"
        )

        return result


def main(video_dir: str):
    """メイン関数"""
    config = load_config()
    automation = AnalysisAutomation(config)
    result = automation.run(Path(video_dir))
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chapter2_analysis.py <video_dir>")
        sys.exit(1)
    main(sys.argv[1])
