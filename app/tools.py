# Copyright 2026 Google LLC
# Firestore and Action Tools for D&D Dungeon Master Agent

import json
import random
import re
import urllib.request
import uuid
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

# CRITICAL: Hardcode the project ID and GCS bucket name as strings.
# DO NOT use os.getenv("GOOGLE_CLOUD_PROJECT") or google.auth.default()
# because on Agent Platform those return the project number instead of project ID.
FIRESTORE_PROJECT = "qwiklabs-gcp-01-521125bdb49e"
GCS_BUCKET_NAME = "dnd-dungeon-master-assets-521125"

_db = None
_storage_client = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=FIRESTORE_PROJECT)
    return _db


def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=FIRESTORE_PROJECT)
    return _storage_client


# =====================================================================
# 1. ITEM IMAGE GENERATION TOOL (GLOBAL REGION GEMINI 3.1 FLASH LITE IMAGE)
# =====================================================================

def generate_item_image(tool_context: ToolContext, item_name: str, item_description: str = "") -> str:
    """Generates an image for a magic item, weapon, or gear using gemini-3.1-flash-lite-image in the global region.

    Saves the image artifact to the Playground Artifacts panel and uploads it to the public Cloud Storage bucket.

    Args:
        tool_context: Context object provided automatically by ADK for artifact saving.
        item_name: Name of the D&D item (e.g., 'Flame Tongue Longsword', 'Amulet of Health', 'Ring of Protection').
        item_description: Detailed visual description of the item.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage (https://storage.googleapis.com/dnd-dungeon-master-assets-521125/items/...).
    """
    client = genai.Client(
        vertexai=True,
        project=FIRESTORE_PROJECT,
        location="global",
    )
    prompt = (
        f"Detailed medieval fantasy digital art illustration of the RPG item: {item_name}. "
        f"{item_description}. Epic item icon, isolated background, high resolution."
    )

    res = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    image_bytes = None
    mime_type = "image/png"
    if res.candidates and res.candidates[0].content and res.candidates[0].content.parts:
        for part in res.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/png"
                break

    if not image_bytes:
        return f"Unable to generate image for item '{item_name}'."

    clean_name = item_name.lower().strip().replace(" ", "_")
    ext = "jpg" if "jpeg" in mime_type else "png"
    filename = f"{clean_name}.{ext}"

    # 1. Save artifact in Playground Artifacts panel
    if tool_context is not None:
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same image bytes to public Cloud Storage bucket
    object_key = f"items/{uuid.uuid4().hex[:8]}_{clean_name}.{ext}"
    storage_cli = get_storage_client()
    bucket = storage_cli.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(object_key)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{object_key}"
    return f"✨ Generated item image for '{item_name}': {public_url}"


# =====================================================================
# 2. PUBLIC D&D 5E API TOOL (FREE OPEN PUBLIC API)
# =====================================================================

def lookup_dnd_rule_or_spell(query: str, category: str = "spells") -> str:
    """Fetches official D&D 5e rules, spell descriptions, or equipment from the free public D&D 5e API (dnd5eapi.co).

    Args:
        query: Name of the spell or equipment to search for (e.g., 'fireball', 'cure-wounds', 'longsword', 'shield').
        category: Search category - 'spells' or 'equipment'. Defaults to 'spells'.

    Returns:
        Formatted details including spell level, range, casting time, damage, and description, or equipment stats.
    """
    clean_query = query.lower().strip().replace(" ", "-")
    cat = category.lower().strip()
    if cat not in ["spells", "equipment"]:
        cat = "spells"

    url = f"https://www.dnd5eapi.co/api/2014/{cat}/{clean_query}"
    req = urllib.request.Request(url, headers={"User-Agent": "DNDDungeonMasterAgent/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if cat == "spells":
            desc = " ".join(data.get("desc", []))
            range_info = data.get("range", "N/A")
            casting_time = data.get("casting_time", "N/A")
            level = data.get("level", "N/A")
            school = data.get("school", {}).get("name", "N/A")
            return (
                f"✨ D&D 5e Official Spell: {data.get('name')}\n"
                f"- Level: {level} ({school})\n"
                f"- Casting Time: {casting_time} | Range: {range_info}\n"
                f"- Description: {desc}"
            )
        else:
            eq_category = data.get("equipment_category", {}).get("name", "N/A")
            cost = f"{data.get('cost', {}).get('quantity', '')} {data.get('cost', {}).get('unit', '')}"
            return (
                f"🗡️ D&D 5e Official Equipment: {data.get('name')}\n"
                f"- Category: {eq_category}\n"
                f"- Cost: {cost}\n"
                f"- Description: {' '.join(data.get('desc', ['Standard D&D 5e gear.']))}"
            )
    except Exception:
        return f"D&D 5e Public API lookup for '{query}' in category '{cat}' returned no exact match."


# =====================================================================
# 3. DICE ROLLING & DIFFICULTY CHECK TOOL (LOCAL & PRIVACY-FOCUSED)
# =====================================================================

def roll_dice(dice_expression: str = "1d20", bonus: int = 0, dc: int = 10) -> str:
    """Executes a D&D dice roll, applies modifiers, and evaluates success against a Target Difficulty Class (DC).

    Args:
        dice_expression: The dice notation string (e.g. '1d20', '2d6', '1d10'). Defaults to '1d20'.
        bonus: Attribute modifier or bonus to add to the roll result (e.g. +3 for high Strength/Dexterity).
        dc: Difficulty Class target (e.g. 10 for easy, 15 for moderate, 20 for hard/unreasonable actions).

    Returns:
        Structured breakdown showing natural dice roll, bonus modifier, total result, and PASS/FAIL outcome.
    """
    match = re.match(r"^(\d+)d(\d+)$", dice_expression.strip().lower())
    if not match:
        num_dice, num_sides = 1, 20
        expr_used = "1d20"
    else:
        num_dice = int(match.group(1))
        num_sides = int(match.group(2))
        expr_used = dice_expression

    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
    natural_sum = sum(rolls)
    total_result = natural_sum + bonus
    is_success = total_result >= dc

    outcome = "PASSED ✅" if is_success else "FAILED ❌"
    
    crit_note = ""
    if num_dice == 1 and num_sides == 20:
        if natural_sum == 20:
            crit_note = " (CRITICAL SUCCESS! 🌟)"
            is_success = True
            outcome = "CRITICAL PASS ✅"
        elif natural_sum == 1:
            crit_note = " (CRITICAL FAILURE! 💀)"
            is_success = False
            outcome = "CRITICAL FAIL ❌"

    return (
        f"🎲 Dice Roll Result ({expr_used}):\n"
        f"- Natural Roll: {rolls} = {natural_sum}{crit_note}\n"
        f"- Stat Bonus: {bonus:+d}\n"
        f"- Final Total: {total_result}\n"
        f"- Target DC (Difficulty): {dc}\n"
        f"- Outcome: {outcome}\n"
        f"Consequence Guidance: {'Action succeeded cleanly. Describe a positive outcome.' if is_success else 'Action failed or incurred consequences. Describe the setback.'}"
    )


# =====================================================================
# 4. REST & RECOVERY TOOL (FIRESTORE STATE MUTATION)
# =====================================================================

def rest_and_recover(character_id: str, rest_type: str = "long") -> str:
    """Executes a Short or Long Rest for a character in Firestore, recovering HP.

    Args:
        character_id: Unique character identifier in Firestore (e.g. 'sample_hero').
        rest_type: 'short' (recovers ~50% max HP) or 'long' (recovers 100% max HP).

    Returns:
        Summary of HP restored and current health status.
    """
    db = get_db()
    doc_ref = db.collection("characters").document(character_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Character '{character_id}' not found in database."

    data = doc.to_dict()
    current_hp = data.get("hp", 0)
    max_hp = data.get("max_hp", 10)
    char_name = data.get("name", character_id)

    if rest_type.lower() == "short":
        recovery = max(1, max_hp // 2)
        new_hp = min(max_hp, current_hp + recovery)
        rest_name = "Short Rest"
    else:
        recovery = max_hp - current_hp
        new_hp = max_hp
        rest_name = "Long Rest"

    doc_ref.update({"hp": new_hp})
    return (
        f"🏕️ {char_name} took a {rest_name}:\n"
        f"- HP Restored: +{recovery}\n"
        f"- Current HP: {new_hp}/{max_hp}"
    )


# =====================================================================
# 5. FIRESTORE DATABASE TOOLS
# =====================================================================

def lookup_monster(monster_name: str) -> str:
    """Reads monster statistics, abilities, and details from the Firestore monsters collection.

    Args:
        monster_name: The name or key of the monster to look up (e.g. 'Goblin', 'Skeleton', 'Beholder', 'Young Red Dragon').

    Returns:
        A string summarizing the monster's stats, HP, AC, CR, and abilities.
    """
    db = get_db()
    norm_key = monster_name.lower().strip().replace(" ", "_")
    doc_ref = db.collection("monsters").document(norm_key)
    doc = doc_ref.get()

    if not doc.exists:
        query = db.collection("monsters").where("name", "==", monster_name.title()).stream()
        results = [d.to_dict() for d in query]
        if results:
            data = results[0]
        else:
            return f"Monster '{monster_name}' not found in the Firestore monsters database."
    else:
        data = doc.to_dict()

    return (
        f"👹 Monster Found: {data.get('name')}\n"
        f"- Type: {data.get('type')}\n"
        f"- HP: {data.get('hp')}/{data.get('max_hp')}\n"
        f"- AC (Armor Class): {data.get('ac')}\n"
        f"- Challenge Rating (CR): {data.get('cr')}\n"
        f"- Description: {data.get('description')}\n"
        f"- Abilities: {data.get('abilities')}\n"
        f"- Location: {data.get('location')}"
    )


def list_monsters() -> str:
    """Lists all available monsters in the Firestore monsters collection.

    Returns:
        A string listing all monsters with their types and CR ratings.
    """
    db = get_db()
    docs = db.collection("monsters").stream()
    monster_list = []
    for doc in docs:
        d = doc.to_dict()
        monster_list.append(f"• {d.get('name')} (Type: {d.get('type')}, CR: {d.get('cr')}, HP: {d.get('hp')})")

    if not monster_list:
        return "No monsters found in the database."

    return "📜 Available Monsters in Database:\n" + "\n".join(monster_list)


def get_character_sheet(character_id: str) -> str:
    """Retrieves a player's character sheet from the Firestore characters collection.

    Args:
        character_id: Unique identifier for the character (e.g. 'sample_hero' or player name).

    Returns:
        Formatted character sheet details including stats, gender, sexuality, talent, and inventory.
    """
    db = get_db()
    doc_ref = db.collection("characters").document(character_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Character '{character_id}' not found in Firestore characters database."

    data = doc.to_dict()
    stats = data.get("stats", {})
    stats_str = ", ".join([f"{k.capitalize()}: {v}" for k, v in stats.items()])
    inv_str = ", ".join(data.get("inventory", []))

    return (
        f"🛡️ Character Sheet: {data.get('name')} (ID: {character_id})\n"
        f"- Race: {data.get('race')} | Class: {data.get('class_name')} | Gender: {data.get('gender', 'Unspecified')} | Sexuality: {data.get('sexuality', 'Unspecified')} | Level: {data.get('level')}\n"
        f"- HP: {data.get('hp')}/{data.get('max_hp')}\n"
        f"- Attributes: {stats_str}\n"
        f"- Unique Talent: {data.get('talent')}\n"
        f"- Inventory: {inv_str}"
    )


def save_character_sheet(
    character_id: str,
    name: str,
    race: str,
    class_name: str,
    gender: str,
    sexuality: str,
    level: int,
    hp: int,
    max_hp: int,
    strength: int,
    dexterity: int,
    constitution: int,
    intelligence: int,
    wisdom: int,
    charisma: int,
    talent: str,
    inventory_items: str,
) -> str:
    """Creates or updates a character sheet document in the Firestore characters collection.

    Args:
        character_id: Unique ID for the character (lowercase, no spaces).
        name: Full character name.
        race: Character race (Elf, Human, Dwarf, etc.).
        class_name: Character class (Fighter, Wizard, Rogue, Ranger, etc.).
        gender: Character gender and identity (e.g., Male, Female, Non-binary, Transgender, Custom).
        sexuality: Character sexuality and attraction preferences (e.g., Straight, Gay, Lesbian, Bisexual, Pansexual, Asexual, etc.).
        level: Character level (1-20).
        hp: Current hit points.
        max_hp: Maximum hit points.
        strength: Strength attribute score (1-20).
        dexterity: Dexterity attribute score (1-20).
        constitution: Constitution attribute score (1-20).
        intelligence: Intelligence attribute score (1-20).
        wisdom: Wisdom attribute score (1-20).
        charisma: Charisma attribute score (1-20).
        talent: Custom unique talent assigned to the character.
        inventory_items: Comma-separated list of inventory items.

    Returns:
        Confirmation message.
    """
    db = get_db()
    items = [item.strip() for item in inventory_items.split(",") if item.strip()]

    char_data = {
        "character_id": character_id,
        "name": name,
        "race": race,
        "class_name": class_name,
        "gender": gender,
        "sexuality": sexuality,
        "level": level,
        "hp": hp,
        "max_hp": max_hp,
        "stats": {
            "strength": strength,
            "dexterity": dexterity,
            "constitution": constitution,
            "intelligence": intelligence,
            "wisdom": wisdom,
            "charisma": charisma,
        },
        "talent": talent,
        "inventory": items,
    }

    db.collection("characters").document(character_id).set(char_data)
    return f"✅ Character sheet for '{name}' ({character_id}) successfully saved to Firestore."


def update_character_hp(character_id: str, hp_change: int) -> str:
    """Modifies a character's current HP (positive for healing, negative for damage) in Firestore.

    Args:
        character_id: Unique ID of the character.
        hp_change: Integer HP change (e.g. -5 for 5 damage, +3 for 3 healing).

    Returns:
        Status string showing old and new HP.
    """
    db = get_db()
    doc_ref = db.collection("characters").document(character_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Character '{character_id}' not found."

    data = doc.to_dict()
    old_hp = data.get("hp", 10)
    max_hp = data.get("max_hp", 10)
    new_hp = max(0, min(max_hp, old_hp + hp_change))

    doc_ref.update({"hp": new_hp})
    return f"💖 HP Updated for {data.get('name')}: {old_hp} ➔ {new_hp} / {max_hp} (Change: {hp_change:+d})"
