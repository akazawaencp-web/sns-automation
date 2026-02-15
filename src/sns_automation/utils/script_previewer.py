"""
台本プレビューモジュール

生成された台本の推定時間、文字数をチェックする
"""

import re
from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class ScriptPreviewer:
    """台本のプレビュー情報を生成するクラス"""

    # 日本語の読み上げ速度（文字/秒）
    READING_SPEED = 6.5  # 平均6.5文字/秒（約390文字/分）

    def preview_script(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """
        台本のプレビュー情報を生成

        Args:
            script: 台本辞書

        Returns:
            プレビュー情報
        """
        narration = script.get("narration", "")
        full_script = script.get("full_script", "")

        # ナレーション全文の文字数
        narration_length = len(narration)

        # 推定読み上げ時間（秒）
        estimated_duration = narration_length / self.READING_SPEED

        # スライドごとの情報を抽出
        slides = self._extract_slides(full_script)

        # 各スライドの文字数チェック
        slide_warnings = []
        for i, slide in enumerate(slides, 1):
            char_count = len(slide.get("narration", ""))
            duration = slide.get("duration", "")

            # 6-7秒のスライドで30-49文字の範囲外の場合は警告
            if char_count < 30:
                slide_warnings.append(f"スライド{i}: 文字数が少なすぎます（{char_count}文字 < 30文字）")
            elif char_count > 49:
                slide_warnings.append(f"スライド{i}: 文字数が多すぎます（{char_count}文字 > 49文字）")

        # 全体の推定時間チェック
        time_warning = None
        if estimated_duration < 24:  # 4スライド × 6秒 = 24秒
            time_warning = f"動画が短すぎる可能性があります（推定{estimated_duration:.1f}秒 < 24秒）"
        elif estimated_duration > 42:  # 6スライド × 7秒 = 42秒
            time_warning = f"動画が長すぎる可能性があります（推定{estimated_duration:.1f}秒 > 42秒）"

        return {
            "narration_length": narration_length,
            "estimated_duration": estimated_duration,
            "slide_count": len(slides),
            "slides": slides,
            "slide_warnings": slide_warnings,
            "time_warning": time_warning,
            "has_issues": len(slide_warnings) > 0 or time_warning is not None,
        }

    def _extract_slides(self, script_text: str) -> List[Dict[str, Any]]:
        """
        台本テキストからスライド情報を抽出

        Args:
            script_text: 台本テキスト

        Returns:
            スライド情報のリスト
        """
        slides = []

        # テーブル行をパース（| スライドNo | 秒数 | テロップ | ナレーション | ... |）
        for line in script_text.split("\n"):
            line = line.strip()

            # テーブル行をチェック
            if line.startswith("|") and "/" in line:  # スライドNo列に "/" が含まれる
                parts = [p.strip() for p in line.split("|")[1:-1]]

                if len(parts) >= 4:
                    try:
                        slide_no = parts[0]
                        duration = parts[1]
                        telop = parts[2]
                        narration = parts[3]

                        # ヘッダー行やサンプル行をスキップ
                        if "スライドNo" in slide_no or "例：" in narration:
                            continue

                        slides.append({
                            "slide_no": slide_no,
                            "duration": duration,
                            "telop": telop,
                            "narration": narration,
                        })
                    except:
                        continue

        return slides

    def show_preview(self, preview: Dict[str, Any], idea_title: str = "") -> None:
        """
        プレビュー情報を表示

        Args:
            preview: プレビュー情報
            idea_title: 企画タイトル
        """
        title_text = f"台本プレビュー" + (f": {idea_title}" if idea_title else "")

        # 基本情報
        info_text = (
            f"[bold]ナレーション文字数:[/bold] {preview['narration_length']}文字\n"
            f"[bold]推定読み上げ時間:[/bold] {preview['estimated_duration']:.1f}秒\n"
            f"[bold]スライド枚数:[/bold] {preview['slide_count']}枚"
        )

        # スライド詳細
        if preview['slides']:
            table = Table(title="スライド詳細", show_header=True)
            table.add_column("No", style="cyan", width=6)
            table.add_column("秒数", style="yellow", width=8)
            table.add_column("ナレーション", style="green", width=40)
            table.add_column("文字数", style="magenta", width=8, justify="right")

            for slide in preview['slides']:
                char_count = len(slide['narration'])
                # 文字数が範囲外の場合は色を変える
                if char_count < 30 or char_count > 49:
                    char_style = "bold red"
                else:
                    char_style = "green"

                table.add_row(
                    slide['slide_no'],
                    slide['duration'],
                    slide['narration'][:40] + ("..." if len(slide['narration']) > 40 else ""),
                    f"[{char_style}]{char_count}文字[/{char_style}]",
                )

            console.print("\n")
            console.print(table)

        # 警告
        warnings = []
        if preview['time_warning']:
            warnings.append(preview['time_warning'])
        warnings.extend(preview['slide_warnings'])

        if warnings:
            warning_text = "\n".join(f"⚠️  {w}" for w in warnings)
            console.print(Panel(
                f"[bold yellow]{warning_text}[/bold yellow]\n\n"
                "[dim]推奨範囲: 各スライド30-49文字、全体24-42秒[/dim]",
                title="⚠️  品質チェック",
                border_style="yellow",
            ))
        else:
            console.print(Panel(
                f"[bold green]✅ 全ての品質基準を満たしています[/bold green]\n\n"
                f"{info_text}",
                title="✅ 品質チェック",
                border_style="green",
            ))

    def needs_revision(self, preview: Dict[str, Any]) -> bool:
        """
        修正が必要か判定

        Args:
            preview: プレビュー情報

        Returns:
            修正が必要な場合True
        """
        return preview.get("has_issues", False)
