"""
プロンプトテンプレートの読み込みと管理
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template


class PromptLoader:
    """プロンプトテンプレートを読み込み・管理するクラス"""

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        初期化

        Args:
            templates_dir: テンプレートディレクトリ（省略時は自動検索）
        """
        if templates_dir is None:
            # デフォルトのテンプレートディレクトリを検索
            templates_dir = self._find_templates_dir()

        self.templates_dir = templates_dir
        self.prompts: Dict[str, Any] = {}

        # Jinja2環境の初期化
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # プロンプトファイルの読み込み
        self._load_prompts()

    def _find_templates_dir(self) -> Path:
        """
        テンプレートディレクトリを検索

        Returns:
            テンプレートディレクトリのパス

        Raises:
            FileNotFoundError: テンプレートディレクトリが見つからない場合
        """
        # 1. カレントディレクトリの templates/
        current_templates = Path.cwd() / "templates"
        if current_templates.exists():
            return current_templates

        # 2. パッケージのインストールディレクトリから相対パス
        package_dir = Path(__file__).parent.parent.parent.parent
        package_templates = package_dir / "templates"
        if package_templates.exists():
            return package_templates

        # 3. ホームディレクトリの .sns-automation/templates/
        home_templates = Path.home() / ".sns-automation" / "templates"
        if home_templates.exists():
            return home_templates

        raise FileNotFoundError(
            "テンプレートディレクトリが見つかりません。以下のいずれかに templates/ を配置してください:\n"
            "1. カレントディレクトリ\n"
            "2. パッケージディレクトリ\n"
            "3. ~/.sns-automation/templates/"
        )

    def _load_prompts(self) -> None:
        """
        プロンプトファイルを読み込む

        トークン効率化のため、Chapter別に分割されたファイルから読み込みます。
        後方互換性のため、prompts.yamlが存在する場合はそちらを優先します。
        """
        prompts_file = self.templates_dir / "prompts.yaml"

        # 後方互換性：prompts.yamlが存在する場合はそちらを使用
        if prompts_file.exists():
            with open(prompts_file, "r", encoding="utf-8") as f:
                self.prompts = yaml.safe_load(f)
            return

        # 新形式：Chapter別に分割されたファイルを読み込み
        self.prompts = {}

        # Chapter 1を読み込み
        chapter1_file = self.templates_dir / "chapter1.yaml"
        if chapter1_file.exists():
            with open(chapter1_file, "r", encoding="utf-8") as f:
                self.prompts["chapter1"] = yaml.safe_load(f)

        # Chapter 3を読み込み
        chapter3_file = self.templates_dir / "chapter3.yaml"
        if chapter3_file.exists():
            with open(chapter3_file, "r", encoding="utf-8") as f:
                self.prompts["chapter3"] = yaml.safe_load(f)

        # どちらも存在しない場合はエラー
        if not self.prompts:
            raise FileNotFoundError(
                f"プロンプトファイルが見つかりません。以下のいずれかを配置してください:\n"
                f"1. {prompts_file} (旧形式)\n"
                f"2. {self.templates_dir}/chapter1.yaml と chapter3.yaml (新形式)"
            )

    def get_prompt(
        self, chapter: str, prompt_name: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        プロンプトを取得し、変数を埋め込む

        Args:
            chapter: チャプター名（chapter1, chapter2, chapter3）
            prompt_name: プロンプト名
            variables: 埋め込む変数の辞書

        Returns:
            プロンプト辞書（system, user, temperature, max_tokens）

        Raises:
            KeyError: プロンプトが見つからない場合
        """
        if chapter not in self.prompts or prompt_name not in self.prompts.get(chapter, {}):
            # キャッシュが古い可能性があるため、テンプレートを再読み込みして再試行
            self.reload()

        if chapter not in self.prompts:
            raise KeyError(f"チャプター '{chapter}' が見つかりません")

        chapter_prompts = self.prompts[chapter]
        if prompt_name not in chapter_prompts:
            raise KeyError(
                f"プロンプト '{prompt_name}' がチャプター '{chapter}' に見つかりません"
            )

        prompt_template = chapter_prompts[prompt_name]

        # 変数の埋め込み
        if variables is None:
            variables = {}

        result = {}

        # system プロンプトの処理
        if "system" in prompt_template:
            system_template = Template(prompt_template["system"])
            result["system"] = system_template.render(**variables)

        # user プロンプトの処理
        if "user" in prompt_template:
            user_template = Template(prompt_template["user"])
            result["user"] = user_template.render(**variables)

        # その他のパラメータをコピー
        for key in ["temperature", "max_tokens"]:
            if key in prompt_template:
                result[key] = prompt_template[key]

        return result

    def list_prompts(self, chapter: Optional[str] = None) -> Dict[str, list]:
        """
        利用可能なプロンプトのリストを取得

        Args:
            chapter: チャプター名（省略時は全チャプター）

        Returns:
            {チャプター名: [プロンプト名リスト]} の辞書
        """
        if chapter is not None:
            if chapter not in self.prompts:
                return {}
            return {chapter: list(self.prompts[chapter].keys())}

        result = {}
        for chap_name, chap_prompts in self.prompts.items():
            result[chap_name] = list(chap_prompts.keys())

        return result

    def reload(self) -> None:
        """プロンプトファイルを再読み込み"""
        self._load_prompts()


# グローバルインスタンス
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader(templates_dir: Optional[Path] = None) -> PromptLoader:
    """
    グローバルなPromptLoaderインスタンスを取得

    Args:
        templates_dir: テンプレートディレクトリ（初回のみ有効）

    Returns:
        PromptLoaderインスタンス
    """
    global _prompt_loader

    if _prompt_loader is None:
        _prompt_loader = PromptLoader(templates_dir)

    return _prompt_loader


def load_prompt(
    chapter: str, prompt_name: str, variables: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    プロンプトを読み込む（便利関数）

    Args:
        chapter: チャプター名
        prompt_name: プロンプト名
        variables: 埋め込む変数

    Returns:
        プロンプト辞書
    """
    loader = get_prompt_loader()
    return loader.get_prompt(chapter, prompt_name, variables)
