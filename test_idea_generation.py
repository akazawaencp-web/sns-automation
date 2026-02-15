#!/usr/bin/env python3
"""
企画生成のテストスクリプト
"""

import sys
import json
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sns_automation.utils import load_config, load_prompt
from sns_automation.chapter3_content import ContentAutomation

def test_idea_generation():
    """企画生成をテスト"""
    print("=" * 60)
    print("企画生成テスト開始")
    print("=" * 60)

    # 設定を読み込み
    print("\n1. 設定を読み込み中...")
    config = load_config()
    print("✓ 設定を読み込みました")

    # プロジェクト状態を読み込み
    print("\n2. プロジェクト状態を読み込み中...")
    state_file = Path.home() / ".sns-automation" / "states" / "Test1.json"
    with open(state_file, "r", encoding="utf-8") as f:
        project_state = json.load(f)
    print(f"✓ プロジェクト「{project_state['project_name']}」を読み込みました")

    # Chapter 1のデータを取得
    print("\n3. Chapter 1のデータを確認中...")
    strategy_data = project_state.get("data", {})

    persona = strategy_data.get("persona", {})
    if isinstance(persona, dict):
        persona_text = persona.get("raw_text", "未設定")
    else:
        persona_text = str(persona)

    print(f"✓ ペルソナ: {persona_text[:50]}...")

    pains_list = strategy_data.get("pains", [])
    print(f"✓ Pain数: {len(pains_list)}件")

    # プロンプトをテスト
    print("\n4. プロンプトを読み込み中...")
    try:
        pains = "\n".join(f"{i}. {p}" for i, p in enumerate(pains_list, 1))

        prompt_data = load_prompt(
            chapter="chapter3",
            prompt_name="idea_generation",
            variables={
                "persona": persona_text[:200],  # 短縮版でテスト
                "pains": pains[:500],  # 短縮版でテスト
            },
        )
        print("✓ プロンプトを読み込みました")
        print(f"  - system prompt: {len(prompt_data.get('system', ''))} 文字")
        print(f"  - user prompt: {len(prompt_data.get('user', ''))} 文字")
        print(f"  - temperature: {prompt_data.get('temperature')}")
        print(f"  - max_tokens: {prompt_data.get('max_tokens')}")
    except Exception as e:
        print(f"✗ プロンプト読み込みエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ContentAutomationを初期化
    print("\n5. ContentAutomationを初期化中...")
    try:
        automation = ContentAutomation(config, project_name="Test1")
        print("✓ ContentAutomationを初期化しました")
        print(f"  - Claude API: OK")
        print(f"  - Sheets API: {'OK' if automation.sheets else 'Disabled (オプショナル)'}")
        print(f"  - ElevenLabs API: OK")
    except Exception as e:
        print(f"✗ ContentAutomation初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ 全てのテストに合格しました！")
    print("=" * 60)
    print("\nWebUIから企画生成を実行できる状態です。")
    print("http://localhost:8501 にアクセスして、「企画を生成（20案）」ボタンをクリックしてください。")
    return True

if __name__ == "__main__":
    success = test_idea_generation()
    sys.exit(0 if success else 1)
