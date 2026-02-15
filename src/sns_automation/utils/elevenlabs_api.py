"""
ElevenLabs API wrapper
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from elevenlabs import ElevenLabs
from elevenlabs.core import ApiError

logger = logging.getLogger(__name__)

# ElevenLabs APIのテキスト長制限（1リクエストあたり）
MAX_TEXT_LENGTH = 5000


class ElevenLabsAPI:
    """ElevenLabs APIのラッパークラス"""

    def __init__(self, config: Dict[str, Any]):
        """
        初期化

        Args:
            config: 設定辞書
        """
        api_key = config.get("api_keys", {}).get("elevenlabs")
        if not api_key:
            raise ValueError("ElevenLabs API Keyが設定されていません")

        self.client = ElevenLabs(api_key=api_key)

        el_config = config.get("elevenlabs", {})
        self.default_voice_id: str = el_config.get("default_voice_id", "21m00Tcm4TlvDq8ikWAM")
        self.default_model: str = el_config.get("model", "eleven_multilingual_v2")
        self.stability: float = el_config.get("stability", 0.5)
        self.similarity_boost: float = el_config.get("similarity_boost", 0.75)

    def generate_audio(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_path: Optional[Path] = None,
        model: Optional[str] = None,
    ) -> Path:
        """
        音声を生成

        Args:
            text: テキスト
            voice_id: ボイスID（省略時はデフォルト）
            output_path: 出力パス（省略時は自動生成）
            model: 音声モデル（省略時はデフォルト）

        Returns:
            生成された音声ファイルパス
        """
        voice_id = voice_id or self.default_voice_id
        model = model or self.default_model

        if output_path is None:
            output_path = Path("output.mp3")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        chunks = self._split_text(text)

        if len(chunks) == 1:
            self._generate_single(chunks[0], voice_id, output_path, model)
        else:
            self._generate_concatenated(chunks, voice_id, output_path, model)

        logger.info("音声生成完了: %s", output_path)
        return output_path

    def _generate_single(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        model: str,
    ) -> None:
        """単一テキストから音声を生成してファイルに保存"""
        audio_iterator = self.client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model,
            voice_settings={
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
            },
        )

        with open(output_path, "wb") as f:
            for chunk in audio_iterator:
                f.write(chunk)

    def _generate_concatenated(
        self,
        chunks: List[str],
        voice_id: str,
        output_path: Path,
        model: str,
    ) -> None:
        """複数チャンクの音声を生成して結合"""
        with open(output_path, "wb") as f:
            for i, chunk in enumerate(chunks):
                logger.debug("チャンク %d/%d を生成中...", i + 1, len(chunks))
                audio_iterator = self.client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=chunk,
                    model_id=model,
                    voice_settings={
                        "stability": self.stability,
                        "similarity_boost": self.similarity_boost,
                    },
                )
                for audio_chunk in audio_iterator:
                    f.write(audio_chunk)

    def list_voices(self) -> List[Dict[str, Any]]:
        """
        利用可能なボイスのリストを取得

        Returns:
            ボイス情報のリスト
        """
        response = self.client.voices.get_all()
        voices = []
        for voice in response.voices:
            voices.append({
                "voice_id": voice.voice_id,
                "name": voice.name,
                "category": voice.category,
                "labels": voice.labels,
                "preview_url": voice.preview_url,
            })
        return voices

    def batch_generate(
        self,
        texts: List[str],
        voice_id: Optional[str] = None,
        output_dir: Optional[Path] = None,
        model: Optional[str] = None,
    ) -> List[Path]:
        """
        バッチで音声を生成

        Args:
            texts: テキストのリスト
            voice_id: ボイスID（省略時はデフォルト）
            output_dir: 出力ディレクトリ（省略時はカレント）
            model: 音声モデル（省略時はデフォルト）

        Returns:
            生成された音声ファイルパスのリスト
        """
        if output_dir is None:
            output_dir = Path(".")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results: List[Path] = []
        total = len(texts)

        for i, text in enumerate(texts):
            output_path = output_dir / f"audio_{i:03d}.mp3"
            logger.info("バッチ生成 %d/%d: %s", i + 1, total, output_path.name)
            try:
                generated = self.generate_audio(
                    text=text,
                    voice_id=voice_id,
                    output_path=output_path,
                    model=model,
                )
                results.append(generated)
            except ApiError as e:
                logger.error("音声生成に失敗 (item %d): %s", i + 1, e)
                raise

        logger.info("バッチ生成完了: %d/%d ファイル", len(results), total)
        return results

    @staticmethod
    def _split_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> List[str]:
        """
        長いテキストを分割する

        文末（。！？!?）で分割し、各チャンクがmax_length以下になるようにする。

        Args:
            text: 分割対象のテキスト
            max_length: 1チャンクの最大文字数

        Returns:
            分割されたテキストのリスト
        """
        if len(text) <= max_length:
            return [text]

        delimiters = ["。", "！", "？", "!", "?", "\n"]
        chunks: List[str] = []
        remaining = text

        while remaining:
            if len(remaining) <= max_length:
                chunks.append(remaining)
                break

            # max_length以内で最後の区切り文字を探す
            split_pos = -1
            for delimiter in delimiters:
                pos = remaining.rfind(delimiter, 0, max_length)
                if pos > split_pos:
                    split_pos = pos

            if split_pos == -1:
                # 区切り文字が見つからない場合はmax_lengthで強制分割
                split_pos = max_length - 1

            chunk = remaining[: split_pos + 1].strip()
            if chunk:
                chunks.append(chunk)
            remaining = remaining[split_pos + 1 :].strip()

        return chunks
