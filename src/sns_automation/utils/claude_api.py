"""
Claude API wrapper
"""

import base64
import logging
import mimetypes
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-6"


class ClaudeAPI:
    """Claude APIのラッパークラス"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化

        Args:
            config: 設定辞書（省略時はget_api_key()を使用）
        """
        if config is None:
            # Streamlit環境またはconfig未指定の場合、get_api_key()を使用
            from .config import get_api_key
            api_key = get_api_key("claude")
            self.model = DEFAULT_MODEL
        else:
            api_key = config["api_keys"]["claude"]
            self.model = config.get("claude", {}).get("model", DEFAULT_MODEL)

        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """
        テキストを生成

        Args:
            prompt: プロンプト
            system_prompt: システムプロンプト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数

        Returns:
            生成されたテキスト
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._call_api(kwargs)
        return response.content[0].text

    def generate_with_images(
        self,
        prompt: str,
        image_paths: List[Path],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """
        画像付きでテキストを生成

        Args:
            prompt: プロンプト
            image_paths: 画像ファイルパスのリスト
            system_prompt: システムプロンプト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数

        Returns:
            生成されたテキスト
        """
        content: List[Dict[str, Any]] = []

        for image_path in image_paths:
            image_path = Path(image_path)
            media_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
            with open(image_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                }
            )

        content.append({"type": "text", "text": prompt})

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": content}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._call_api(kwargs)
        return response.content[0].text

    def batch_generate(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> List[str]:
        """
        バッチでテキストを生成

        Args:
            prompts: プロンプトのリスト
            system_prompt: システムプロンプト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数

        Returns:
            生成されたテキストのリスト
        """
        results: List[str] = []
        for i, prompt in enumerate(prompts):
            logger.info("バッチ生成 %d/%d", i + 1, len(prompts))
            text = self.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            results.append(text)
        return results

    def _call_api(self, kwargs: Dict[str, Any]) -> Any:
        """
        API呼び出しのラッパー（リトライ付き）

        Args:
            kwargs: messages.create に渡す引数

        Returns:
            APIレスポンス
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(**kwargs)
                usage = response.usage
                logger.info(
                    "トークン使用量 - input: %d, output: %d",
                    usage.input_tokens,
                    usage.output_tokens,
                )
                return response
            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning("レート制限に到達。%d秒後にリトライします...", wait)
                    time.sleep(wait)
                else:
                    logger.error("レート制限エラー: リトライ回数を超えました")
                    raise
            except anthropic.APITimeoutError:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning("タイムアウト。%d秒後にリトライします...", wait)
                    time.sleep(wait)
                else:
                    logger.error("タイムアウトエラー: リトライ回数を超えました")
                    raise
            except anthropic.APIError as e:
                logger.error("API エラー: %s", e)
                raise
