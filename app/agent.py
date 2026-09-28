# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");

import json
from pathlib import Path

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    generate_item_image,
    get_character_sheet,
    list_monsters,
    lookup_dnd_rule_or_spell,
    lookup_monster,
    rest_and_recover,
    roll_dice,
    save_character_sheet,
    update_character_hp,
)

# Load Agent Engine resource name from deployment_metadata.json
metadata_file = Path("deployment_metadata.json")
agent_engine_id = None
if metadata_file.exists():
    try:
        with open(metadata_file) as f:
            metadata = json.load(f)
            agent_engine_id = metadata.get("remote_agent_runtime_id")
    except Exception:
        pass

if not agent_engine_id:
    agent_engine_id = "projects/1097060004307/locations/us-east1/reasoningEngines/3909535693906378752"

# Extract numeric Memory Bank ID
memory_bank_id = agent_engine_id.split("/")[-1]

# Agent Engine Sandbox Code Executor for safe Python execution
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_id
)


# Memory Bank Service Builder for future deployments
def memory_service_builder():
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-01-521125bdb49e",
        location="us-east1",
        agent_engine_id=memory_bank_id,
    )


# Write Memory Callback: extracts durable facts (player choices, stats, gender, sexuality, backstory, talents, inventory, decisions)
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        pass
    return None


# A2UI Schema Manager setup for Version 0.8 and Basic Catalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are an interactive Medieval Fantasy D&D Dungeon Master leading an epic tabletop RPG campaign.\n\n"
        "Campaign Rules & Instructions:\n"
        "1. Welcome the player to the realm and guide them through custom character creation:\n"
        "   - Name, Race, Class, Gender/Identity, Sexuality/Attraction, Attributes (Strength, Dexterity, etc.), and Backstory.\n"
        "2. Once character traits are created, assign one unique, custom-tailored talent matching their specific character persona and background.\n"
        "3. Record their full character details into Firestore using `save_character_sheet` (including gender & sexuality).\n"
        "4. Begin the campaign! Enforce dynamic choice & consequences:\n"
        "   - **Gender, Identity & Attraction Dynamics**: Gender, sexuality, and identity play an active role in the world. Make choices, NPC social dynamics, romance, court intrigues, and faction events react meaningfully with authentic consequences based on the character's gender and sexuality.\n"
        "   - Perform difficulty checks using `roll_dice` (scaling DC to action reasonableness and adding attribute bonuses).\n"
        "   - Look up official D&D 5e spells/rules using `lookup_dnd_rule_or_spell`.\n"
        "   - Generate visual item artwork for magical loot using `generate_item_image`.\n"
        "   - Look up campaign monsters using `lookup_monster`.\n"
        "   - Handle HP changes and rests with `update_character_hp` and `rest_and_recover`.\n"
        "5. Memory & Continuity: Remember player stats, gender, sexuality, custom talent, active inventory, campaign history, quest decisions, and level progression across conversations using PreloadMemoryTool."
    ),
    workflow_description="Analyze the user request, run tabletop RPG checks/tools, and return structured A2UI display cards/tables when presenting character sheets, monster encounters, spell/rule lookups, item artwork, or campaign status.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        generate_item_image,
        lookup_dnd_rule_or_spell,
        roll_dice,
        rest_and_recover,
        lookup_monster,
        list_monsters,
        get_character_sheet,
        save_character_sheet,
        update_character_hp,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
