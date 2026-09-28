# Copyright 2026 Google LLC
# Seed script for D&D Dungeon Master Firestore database

from google.cloud import firestore

# CRITICAL: Hardcode the project ID as a string.
# DO NOT use os.getenv("GOOGLE_CLOUD_PROJECT") or google.auth.default()
# because on Agent Platform those return the project number instead of project ID.
FIRESTORE_PROJECT = "qwiklabs-gcp-01-521125bdb49e"

def seed():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT}...")
    db = firestore.Client(project=FIRESTORE_PROJECT)

    # Seed Monsters Collection
    monsters_ref = db.collection("monsters")
    monsters_data = {
        "goblin": {
            "name": "Goblin",
            "type": "Humanoid",
            "hp": 7,
            "max_hp": 7,
            "ac": 15,
            "cr": "1/4",
            "description": "A small, malicious humanoid with sharp teeth and yellow eyes.",
            "abilities": "Nimble Escape, Scimitar (+4 to hit, 1d6+2 slashing)",
            "location": "Dank Caves",
        },
        "skeleton": {
            "name": "Skeleton",
            "type": "Undead",
            "hp": 13,
            "max_hp": 13,
            "ac": 13,
            "cr": "1/4",
            "description": "An animated skeletal warrior wielding a rusty shortsword.",
            "abilities": "Shortsword (+4 to hit, 1d6+2 piercing)",
            "location": "Ancient Crypt",
        },
        "young_red_dragon": {
            "name": "Young Red Dragon",
            "type": "Dragon",
            "hp": 178,
            "max_hp": 178,
            "ac": 18,
            "cr": "10",
            "description": "A fierce red dragon breathing terrifying flames.",
            "abilities": "Fire Breath (16d6 fire), Multiattack",
            "location": "Mountain Peak",
        },
        "beholder": {
            "name": "Beholder",
            "type": "Aberration",
            "hp": 180,
            "max_hp": 180,
            "ac": 18,
            "cr": "13",
            "description": "A floating orb with a giant central eye and ten eyestalks.",
            "abilities": "Antimagic Cone, Eye Rays (Disintegration, Death, Charm)",
            "location": "Underdark Dungeon",
        },
    }

    for doc_id, data in monsters_data.items():
        monsters_ref.document(doc_id).set(data)
        print(f"  ✓ Seeded monster: {data['name']} ({doc_id})")

    # Seed Sample Character Sheet
    characters_ref = db.collection("characters")
    sample_hero = {
        "character_id": "sample_hero",
        "name": "Eldrin the Brave",
        "race": "Elf",
        "class_name": "Ranger",
        "level": 1,
        "hp": 12,
        "max_hp": 12,
        "stats": {
            "strength": 12,
            "dexterity": 16,
            "constitution": 14,
            "intelligence": 12,
            "wisdom": 14,
            "charisma": 10,
        },
        "talent": "Shadow Step (Advantage on stealth checks in shadows)",
        "inventory": ["Longbow", "Leather Armor", "Rations (5)", "Torch"],
        "created_at": "2026-09-28T02:00:00Z",
    }
    characters_ref.document("sample_hero").set(sample_hero)
    print("  ✓ Seeded sample character: Eldrin the Brave (sample_hero)")

    print("\n✅ Firestore seeding complete!")

if __name__ == "__main__":
    seed()
