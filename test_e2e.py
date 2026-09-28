# Copyright 2026 Google LLC
# Full End-to-End Test Suite for D&D Dungeon Master Agent

import asyncio
import os
import sys

# Ensure project environment variables
os.environ["GOOGLE_CLOUD_PROJECT"] = "qwiklabs-gcp-01-521125bdb49e"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-east1"

print("==================================================")
print("🚀 STARTING FULL END-TO-END VERIFICATION TEST SUITE")
print("==================================================")

# 1. Test importing app.agent and app.tools
try:
    import app.agent as agent_mod
    import app.tools as tools
    from app.a2ui_utils import a2ui_callback
    print("✅ 1. Module Imports: SUCCESS")
except Exception as e:
    print(f"❌ 1. Module Imports: FAILED - {e}")
    sys.exit(1)

# 2. Test Firestore Save & Get Character Sheet (with Gender & Sexuality)
try:
    test_id = "e2e_test_hero"
    save_res = tools.save_character_sheet(
        character_id=test_id,
        name="Astraea Moonshadow",
        race="High Elf",
        class_name="Wizard",
        gender="Non-binary",
        sexuality="Pansexual",
        level=3,
        hp=24,
        max_hp=24,
        strength=10,
        dexterity=16,
        constitution=14,
        intelligence=18,
        wisdom=12,
        charisma=14,
        talent="Arcane Weaver (Spells cast cost less focus)",
        inventory_items="Staff of Power, Spellbook, Healing Potion",
    )
    print(f"✅ 2a. Save Character Sheet: {save_res}")

    sheet_res = tools.get_character_sheet(test_id)
    assert "Non-binary" in sheet_res and "Pansexual" in sheet_res and "Astraea Moonshadow" in sheet_res
    print(f"✅ 2b. Retrieve Character Sheet:\n{sheet_res}")
except Exception as e:
    print(f"❌ 2. Firestore Character Sheet: FAILED - {e}")

# 3. Test HP Updates & Rest Recovery
try:
    hp_res1 = tools.update_character_hp(test_id, -8)
    print(f"✅ 3a. Take Damage (-8 HP): {hp_res1}")
    
    rest_res = tools.rest_and_recover(test_id, rest_type="long")
    print(f"✅ 3b. Long Rest Recovery: {rest_res}")
except Exception as e:
    print(f"❌ 3. HP Updates & Rest: FAILED - {e}")

# 4. Test Firestore Monsters DB
try:
    monsters_list = tools.list_monsters()
    print(f"✅ 4a. List Monsters:\n{monsters_list}")

    goblin_info = tools.lookup_monster("Goblin")
    print(f"✅ 4b. Lookup Monster (Goblin):\n{goblin_info}")
except Exception as e:
    print(f"❌ 4. Firestore Monsters: FAILED - {e}")

# 5. Test Local Dice Roll
try:
    dice_res = tools.roll_dice("1d20", bonus=4, dc=15)
    print(f"✅ 5. Dice Roll Execution:\n{dice_res}")
except Exception as e:
    print(f"❌ 5. Dice Roll: FAILED - {e}")

# 6. Test Free Public D&D 5e API (Spell & Gear Lookups)
try:
    spell_res = tools.lookup_dnd_rule_or_spell("fireball", category="spells")
    print(f"✅ 6a. D&D 5e API Spell Lookup:\n{spell_res}")

    gear_res = tools.lookup_dnd_rule_or_spell("longsword", category="equipment")
    print(f"✅ 6b. D&D 5e API Equipment Lookup:\n{gear_res}")
except Exception as e:
    print(f"❌ 6. Public D&D 5e API: FAILED - {e}")

# 7. Test Image Generation & Public GCS Upload
try:
    print("⏳ Testing Image Generation & GCS Upload (Gemini 3.1 Flash Lite Image)...")
    img_res = tools.generate_item_image(
        tool_context=None,
        item_name="Amulet of Arcane Might",
        item_description="A glowing glowing sapphire pendant encased in silver dragon runes.",
    )
    assert "https://storage.googleapis.com/" in img_res
    print(f"✅ 7. Image Generation & GCS Upload: {img_res}")
except Exception as e:
    print(f"❌ 7. Image Gen & GCS Upload: FAILED - {e}")

# 8. Test A2UI Callback Formatting
try:
    from google.genai import types
    from google.adk.models.llm_response import LlmResponse
    
    sample_a2ui_text = (
        '```json\n'
        '[\n'
        '  {"beginRendering": {"surfaceId": "test", "root": "card1"}},\n'
        '  {"surfaceUpdate": {"surfaceId": "test", "components": [{"id": "card1", "component": {"Card": {"child": "col1"}}}, {"id": "col1", "component": {"Column": {"children": {"explicitList": ["txt1"]}}}}, {"id": "txt1", "component": {"Text": {"text": {"literalString": "Hello A2UI!"}}}}]}}\n'
        ']\n'
        '```'
    )
    dummy_resp = LlmResponse(content=types.Content(role="model", parts=[types.Part(text=sample_a2ui_text)]))
    wrapped_resp = a2ui_callback(None, dummy_resp)
    assert wrapped_resp is not None and wrapped_resp.custom_metadata.get("a2a:response") == "true"
    print("✅ 8. A2UI Output Rewrapping Callback: SUCCESS")
except Exception as e:
    print(f"❌ 8. A2UI Callback: FAILED - {e}")

print("==================================================")
print("🎉 ALL END-TO-END VERIFICATION TESTS COMPLETED!")
print("==================================================")
