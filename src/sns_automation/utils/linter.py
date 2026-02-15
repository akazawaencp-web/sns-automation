"""
台本・ナレーションの品質チェッカー

SNSコンテンツ向けの品質基準をチェックします。
"""

import re
from typing import Dict, List, Tuple
from pathlib import Path


class ScriptLinter:
    """台本の品質をチェックするLinter"""

    def __init__(self):
        """初期化"""
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []

        # AIっぽい表現パターン
        self.ai_patterns = [
            r"〜することで",
            r"〜することができます",
            r"〜してみましょう",
            r"重要なポイント",
            r"効果的な",
            r"最適な",
            r"ぜひ.*してみてください",
            r"いかがでしたか",
        ]

        # 禁止フレーズ
        self.forbidden_phrases = [
            "AI",
            "Claude",
            "生成しました",
            "自動生成",
            "プロンプト",
            "GPT",
            "ChatGPT",
        ]

    def check_script(self, script_text: str, narration: str) -> Dict[str, any]:
        """
        台本とナレーションの品質をチェック

        Args:
            script_text: 台本全文
            narration: ナレーション全文

        Returns:
            チェック結果
        """
        self.errors = []
        self.warnings = []

        # 各チェック項目を実行
        self._check_bold_usage(script_text)
        self._check_bold_usage(narration, context="ナレーション")
        self._check_ai_patterns(script_text)
        self._check_ai_patterns(narration, context="ナレーション")
        self._check_narration_length(narration)
        self._check_forbidden_phrases(script_text)
        self._check_forbidden_phrases(narration, context="ナレーション")
        self._check_tone_consistency(narration)

        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "passed": len(self.errors) == 0,
        }

    def _check_bold_usage(self, text: str, context: str = "台本") -> None:
        """太字（**）の使用をチェック"""
        if "**" in text:
            matches = re.finditer(r"\*\*(.*?)\*\*", text)
            for match in matches:
                self.errors.append({
                    "type": "bold_usage",
                    "context": context,
                    "message": f"太字が使用されています: {match.group(1)}",
                    "suggestion": "太字を削除してください（AIっぽさを避けるため）",
                })

    def _check_ai_patterns(self, text: str, context: str = "台本") -> None:
        """AIっぽい表現をチェック"""
        for pattern in self.ai_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                self.warnings.append({
                    "type": "ai_pattern",
                    "context": context,
                    "message": f"AIっぽい表現が含まれています: {match.group(0)}",
                    "suggestion": "より自然な口語表現に変更を検討してください",
                })

    def _check_narration_length(self, narration: str) -> None:
        """ナレーションの文字数をチェック"""
        length = len(narration.strip())

        if length < 100:
            self.warnings.append({
                "type": "narration_length",
                "context": "ナレーション",
                "message": f"ナレーションが短すぎます（{length}文字）",
                "suggestion": "最低100文字以上のナレーションを推奨します",
            })
        elif length > 2000:
            self.warnings.append({
                "type": "narration_length",
                "context": "ナレーション",
                "message": f"ナレーションが長すぎます（{length}文字）",
                "suggestion": "2000文字以下に収めることを推奨します（音声時間の制約）",
            })

    def _check_forbidden_phrases(self, text: str, context: str = "台本") -> None:
        """禁止フレーズをチェック"""
        for phrase in self.forbidden_phrases:
            if phrase in text:
                self.errors.append({
                    "type": "forbidden_phrase",
                    "context": context,
                    "message": f"禁止フレーズが含まれています: {phrase}",
                    "suggestion": "メタ表現（AI、生成等）は削除してください",
                })

    def _check_tone_consistency(self, narration: str) -> None:
        """口調の一貫性をチェック"""
        # 「です・ます」調のカウント
        desu_masu_count = len(re.findall(r"です[。、]|ます[。、]", narration))

        # 「だ・である」調のカウント
        da_dearu_count = len(re.findall(r"だ[。、]|である[。、]", narration))

        # 両方が混在している場合は警告
        if desu_masu_count > 0 and da_dearu_count > 0:
            self.warnings.append({
                "type": "tone_inconsistency",
                "context": "ナレーション",
                "message": f"「です・ます」調と「だ・である」調が混在しています（です・ます: {desu_masu_count}箇所、だ・である: {da_dearu_count}箇所）",
                "suggestion": "統一された口調に修正してください",
            })

    def format_results(self, results: Dict[str, any]) -> str:
        """
        チェック結果を整形して表示用テキストに変換

        Args:
            results: check_script()の返り値

        Returns:
            整形されたテキスト
        """
        lines = []
        lines.append("=" * 60)
        lines.append("🔍 台本品質チェック結果")
        lines.append("=" * 60)
        lines.append("")

        # エラー
        if results["errors"]:
            lines.append(f"❌ エラー: {results['error_count']}件")
            lines.append("")
            for i, error in enumerate(results["errors"], 1):
                lines.append(f"{i}. [{error['context']}] {error['message']}")
                lines.append(f"   💡 {error['suggestion']}")
                lines.append("")

        # 警告
        if results["warnings"]:
            lines.append(f"⚠️  警告: {results['warning_count']}件")
            lines.append("")
            for i, warning in enumerate(results["warnings"], 1):
                lines.append(f"{i}. [{warning['context']}] {warning['message']}")
                lines.append(f"   💡 {warning['suggestion']}")
                lines.append("")

        # 合格判定
        lines.append("=" * 60)
        if results["passed"]:
            lines.append("✅ 全ての品質基準をクリアしました！")
        else:
            lines.append(f"❌ {results['error_count']}件のエラーがあります。修正してください。")
        lines.append("=" * 60)

        return "\n".join(lines)


def lint_script(script_text: str, narration: str) -> Dict[str, any]:
    """
    台本とナレーションの品質をチェック（関数版）

    Args:
        script_text: 台本全文
        narration: ナレーション全文

    Returns:
        チェック結果
    """
    linter = ScriptLinter()
    return linter.check_script(script_text, narration)


def lint_script_file(file_path: Path) -> Dict[str, any]:
    """
    JSONファイルから台本を読み込んでチェック

    Args:
        file_path: chapter3_result.jsonのパス

    Returns:
        チェック結果
    """
    import json

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    linter = ScriptLinter()
    all_results = []

    for script in data.get("scripts", []):
        result = linter.check_script(
            script_text=script.get("full_script", ""),
            narration=script.get("narration", ""),
        )
        result["idea_title"] = script.get("idea_title", "")
        all_results.append(result)

    return all_results
