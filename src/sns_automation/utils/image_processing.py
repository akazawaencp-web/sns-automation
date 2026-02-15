"""
動画から静止画を抽出するユーティリティ（ffmpeg使用）
"""

import logging
import shutil
import subprocess
from typing import List
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}


def _check_ffmpeg() -> None:
    """ffmpegがインストールされているか確認する"""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpegが見つかりません。インストールしてください: brew install ffmpeg"
        )


def _check_ffprobe() -> None:
    """ffprobeがインストールされているか確認する"""
    if shutil.which("ffprobe") is None:
        raise RuntimeError(
            "ffprobeが見つかりません。ffmpegと一緒にインストールしてください: brew install ffmpeg"
        )


def _validate_video_file(video_path: Path) -> None:
    """動画ファイルを検証する"""
    if not video_path.exists():
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

    if video_path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"サポートされていない動画形式です: {video_path.suffix}\n"
            f"対応形式: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}"
        )


def get_video_duration(video_path: Path) -> float:
    """
    動画の長さを取得

    Args:
        video_path: 動画ファイルパス

    Returns:
        動画の長さ（秒）
    """
    _check_ffprobe()
    _validate_video_file(video_path)

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"動画の長さを取得できませんでした: {video_path}\n"
            f"ffprobe error: {result.stderr.strip()}"
        )

    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(
            f"動画の長さを解析できませんでした: {result.stdout.strip()}"
        )


def extract_frames(
    video_path: Path,
    output_dir: Path,
    num_frames: int = 5,
) -> List[Path]:
    """
    動画から等間隔で静止画を抽出

    Args:
        video_path: 動画ファイルパス
        output_dir: 出力ディレクトリ
        num_frames: 抽出するフレーム数

    Returns:
        抽出された画像ファイルパスのリスト
    """
    _check_ffmpeg()
    _validate_video_file(video_path)

    if num_frames < 1:
        raise ValueError("num_framesは1以上である必要があります")

    video_path = video_path.resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    duration = get_video_duration(video_path)
    if duration <= 0:
        raise RuntimeError(f"動画の長さが不正です: {duration}秒")

    video_name = video_path.stem

    extracted_paths: List[Path] = []

    for i in range(num_frames):
        if num_frames == 1:
            timestamp = duration / 2
        else:
            timestamp = (duration / (num_frames + 1)) * (i + 1)

        output_path = output_dir / f"{video_name}_frame_{i:03d}.png"

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss", str(timestamp),
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.warning(
                "フレーム %d の抽出に失敗しました (timestamp=%.2f): %s",
                i, timestamp, result.stderr.strip(),
            )
            continue

        if output_path.exists():
            extracted_paths.append(output_path)
            logger.info(
                "フレーム抽出: %s (timestamp=%.2f秒)", output_path.name, timestamp
            )

    if not extracted_paths:
        raise RuntimeError(
            f"フレームを1つも抽出できませんでした: {video_path}"
        )

    logger.info(
        "%s から %d/%d フレームを抽出しました",
        video_path.name, len(extracted_paths), num_frames,
    )

    return extracted_paths


def batch_extract(
    video_dir: Path,
    output_dir: Path,
    num_frames: int = 5,
) -> dict[str, List[Path]]:
    """
    ディレクトリ内の全動画から静止画を抽出

    Args:
        video_dir: 動画ディレクトリ
        output_dir: 出力ディレクトリ
        num_frames: 抽出するフレーム数

    Returns:
        {動画名: 画像パスリスト} の辞書
    """
    video_dir = Path(video_dir).resolve()
    output_dir = Path(output_dir).resolve()

    if not video_dir.exists():
        raise FileNotFoundError(f"動画ディレクトリが見つかりません: {video_dir}")

    if not video_dir.is_dir():
        raise NotADirectoryError(f"ディレクトリではありません: {video_dir}")

    video_files = sorted(
        f for f in video_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
    )

    if not video_files:
        logger.warning("動画ファイルが見つかりません: %s", video_dir)
        return {}

    logger.info("%d 件の動画ファイルを処理します", len(video_files))

    results: dict[str, List[Path]] = {}

    for video_file in video_files:
        video_output_dir = output_dir / video_file.stem
        try:
            frames = extract_frames(video_file, video_output_dir, num_frames)
            results[video_file.name] = frames
        except Exception:
            logger.exception("動画の処理に失敗しました: %s", video_file.name)
            results[video_file.name] = []

    logger.info(
        "バッチ処理完了: %d/%d 件成功",
        sum(1 for v in results.values() if v),
        len(results),
    )

    return results
