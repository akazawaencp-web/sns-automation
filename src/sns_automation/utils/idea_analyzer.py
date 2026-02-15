"""
企画分析モジュール

生成された企画の傾向を分析し、バランスをチェックする
"""

from typing import List, Dict, Any
from collections import Counter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class IdeaAnalyzer:
    """企画の傾向を分析するクラス"""

    # 訴求タイプのキーワード
    APPEAL_KEYWORDS = {
        "恐怖訴求": ["NG", "失敗", "末路", "危険", "損", "後悔", "やばい", "最悪", "罠", "注意"],
        "メリット訴求": ["成功", "効果", "メリット", "得", "おすすめ", "最適", "ベスト", "簡単", "楽"],
        "権威訴求": ["プロ", "専門家", "実績", "証明", "データ", "研究", "〇〇式", "秘訣", "裏側"],
        "共感訴求": ["あるある", "悩み", "気持ち", "わかる", "辛い", "大変", "苦労", "不安"],
        "好奇心訴求": ["知ってる？", "実は", "意外", "驚き", "秘密", "真実", "裏話", "本当は"],
        "緊急性訴求": ["今すぐ", "すぐに", "早く", "急いで", "期間限定", "タイムリミット"],
    }

    def analyze_ideas(self, ideas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        企画リストを分析

        Args:
            ideas: 企画リスト

        Returns:
            分析結果
        """
        if not ideas:
            return {
                "total_count": 0,
                "appeal_distribution": {},
                "is_balanced": False,
                "warnings": ["企画が生成されていません"],
            }

        # 各企画の訴求タイプを分類
        appeal_types = []
        for idea in ideas:
            title = idea.get("title", "")
            summary = idea.get("summary", "")
            combined_text = title + " " + summary

            # 最も多くマッチしたキーワードの訴求タイプを採用
            matches = {}
            for appeal_type, keywords in self.APPEAL_KEYWORDS.items():
                count = sum(1 for keyword in keywords if keyword in combined_text)
                if count > 0:
                    matches[appeal_type] = count

            if matches:
                # 最も多くマッチした訴求タイプ
                primary_type = max(matches, key=matches.get)
                appeal_types.append(primary_type)
            else:
                appeal_types.append("その他")

        # 訴求タイプの分布を計算
        appeal_distribution = Counter(appeal_types)

        # バランスチェック
        warnings = []
        is_balanced = True

        # 1つの訴求タイプが50%以上の場合は警告
        for appeal_type, count in appeal_distribution.items():
            percentage = (count / len(ideas)) * 100
            if percentage > 50:
                warnings.append(f"「{appeal_type}」が{percentage:.0f}%を占めています（バランスが偏っています）")
                is_balanced = False

        # 訴求タイプが2種類以下の場合は警告
        if len(appeal_distribution) <= 2:
            warnings.append(f"訴求タイプのバリエーションが少ないです（{len(appeal_distribution)}種類のみ）")
            is_balanced = False

        return {
            "total_count": len(ideas),
            "appeal_distribution": dict(appeal_distribution),
            "appeal_types": appeal_types,
            "is_balanced": is_balanced,
            "warnings": warnings,
        }

    def show_analysis_report(self, analysis: Dict[str, Any]) -> None:
        """
        分析レポートを表示

        Args:
            analysis: 分析結果
        """
        total = analysis["total_count"]
        distribution = analysis["appeal_distribution"]
        is_balanced = analysis["is_balanced"]
        warnings = analysis["warnings"]

        # 分布テーブル
        table = Table(title="企画の訴求タイプ分布", show_header=True)
        table.add_column("訴求タイプ", style="cyan")
        table.add_column("件数", style="yellow", justify="right")
        table.add_column("割合", style="green", justify="right")

        for appeal_type, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            table.add_row(
                appeal_type,
                str(count),
                f"{percentage:.1f}%",
            )

        console.print("\n")
        console.print(table)

        # 評価
        if is_balanced:
            console.print(Panel(
                "[bold green]✅ バランスの良い企画構成です[/bold green]\n\n"
                "複数の訴求タイプがバランスよく配置されています。",
                title="品質評価",
                border_style="green",
            ))
        else:
            warning_text = "\n".join(f"⚠️  {w}" for w in warnings)
            console.print(Panel(
                f"[bold yellow]⚠️  企画の傾向に偏りがあります[/bold yellow]\n\n"
                f"{warning_text}\n\n"
                "[dim]複数の訴求タイプを組み合わせることで、より幅広いターゲットに響く企画になります。[/dim]",
                title="品質評価",
                border_style="yellow",
            ))

    def should_regenerate(self, analysis: Dict[str, Any]) -> bool:
        """
        再生成を推奨すべきか判定

        Args:
            analysis: 分析結果

        Returns:
            再生成を推奨する場合True
        """
        # バランスが悪い場合は再生成を推奨
        if not analysis["is_balanced"]:
            return True

        # 訴求タイプが3種類未満の場合は再生成を推奨
        if len(analysis["appeal_distribution"]) < 3:
            return True

        return False
