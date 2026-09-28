# 🐉 D&D Dungeon Master Agent

An interactive Tabletop RPG Dungeon Master agent built with the **Google Agent Development Kit (ADK)**, featuring **A2UI v0.8** rich card interfaces, **Imagen 3** visual scene generation, **Firestore** persistent character storage, **Memory Bank** cross-session memory, and **5e OpenSRD** rulebook integration.

![D&D Dungeon Master Demo](docs/demo.gif)

---

## 🛠️ Key Capabilities (Implemented in Code)

- **A2UI v0.8 Dynamic Cards**: Emits structured A2UI component surfaces (`A2uiSchemaManager`) rendered as interactive Character Sheets, Monster Cards, and Inventory blocks without code leaks.
- **5e Rulebook Lookup Tool (`search_5e_rules`)**: Queries 5e OpenSRD rules for spells (e.g., *Fireball*), monster stat blocks, magic items, and mechanics.
- **Dice Rolling Engine Tool (`roll_dice`)**: Evaluates virtual dice expressions (e.g., `1d20 + 4`, `2d6 + 3`) against Difficulty Class (DC) thresholds.
- **Imagen 3 Image Generation (`generate_fantasy_image`)**: Generates custom fantasy character portraits and location artwork using `imagen-3.0-generate-002`, persisting images to Google Cloud Storage (`GCS`).
- **Google Cloud Firestore Persistence**: Saves and retrieves character attributes, gender/sexuality choices, and campaign backstory in the `dnd_characters` Firestore collection.
- **Vertex AI Memory Bank**: Preserves player decisions and durable narrative facts across multi-turn sessions using `CallbackContext.add_session_to_memory()`.
- **OpenTelemetry Observability**: Emits telemetry traces to Google Cloud Trace for production monitoring (`GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`).

---

## 🏗️ Repository Architecture

```text
.
├── app/
│   ├── agent.py         # ADK Agent definition, callbacks, system prompts & A2UI wiring
│   ├── tools.py         # 5e rules, dice engine, Imagen image generation & Firestore persistence
│   └── a2ui_utils.py    # A2UI v0.8 schema manager & surface update callbacks
├── frontend/
│   ├── main.py          # FastAPI A2A proxy server authenticating with ADC
│   ├── requirements.txt # Proxy & A2A SDK dependencies
│   └── static/
│       └── index.html   # Medieval Fantasy Chat UI & native A2UI card renderer
├── agents-cli-manifest.yaml # Agent configuration manifest (agent_directory: app)
└── docs/
    └── demo.gif         # Loop recording of local/Cloud Run chat UI
```

---

## 🚀 Local Setup & Execution

### Prerequisites
- Python 3.10+
- `uv` or `pip`
- Google Cloud SDK (`gcloud`) authenticated with Application Default Credentials (`gcloud auth application-default login`).

### 1. Install Dependencies
```bash
# Install core agent dependencies
uv pip install -r requirements.txt

# Install frontend proxy dependencies
cd frontend
uv pip install -r requirements.txt
cd ..
```

### 2. Set Environment Variables
```bash
export GOOGLE_CLOUD_PROJECT="<YOUR_GCP_PROJECT_ID>"
export GOOGLE_CLOUD_LOCATION="us-east1"
export GOOGLE_GENAI_USE_VERTEXAI="true"
```

### 3. Test Agent Locally with ADK CLI
```bash
uv run agents-cli run --mode adk
```

### 4. Run Frontend Web App Locally
```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="<YOUR_DEPLOYED_REASONING_ENGINE_RESOURCE_NAME>"
export AGENT_DIRECTORY="app"
uv run python main.py
```
Open a browser and navigate to port `8080` on your local host to launch the D&D Dungeon Master chat interface.

---

## ☁️ Deployment

### Deploy Agent Engine to Vertex AI Agent Runtime
```bash
uv run agents-cli deploy \
  --no-confirm-project \
  --update-env-vars "GOOGLE_CLOUD_LOCATION=us-east1,GOOGLE_GENAI_USE_VERTEXAI=true"
```

### Deploy Frontend Web App to Google Cloud Run
```bash
cd frontend
gcloud run deploy dnd-dungeon-master-frontend \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars "AGENT_ENGINE_RESOURCE_NAME=<YOUR_REASONING_ENGINE_RESOURCE_NAME>,AGENT_DIRECTORY=app"
```

### IAM Permissions Required
- **Agent Service Account**: `roles/datastore.user` (Firestore), `roles/storage.objectAdmin` (GCS bucket).
- **Cloud Run Service Account**: `roles/aiplatform.user` (Vertex AI Agent Engine access).
