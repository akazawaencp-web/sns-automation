# SNS Automation

SNSアカウント構築・運用マニュアル自動化システム

## 概要

このツールは、SNS（Instagram等）アカウントの戦略設計からコンテンツ量産までのプロセスを自動化します。Claude API（Anthropic）を活用したAI生成、Google Sheetsへの自動記入、ElevenLabsによる音声ナレーション生成まで、一連のワークフローをCLIから実行できます。

## 機能一覧

| Chapter | 機能 | 状態 |
|---------|------|------|
| **Chapter 1** | 戦略設計の自動化 | 実装済み |
| **Chapter 2** | 競合分析の自動化 | 実装済み |
| **Chapter 3** | コンテンツ量産の自動化 | 実装済み |

### Chapter 1: 戦略設計

- 勝ち筋コンセプトの自動生成（20案）
- ペルソナの詳細化（10項目）
- 脳内独り言（Pain）の抽出（20個）
- USPとFutureの定義
- プロフィール文の作成（3案）
- Google Sheetsへの自動記入
- 結果のJSON出力（`output/chapter1_result.json`）

### Chapter 2: 競合分析

- 動画から静止画の自動抽出（ffmpeg、5枚/動画）
- AI画像分析（Claude Vision API）
- 採点基準の自動生成
- 分析結果のスプレッドシート記入（D〜H列に競合1〜5）
- 横断分析・鉄則抽出（I列に記入）
- 結果のJSON出力（`output/chapter2_result.json`）

### Chapter 3: コンテンツ量産

- 企画20本の自動生成（Chapter 1/2の結果を活用）
- 対話式の企画選択（個別選択 or 全選択）
- 採用企画から台本の自動作成
- 音声ナレーションの自動生成（ElevenLabs）
- スプレッドシート記入（企画タイトル表・台本表）
- 結果のJSON出力（`output/chapter3_result.json`）

## インストール

### 前提条件

- Python 3.9以上
- ffmpeg（動画処理用、Chapter 2で使用）

#### ffmpegのインストール

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
[ffmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロード

### パッケージのインストール

```bash
# リポジトリをクローン
cd sns-automation

# 依存関係をインストール
pip install -e .

# 開発用依存関係も含める場合
pip install -e ".[dev]"
```

### 設定ファイルの初期化

```bash
# CLIコマンドで初期化（config.yaml.example を config.yaml にコピー）
sns-automation init

# または
sns-automation config init
```

## 事前準備

### 1. API Keyの取得

#### Claude API（Anthropic） -- 必須

1. [Anthropic Console](https://console.anthropic.com/)にアクセス
2. API Keyを発行
3. 料金プランを確認（従量課金制）

#### Google Sheets API -- 必須

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成
3. Google Sheets APIを有効化
4. Service Accountを作成
5. JSONキーファイルをダウンロード

詳細手順: [Google Sheets API Setup Guide](https://developers.google.com/sheets/api/quickstart/python)

#### ElevenLabs API（音声生成用） -- Chapter 3で使用

1. [ElevenLabs](https://elevenlabs.io/)にアクセス
2. アカウント作成
3. API Keyを取得
4. 料金プランを確認

### 2. 設定ファイルの編集

`config.yaml` を編集してAPI Keyと認証情報を設定します。

```yaml
api_keys:
  claude: "your-claude-api-key-here"
  elevenlabs: "your-elevenlabs-api-key-here"

google_sheets:
  credentials_path: "/path/to/service-account-credentials.json"
  default_spreadsheet_id: "your-spreadsheet-id-here"
```

設定ファイルの検索順序:

1. 環境変数 `SNS_AUTOMATION_CONFIG` で指定したパス
2. カレントディレクトリの `config.yaml`
3. `~/.sns-automation/config.yaml`

### 3. Google スプレッドシートの準備

1. 新しいスプレッドシートを作成
2. 以下のシートを作成:
   - `戦略設計` (Chapter 1用)
   - `競合分析` (Chapter 2用)
   - `企画タイトル表` (Chapter 3用)
   - `台本表` (Chapter 3用)
3. Service AccountのメールアドレスにEditor権限を付与
4. スプレッドシートIDを`config.yaml`に設定

スプレッドシートIDは、URLの `/d/` と `/edit` の間の文字列です:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
```

## クイックスタート

最小限の手順で動かす方法です。

```bash
# 1. インストール
cd sns-automation
pip install -e .

# 2. 設定ファイルの初期化
sns-automation init

# 3. config.yaml を編集してAPI Keyを設定
#    （エディタで config.yaml を開いて編集）

# 4. Chapter 1: 戦略設計の実行
sns-automation strategy create

# 5. Chapter 2: 競合分析の実行（動画ファイルを準備してから）
mkdir -p videos/competitor1
# 競合の動画ファイルを videos/competitor1/ に配置
sns-automation analyze ./videos/

# 6. Chapter 3: コンテンツ量産の実行
sns-automation content generate
```

## コマンドリファレンス

### ヘルプ

```bash
# 全体のヘルプ
sns-automation --help

# 各コマンドのヘルプ
sns-automation strategy --help
sns-automation content --help
sns-automation config --help
```

### 設定管理

```bash
# 設定ファイルを初期化（config.yaml.example → config.yaml）
sns-automation init
sns-automation config init

# 現在の設定を表示（API Keyは末尾4文字以外マスク）
sns-automation config show
```

### Chapter 1: 戦略設計

```bash
sns-automation strategy create
```

対話形式で以下の情報を入力します:
- 役割（何をしている人か）
- サービス（何を販売しているか）
- ターゲット（誰に売るか）

自動実行される処理:
1. 勝ち筋コンセプト20案生成
2. コンセプトの選択（番号で指定）
3. ペルソナ10項目定義
4. 脳内独り言（Pain）20個抽出
5. USPとFuture定義
6. プロフィール文3案作成
7. Google Sheetsへ自動記入
8. `output/chapter1_result.json` に結果を保存

### Chapter 2: 競合分析

```bash
sns-automation analyze ./videos/
```

**動画ディレクトリの構成:**

```
videos/
├── competitor1/        # 競合1のディレクトリ
│   ├── video1.mp4
│   ├── video2.mp4
│   └── ...
├── competitor2/        # 競合2のディレクトリ
│   ├── video1.mp4
│   └── ...
└── ...                 # 最大5社まで（D〜H列に対応）
```

サブディレクトリがない場合は、ディレクトリ全体を1つの競合として分析します。

対応する動画形式: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.wmv`

自動実行される処理:
1. Chapter 1の結果読み込み
2. 採点基準の自動生成
3. 各動画から静止画5枚を等間隔で抽出
4. Claude Vision APIで画像分析・採点
5. 横断分析（鉄則抽出）
6. スプレッドシートに結果記入
7. `output/chapter2_result.json` に結果を保存

### Chapter 3: コンテンツ量産

```bash
sns-automation content generate
```

**前提:** Chapter 1、Chapter 2 が完了していること（`output/chapter1_result.json` と `output/chapter2_result.json` が必要）

自動実行される処理:
1. Chapter 1/2の結果読み込み
2. 企画20本を生成
3. 企画タイトル表をスプレッドシートに書き込み
4. 採用企画の選択（番号指定 or `all` で全選択）
5. 選択した企画から台本作成
6. ElevenLabsで音声ナレーション生成
7. 台本表をスプレッドシートに書き込み
8. `output/chapter3_result.json` に結果を保存

## 各Chapterの詳細

### Chapter 1: 戦略設計

対話形式でビジネス情報を入力すると、Claude APIが以下を自動生成します:

| ステップ | 生成内容 | 説明 |
|----------|----------|------|
| Step 1 | 基本情報の入力 | 役割・サービス・ターゲットを対話入力 |
| Step 2 | コンセプト20案 | 差別化された勝ち筋コンセプトを20案生成 |
| Step 3 | ペルソナ定義 | 選択したコンセプトに基づき10項目のペルソナを作成 |
| Step 4 | Pain抽出 | ペルソナの脳内独り言を20個抽出 |
| Step 5 | USP & Future | 独自の売りと約束する未来像を定義 |
| Step 6 | プロフィール文 | SNSプロフィール文を3案作成（各150文字以内） |
| Step 7 | 保存 | Google Sheets + JSONファイルに保存 |

### Chapter 2: 競合分析

競合アカウントの動画を分析し、成功パターン（鉄則）を抽出します:

| ステップ | 処理内容 | 説明 |
|----------|----------|------|
| 前処理 | Chapter 1 結果読み込み | コンセプト・ペルソナ情報を活用 |
| Step 1 | 採点基準の生成 | 7項目の5段階評価基準を自動生成 |
| Step 2 | 動画分析 | ffmpegで静止画抽出 → Claude Vision APIで分析 |
| Step 3 | 横断分析 | 全動画の分析結果から鉄則を抽出 |
| Step 4 | 保存 | Google Sheets + JSONファイルに保存 |

**採点項目:** サムネイル/冒頭のインパクト、構成・ストーリー展開、テロップ・文字装飾、映像クオリティ、BGM・SE・音声、CTA、ペルソナへの刺さり度

### Chapter 3: コンテンツ量産

戦略設計と競合分析の結果を活用してコンテンツを量産します:

| ステップ | 処理内容 | 説明 |
|----------|----------|------|
| Step 1 | 企画生成 | 20本の企画を自動生成（タイトル・タイプ・概要・フック） |
| Step 2 | 企画選択 | 採用する企画を対話式で選択 |
| Step 3 | 台本生成 | 30〜60秒のリール動画台本を自動作成 |
| Step 4 | 音声生成 | ElevenLabsでナレーション音声を自動生成 |
| Step 5 | 保存 | Google Sheets + JSONファイルに保存 |

**企画のコンテンツタイプ:** ノウハウ系、共感系、ストーリー系、比較系、リスト系など

## 出力ファイル

### JSONファイル（`output/` ディレクトリ）

| ファイル | 内容 |
|----------|------|
| `output/chapter1_result.json` | 戦略設計の全結果（コンセプト、ペルソナ、Pain、USP/Future、プロフィール文） |
| `output/chapter2_result.json` | 競合分析の全結果（採点基準、各動画の分析、鉄則） |
| `output/chapter3_result.json` | コンテンツ量産の全結果（企画一覧、台本、音声ファイルパス） |

### 音声ファイル（`output/audio/` ディレクトリ）

| ファイル | 内容 |
|----------|------|
| `output/audio/script_001.mp3` | 台本1のナレーション音声 |
| `output/audio/script_002.mp3` | 台本2のナレーション音声 |
| ... | 選択した企画数に応じて生成 |

### Google Sheets

| シート名 | 内容 | 対応Chapter |
|----------|------|-------------|
| `戦略設計` | 基本情報・コンセプト・ペルソナ・Pain・USP/Future・プロフィール | Chapter 1 |
| `競合分析` | D〜H列に競合1〜5の分析結果、I列に鉄則一覧 | Chapter 2 |
| `企画タイトル表` | 企画20本の一覧（タイトル・タイプ・Pain・概要・フック・効果） | Chapter 3 |
| `台本表` | 台本全文・ナレーションテキスト | Chapter 3 |

## ディレクトリ構成

```
sns-automation/
├── src/
│   └── sns_automation/
│       ├── __init__.py              # パッケージ初期化
│       ├── cli.py                   # CLIエントリーポイント
│       ├── chapter1_strategy.py     # Chapter 1: 戦略設計
│       ├── chapter2_analysis.py     # Chapter 2: 競合分析
│       ├── chapter3_content.py      # Chapter 3: コンテンツ量産
│       └── utils/
│           ├── __init__.py          # ユーティリティ公開
│           ├── claude_api.py        # Claude API wrapper（リトライ付き）
│           ├── sheets_api.py        # Google Sheets API wrapper
│           ├── elevenlabs_api.py    # ElevenLabs API wrapper
│           ├── config.py            # 設定ファイルの読み込み・管理
│           ├── image_processing.py  # ffmpegによる動画→静止画抽出
│           └── prompt_loader.py     # プロンプトテンプレートの読み込み
├── templates/
│   └── prompts.yaml                 # プロンプトテンプレート（Jinja2形式）
├── config.yaml.example              # 設定ファイルのサンプル
├── pyproject.toml                   # パッケージ設定
├── output/                          # 出力ファイル（自動生成）
│   ├── chapter1_result.json
│   ├── chapter2_result.json
│   ├── chapter3_result.json
│   └── audio/                       # 生成音声
├── videos/                          # 入力動画（Chapter 2用、手動配置）
└── frames/                          # 抽出静止画（自動生成）
```

## トラブルシューティング

### 設定ファイルが見つからない

```
設定ファイルが見つかりません
```

**対処法:**
```bash
# 設定ファイルを初期化
sns-automation init

# または環境変数で指定
export SNS_AUTOMATION_CONFIG=/path/to/config.yaml
```

設定ファイルの検索順: 環境変数 → カレントディレクトリ → `~/.sns-automation/config.yaml`

### ffmpegが見つからない

```
RuntimeError: ffmpegが見つかりません
```

**対処法:**
```bash
# インストール確認
ffmpeg -version
ffprobe -version

# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# パスが通っていない場合
export PATH="/path/to/ffmpeg:$PATH"
```

### Claude API認証エラー

```
anthropic.AuthenticationError: ...
```

**対処法:**
1. `config.yaml` の `api_keys.claude` が正しいか確認
2. API Keyが有効か [Anthropic Console](https://console.anthropic.com/) で確認
3. 課金設定が有効か確認

### Claude APIレート制限エラー

```
anthropic.RateLimitError: ...
```

**対処法:**
- 自動リトライ機構（最大3回、指数バックオフ）が組み込まれています
- 頻繁に発生する場合はAPI利用プランの確認・アップグレードを検討してください

### Google Sheets API認証エラー

```
google.auth.exceptions.DefaultCredentialsError: ...
```

**対処法:**
1. `config.yaml` の `google_sheets.credentials_path` が正しいか確認
2. Service AccountのJSONファイルが存在するか確認
3. Google Cloud ConsoleでGoogle Sheets APIが有効化されているか確認
4. スプレッドシートにService Accountのメールアドレスを共有（Editor権限）しているか確認

### ElevenLabs APIエラー

```
elevenlabs.core.ApiError: ...
```

**対処法:**
1. `config.yaml` の `api_keys.elevenlabs` が正しいか確認
2. ElevenLabsの利用制限（文字数/月）に達していないか確認
3. ボイスIDが有効か確認

### Chapter 3 実行時に結果ファイルが見つからない

```
FileNotFoundError: Chapter 1 の結果ファイルが見つかりません
```

**対処法:**
- Chapter 1 → Chapter 2 → Chapter 3 の順に実行してください
- `output/chapter1_result.json` と `output/chapter2_result.json` が存在するか確認
- `config.yaml` の `paths.output` の設定を確認

### ログファイルの確認

ログファイルは `config.yaml` の `logging.file` で指定した場所に出力されます（デフォルト: `./logs/sns-automation.log`）。

```bash
# ログの確認
cat logs/sns-automation.log

# DEBUG レベルのログを有効にする場合は config.yaml を編集:
# logging:
#   level: "DEBUG"
```

## コスト見積もり

### 1アカウントあたり

| 項目 | API | 推定コスト |
|------|-----|-----------|
| Chapter 1: 戦略設計 | Claude API | 約$0.5 |
| Chapter 2: 競合分析（5社x5動画） | Claude API (Vision) | 約$2.0 |
| Chapter 3: 企画生成 + 台本作成 | Claude API | 約$1.0 |
| Chapter 3: 音声生成（20本） | ElevenLabs | 約$0.5〜$2.0 |
| Google Sheets API | - | 無料 |

### 月間10アカウント運用時

- Claude API: 約$35/月
  - Chapter 1: $5
  - Chapter 2: $20（画像分析含む）
  - Chapter 3: $10
- ElevenLabs: $5〜$22/月（プランによる）
- Google Sheets API: 無料

**総額: 約$40〜$60/月**

## 設定ファイル（config.yaml）の詳細

すべての設定項目とデフォルト値:

```yaml
# API Keys
api_keys:
  claude: "your-claude-api-key-here"        # 必須
  elevenlabs: "your-elevenlabs-api-key-here" # Chapter 3で必須

# Google Sheets API
google_sheets:
  credentials_path: "/path/to/credentials.json"  # 必須
  default_spreadsheet_id: "your-spreadsheet-id"   # 必須
  sheets:
    strategy: "戦略設計"       # Chapter 1のシート名
    analysis: "競合分析"       # Chapter 2のシート名
    ideas: "企画タイトル表"     # Chapter 3の企画シート名
    scripts: "台本表"          # Chapter 3の台本シート名

# ディレクトリパス
paths:
  output: "./output"   # 出力ファイルの保存先
  videos: "./videos"   # 入力動画の格納先
  frames: "./frames"   # 抽出静止画の保存先
  audio: "./audio"     # 生成音声の保存先

# Claude API設定
claude:
  model: "claude-sonnet-4-5-20250929"  # 使用するモデル
  temperature: 0.7                      # デフォルトの温度
  max_tokens: 4000                      # デフォルトの最大トークン数

# ElevenLabs設定
elevenlabs:
  default_voice_id: "21m00Tcm4TlvDq8ikWAM"  # デフォルトボイス（Rachel）
  model: "eleven_multilingual_v2"             # 音声モデル
  stability: 0.5                              # 音声安定性
  similarity_boost: 0.75                      # 類似性ブースト

# Chapter 2設定
analysis:
  frames_per_video: 5   # 1動画あたりの静止画抽出数
  num_competitors: 5     # 分析する競合の数

# Chapter 3設定
content:
  num_ideas: 20          # 生成する企画の数
  max_script_length: 2000 # 台本の最大文字数

# ログ設定
logging:
  level: "INFO"                        # ログレベル（DEBUG/INFO/WARNING/ERROR）
  file: "./logs/sns-automation.log"    # ログファイルの出力先
```

## 開発

### テストの実行

```bash
pytest
```

### コードフォーマット

```bash
black src/
ruff check src/
```

### 型チェック

```bash
mypy src/
```

### 依存パッケージ

| パッケージ | 用途 |
|-----------|------|
| `anthropic` | Claude API クライアント |
| `google-auth`, `google-api-python-client` | Google Sheets API |
| `elevenlabs` | ElevenLabs 音声生成 |
| `pyyaml` | 設定ファイル・プロンプトテンプレートの読み込み |
| `jinja2` | プロンプトテンプレートの変数展開 |
| `click` | CLIフレームワーク |
| `rich` | ターミナルのリッチ表示（テーブル・プログレスバー） |
| `pillow` | 画像処理 |

## ライセンス

MIT License

## サポート

問題が発生した場合は、Issueを作成してください。

## 今後の予定

- [ ] Webインターフェース（Streamlit/Gradio）
- [ ] バッチ処理機能
- [ ] 業界別プロンプトテンプレート
- [ ] Instagram投稿の自動化（Meta API）
- [ ] CapCut自動編集スクリプト
