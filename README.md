# SG INNOVATION - AI Health Platform

**English | [中文](README_CN.md)**

AI-powered health management platform for diabetic patients in Singapore. Built for the **SG INNOVATION** competition.

This repo contains two integrated modules:

| Module | Description |
|--------|-------------|
| **Vision Agent** (`src/vision_agent/`) | Analyzes food photos, medication images, and medical reports — converting images into structured JSON |
| **Health Companion Chatbot** (`chatbot/`) | Multi-turn conversational agent with intent routing, emotion awareness, and Vision Agent integration |

---

## Chatbot Quick Start

```bash
cd chatbot
pip install -r requirements.txt
cp ../.env .env   # uses same API keys as Vision Agent
python main.py

# CLI commands:
# 你好                          → text input
# image /path/to/food.jpg       → image input (triggers Vision Agent)
# image /path/photo.jpg 这是午饭  → image + text
# voice /path/to/audio.mp3      → voice input
# reset                         → clear conversation history
# quit                          → exit
```

### Chatbot Architecture

```
User Input (text / image / voice)
    |
input_node     ← detects images, calls Vision Agent, generates synthetic text
    |
triage_node    ← keyword pre-classification + LLM fallback (intent + emotion)
    |
policy_node    ← rule table: (intent, emotion) → strategy instruction
    |
    +-- Expert Agent    ← confidence-driven multi-turn: glucose/diet/medication
    +-- Companion Agent ← emotional support + crisis detection
    +-- Chitchat Agent  ← casual conversation
    +-- Task Forward    ← triggers Task Agent (Chayi)
    +-- Alert Forward   ← triggers Alert Agent (Julia)
```

---

## Vision Agent Architecture

### LangGraph Pipeline

```
[Image Input(s)]      One or more images (e.g. front+back of medicine box)
     |
[image_intake]        Receive image(s), validate each, convert to base64
     |
[scene_classifier]    Classify scene: FOOD / MEDICATION / REPORT / UNKNOWN
     |
     +-- FOOD       → [food_analyzer]       Identify dishes, estimate nutrition
     +-- MEDICATION → [medication_reader]    Extract drug name, dosage, frequency
     +-- REPORT     → [report_digitizer]     Extract lab indicators (HbA1c, glucose, etc.)
     +-- UNKNOWN    → [rejection_handler]    Reject non-target images
     |
[output_formatter]    Validate with Pydantic, format unified JSON output
     |
[Structured JSON Output]
```

### VLM Strategy (Model Layer)

```
Current (Development):
  Gemini 2.5 Flash  →  Vision + text analysis (temporary VLM)

Planned (Production):
  FoodAI (A*STAR/SMU) →  "Eyes" - SG food recognition (756 classes, 100+ local dishes)
  SEA-LION VL          →  "Brain" - Multilingual analysis & dietary advice
  SEA-LION 27B Text    →  Localized suggestions (Singlish, SG diabetes diet culture)
```

All VLM implementations share a common `BaseVLM` interface — swap models by changing one config line, no graph logic changes needed.

| Provider | Model | Status | Use Case |
|----------|-------|--------|----------|
| `mock` | MockVLM | Ready | Dev/testing, no API calls |
| `gemini` | Gemini 2.5 Flash | Ready | Temporary VLM for all 3 scenarios |
| `sealion` | Gemma-SEA-LION-v4-27B-IT | Ready | Text-only analysis & advice |
| `foodai` | FoodAI v5.0 | Pending | SG food recognition (applied, awaiting approval) |

## Quick Start

### 1. Install

```bash
git clone <repo-url>
cd SG_INNOVATION
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys:
#   GEMINI_API_KEY=your_key
#   SEALION_API_KEY=your_key
```

### 3. Run

```bash
# Analyze with Gemini (real VLM)
make run-gemini IMG=test_images/chicken_rice.jpg

# Analyze with mock (no API, for dev/testing)
make run IMG=test_images/sample.jpg

# Multi-image analysis (e.g. front + back of medicine box)
python -m src.vision_agent front.jpg back.jpg --provider gemini

# JSON output
make run-json IMG=test_images/sample.jpg PROVIDER=gemini

# Direct CLI
python -m src.vision_agent photo.jpg --provider gemini --json
```

### 4. Test

```bash
make test              # Run all tests (171 tests)
make coverage          # Tests + coverage report (99%+)
```

## Project Structure

```
SG_INNOVATION/
├── README.md
├── CLAUDE.md                        # AI dev guidelines
├── PRD-visionAgent.md               # Vision Agent product spec
├── PRD-chatbot.md                   # Chatbot product spec
├── Makefile
├── requirements.txt
├── .env.example
│
├── chatbot/                         # Health Companion Chatbot
│   ├── main.py                      # CLI entry point
│   ├── agents/                      # triage, policy, expert, companion, chitchat, forward
│   ├── graph/                       # LangGraph graph definition
│   ├── state/                       # ChatState (TypedDict)
│   ├── utils/                       # llm_factory, memory, meralion
│   ├── config/                      # settings
│   └── tests/                       # 29 tests
│
├── src/vision_agent/
│   ├── agent.py                     # Public API: VisionAgent.analyze()
│   ├── graph.py                     # LangGraph state graph definition
│   ├── state.py                     # Shared state (TypedDict)
│   ├── config.py                    # Settings from .env (Pydantic)
│   ├── logging_config.py
│   ├── __main__.py                  # CLI entry point
│   │
│   ├── llm/                         # VLM interface layer
│   │   ├── base.py                  # Abstract BaseVLM interface
│   │   ├── gemini.py                # Google Gemini 2.5 Flash (current)
│   │   ├── sealion.py               # SEA-LION text model
│   │   ├── mock.py                  # Mock for dev/testing
│   │   └── retry.py                 # Exponential backoff wrapper
│   │
│   ├── nodes/                       # Graph nodes (processing steps)
│   │   ├── image_intake.py          # Image loading & base64 conversion
│   │   ├── scene_classifier.py      # Scene classification (4 types)
│   │   ├── food_analyzer.py         # Food identification & nutrition
│   │   ├── medication_reader.py     # Drug info extraction
│   │   ├── report_digitizer.py      # Lab report digitization
│   │   ├── rejection_handler.py     # Non-target image handling
│   │   └── output_formatter.py      # Pydantic validation & formatting
│   │
│   ├── prompts/                     # SG-optimized prompt templates
│   │   ├── classifier.py            # Scene classification prompt
│   │   ├── food.py                  # 50+ SG dishes, HPB nutrition context
│   │   ├── medication.py            # SG drugs, HSA labels, BD/OD/TDS parsing
│   │   └── report.py               # MOH/HPB reference ranges, SG hospital formats
│   │
│   └── schemas/                     # Pydantic v2 output models
│       └── outputs.py               # FoodOutput, MedicationOutput, ReportOutput
│
├── tests/                           # 171 tests, 99%+ coverage
│   ├── conftest.py                  # Shared fixtures
│   ├── test_config.py
│   ├── test_graph.py
│   ├── test_nodes/
│   └── test_schemas/
│
└── test_images/                     # Test images (gitignored)
```

## Output Examples

### Food Analysis

```json
{
  "scene_type": "FOOD",
  "items": [
    {
      "name": "Hainanese Chicken Rice",
      "quantity": "1 plate",
      "nutrition": {
        "calories_kcal": 480.0,
        "carbs_g": 65.0,
        "protein_g": 28.0,
        "fat_g": 12.0,
        "sodium_mg": 820.0
      }
    }
  ],
  "total_calories_kcal": 480.0,
  "meal_type": "lunch",
  "confidence": 0.91
}
```

### Medication Verification

```json
{
  "scene_type": "MEDICATION",
  "drug_name": "Metformin Hydrochloride",
  "dosage": "500mg",
  "frequency": "twice daily with meals (BD)",
  "route": "oral",
  "warnings": ["Do not crush or chew", "Take with food to reduce GI side effects"],
  "confidence": 0.87
}
```

### Medical Report Digitization

```json
{
  "scene_type": "REPORT",
  "report_type": "blood_test",
  "indicators": [
    {"name": "HbA1c", "value": "7.2", "unit": "%", "reference_range": "4.0-5.6", "is_abnormal": true},
    {"name": "Fasting Glucose", "value": "6.8", "unit": "mmol/L", "reference_range": "3.9-6.1", "is_abnormal": true}
  ],
  "report_date": "2024-01-15",
  "lab_name": "Singapore General Hospital",
  "confidence": 0.95
}
```

## API Usage

```python
from src.vision_agent.agent import VisionAgent
from src.vision_agent.llm.gemini import GeminiVLM

# With Gemini (real vision)
agent = VisionAgent(vlm=GeminiVLM())
result = agent.analyze("meal_photo.jpg")

print(result.scene_type)        # "FOOD"
print(result.confidence)        # 0.91
print(result.as_food.items)     # [FoodItem(...), ...]

# Multi-image analysis (e.g. front + back of medicine box)
result = agent.analyze(["front.jpg", "back.jpg"])
print(result.is_multi_image)    # True
print(result.image_path)        # "front.jpg" (backward compatible)
print(result.image_paths)       # ["front.jpg", "back.jpg"]

# With Mock (dev/testing, no API calls)
agent = VisionAgent()
result = agent.analyze("any_image.jpg")
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VLM_PROVIDER` | No | `mock` | VLM provider: `mock`, `gemini`, `sealion` |
| `GEMINI_API_KEY` | When provider=gemini | - | Google Gemini API key |
| `SEALION_API_KEY` | When provider=sealion | - | SEA-LION API key |
| `LOG_LEVEL` | No | `INFO` | DEBUG, INFO, WARNING, ERROR |
| `VLM_MAX_RETRIES` | No | `3` | Max retry attempts for VLM calls |
| `VLM_RETRY_DELAY_S` | No | `1.0` | Initial retry delay (seconds) |
| `MAX_IMAGE_SIZE_MB` | No | `10.0` | Max image file size |

## Tech Stack

- **Framework**: LangGraph (state graph orchestration)
- **Language**: Python 3.10+
- **VLM**: Gemini 2.5 Flash (temp) / SEA-LION (planned)
- **Validation**: Pydantic v2
- **HTTP**: httpx
- **Testing**: pytest (171 tests, 99%+ coverage)

## License

SG INNOVATION Competition Project - AI Singapore
