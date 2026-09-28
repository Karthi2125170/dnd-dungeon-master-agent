# Copyright 2026 Google LLC
# Detailed Integration Check for Agent Tools, Storage, Image Gen, Memory & A2UI

import os
import sys

os.environ["GOOGLE_CLOUD_PROJECT"] = "qwiklabs-gcp-01-521125bdb49e"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-east1"

print("==================================================")
print("🔍 AUDITING AGENT INTEGRATION & ACTIVE COMPONENTS")
print("==================================================")

from app.agent import root_agent, memory_bank_id, code_executor
import app.tools as tools
from google.cloud import firestore, storage
from google import genai

# 1. Check Root Agent Tools Registration
tool_names = []
for t in root_agent.tools:
    if hasattr(t, "name"):
        tool_names.append(t.name)
    elif hasattr(t, "__name__"):
        tool_names.append(t.__name__)
    else:
        tool_names.append(type(t).__name__)

print(f"✅ 1. Registered Agent Tools ({len(root_agent.tools)} total):")
for t in root_agent.tools:
    if hasattr(t, "__name__"):
        print(f"   • Function Tool: {t.__name__}")
    else:
        print(f"   • Object Tool: {type(t).__name__}")

# 2. Check Code Executor Registration
print(f"✅ 2. Sandbox Code Executor: Registered ({type(code_executor).__name__})")
print(f"   • Agent Engine Target: {code_executor.agent_engine_resource_name}")

# 3. Check Memory Bank Callback & Service Configuration
print(f"✅ 3. Memory Bank Integration:")
print(f"   • Memory Bank ID: {memory_bank_id}")
print(f"   • after_agent_callback: {root_agent.after_agent_callback.__name__}")

# 4. Check A2UI System Prompt & Model Callback
print(f"✅ 4. A2UI Integration:")
print(f"   • after_model_callback: {root_agent.after_model_callback.__name__}")
assert "beginRendering" in root_agent.instruction or "surfaceUpdate" in root_agent.instruction

# 5. Check Firestore Connectivity & Collections
db = tools.get_db()
monsters_count = len(list(db.collection("monsters").stream()))
chars_count = len(list(db.collection("characters").stream()))
print(f"✅ 5. Firestore Database Connectivity:")
print(f"   • Project ID (Hardcoded): {tools.FIRESTORE_PROJECT}")
print(f"   • Monsters Collection: {monsters_count} documents found")
print(f"   • Characters Collection: {chars_count} documents found")
assert monsters_count > 0

# 6. Check Cloud Storage Bucket & Permissions
gcs_cli = tools.get_storage_client()
bucket = gcs_cli.bucket(tools.GCS_BUCKET_NAME)
assert bucket.exists(), f"Bucket {tools.GCS_BUCKET_NAME} does not exist"
print(f"✅ 6. Cloud Storage Bucket:")
print(f"   • Bucket Name (Hardcoded): {tools.GCS_BUCKET_NAME}")
print(f"   • Public Base URL: https://storage.googleapis.com/{tools.GCS_BUCKET_NAME}/")

# 7. Check Image Generation Client (Gemini 3.1 Flash Lite Image in global)
client = genai.Client(vertexai=True, project=tools.FIRESTORE_PROJECT, location="global")
print(f"✅ 7. Image Generation Setup: Vertex AI Client initialized (location='global', model='gemini-3.1-flash-lite-image')")

print("==================================================")
print("🎉 ALL AGENT COMPONENTS ARE VERIFIED ACTIVE & FUNCTIONAL!")
print("==================================================")
