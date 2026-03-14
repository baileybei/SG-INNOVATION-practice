"""Mock VLM implementation for development and testing.

Returns pre-baked JSON responses without making real API calls.
Supports multiple scenarios per scene to enable diverse testing.
"""

import json
import random
from typing import Optional

from src.vision_agent.llm.base import BaseVLM


# ─── FOOD scenarios ───────────────────────────────────────────────────────────

_FOOD_SCENARIOS = [
    # Scenario 0: Hainanese Chicken Rice (default)
    {
        "scene_type": "FOOD",
        "food_name": "Hainanese Chicken Rice, Clear Soup",
        "gi_level": "medium",
        "total_calories": 500.0,
        "confidence": 0.91,
    },
    # Scenario 1: Nasi Lemak (breakfast)
    {
        "scene_type": "FOOD",
        "food_name": "Nasi Lemak, Teh Tarik",
        "gi_level": "high",
        "total_calories": 509.0,
        "confidence": 0.88,
    },
    # Scenario 2: Char Kway Teow (supper)
    {
        "scene_type": "FOOD",
        "food_name": "Char Kway Teow",
        "gi_level": "high",
        "total_calories": 742.0,
        "confidence": 0.85,
    },
    # Scenario 3: Kaya Toast breakfast set
    {
        "scene_type": "FOOD",
        "food_name": "Kaya Toast, Half-Boiled Eggs, Kopi-O",
        "gi_level": "medium",
        "total_calories": 375.0,
        "confidence": 0.93,
    },
]

# ─── MEDICATION scenarios ─────────────────────────────────────────────────────

_MEDICATION_SCENARIOS = [
    # Scenario 0: Metformin (default)
    {
        "scene_type": "MEDICATION",
        "drug_name": "Metformin Hydrochloride",
        "dosage": "500mg",
        "frequency": "twice daily with meals (BD)",
        "route": "oral",
        "warnings": ["Do not crush or chew", "Take with food to reduce GI side effects"],
        "expiry_date": "2025-12",
        "confidence": 0.87,
    },
    # Scenario 1: Insulin pen
    {
        "scene_type": "MEDICATION",
        "drug_name": "Insulin Glargine (Lantus)",
        "dosage": "100 units/ml",
        "frequency": "once daily at bedtime (ON)",
        "route": "injection",
        "warnings": [
            "Keep refrigerated (2-8°C) before first use",
            "Do not shake",
            "Discard 28 days after first use",
        ],
        "expiry_date": "2025-06",
        "confidence": 0.92,
    },
    # Scenario 2: Amlodipine (hypertension)
    {
        "scene_type": "MEDICATION",
        "drug_name": "Amlodipine Besylate (Norvasc)",
        "dosage": "5mg",
        "frequency": "once daily (OD)",
        "route": "oral",
        "warnings": ["May cause ankle swelling", "Do not stop without consulting doctor"],
        "expiry_date": "2026-03",
        "confidence": 0.84,
    },
    # Scenario 3: Rosuvastatin
    {
        "scene_type": "MEDICATION",
        "drug_name": "Rosuvastatin Calcium (Crestor)",
        "dosage": "10mg",
        "frequency": "once daily at night (ON)",
        "route": "oral",
        "warnings": ["Report muscle pain or weakness immediately", "Avoid grapefruit juice"],
        "expiry_date": None,
        "ingredients": None,
        "confidence": 0.89,
    },
    # Scenario 4: Supplement with multiple ingredients (BioFinest Magnesium Complex)
    {
        "scene_type": "MEDICATION",
        "drug_name": "BioFinest Magnesium Complex",
        "dosage": "per 3 capsules",
        "frequency": None,
        "route": "oral",
        "warnings": None,
        "expiry_date": None,
        "ingredients": [
            {"name": "Magnesium (as Magnesium Glycinate)", "amount": "400mg"},
            {"name": "Vitamin B6 (as Pyridoxine HCl)", "amount": "5mg"},
            {"name": "Zinc (as Zinc Gluconate)", "amount": "10mg"},
        ],
        "confidence": 0.86,
    },
]

# ─── REPORT scenarios ─────────────────────────────────────────────────────────

_REPORT_SCENARIOS = [
    # Scenario 0: SGH blood test (default)
    {
        "scene_type": "REPORT",
        "report_type": "blood_test",
        "indicators": [
            {"name": "HbA1c", "value": "7.2", "unit": "%",
             "reference_range": "4.0-5.6", "is_abnormal": True},
            {"name": "Fasting Glucose", "value": "6.8", "unit": "mmol/L",
             "reference_range": "3.9-6.1", "is_abnormal": True},
            {"name": "Total Cholesterol", "value": "4.5", "unit": "mmol/L",
             "reference_range": "< 5.2", "is_abnormal": False},
            {"name": "LDL Cholesterol", "value": "2.8", "unit": "mmol/L",
             "reference_range": "< 2.6", "is_abnormal": True},
            {"name": "HDL Cholesterol", "value": "1.2", "unit": "mmol/L",
             "reference_range": "> 1.0", "is_abnormal": False},
        ],
        "report_date": "2024-01-15",
        "lab_name": "Singapore General Hospital",
        "confidence": 0.95,
    },
    # Scenario 1: Health screening (polyclinic)
    {
        "scene_type": "REPORT",
        "report_type": "health_screening",
        "indicators": [
            {"name": "BMI", "value": "26.4", "unit": "kg/m²",
             "reference_range": "18.5-22.9", "is_abnormal": True},
            {"name": "Blood Pressure", "value": "138/88", "unit": "mmHg",
             "reference_range": "< 130/80", "is_abnormal": True},
            {"name": "Random Blood Glucose", "value": "6.2", "unit": "mmol/L",
             "reference_range": "< 7.8", "is_abnormal": False},
            {"name": "Total Cholesterol", "value": "5.8", "unit": "mmol/L",
             "reference_range": "< 5.2", "is_abnormal": True},
        ],
        "report_date": "2024-03-20",
        "lab_name": "Bukit Batok Polyclinic",
        "confidence": 0.91,
    },
    # Scenario 2: Renal panel
    {
        "scene_type": "REPORT",
        "report_type": "renal_panel",
        "indicators": [
            {"name": "Creatinine", "value": "112", "unit": "μmol/L",
             "reference_range": "62-106", "is_abnormal": True},
            {"name": "eGFR", "value": "58", "unit": "mL/min/1.73m²",
             "reference_range": ">= 60", "is_abnormal": True},
            {"name": "Urea", "value": "7.2", "unit": "mmol/L",
             "reference_range": "2.5-7.8", "is_abnormal": False},
            {"name": "Potassium", "value": "4.1", "unit": "mmol/L",
             "reference_range": "3.5-5.1", "is_abnormal": False},
            {"name": "Sodium", "value": "139", "unit": "mmol/L",
             "reference_range": "136-145", "is_abnormal": False},
        ],
        "report_date": "2024-02-08",
        "lab_name": "National University Hospital",
        "confidence": 0.93,
    },
]

# ─── UNKNOWN scenarios ────────────────────────────────────────────────────────

_UNKNOWN_SCENARIOS = [
    {
        "scene_type": "UNKNOWN",
        "reason": "Image does not contain identifiable food, medication, or medical report.",
        "confidence": 0.82,
    },
    {
        "scene_type": "UNKNOWN",
        "reason": "Image appears to be a selfie or portrait. Please upload a food, medication, or medical report image.",
        "confidence": 0.90,
    },
    {
        "scene_type": "UNKNOWN",
        "reason": "Image quality is too low to identify content. Please take a clearer photo.",
        "confidence": 0.65,
    },
]

_ALL_SCENARIOS = {
    "FOOD": _FOOD_SCENARIOS,
    "MEDICATION": _MEDICATION_SCENARIOS,
    "REPORT": _REPORT_SCENARIOS,
    "UNKNOWN": _UNKNOWN_SCENARIOS,
}


class MockVLM(BaseVLM):
    """Deterministic mock VLM for dev/testing. No API calls made."""

    def __init__(
        self,
        forced_scene: Optional[str] = None,
        scenario_index: int = 0,
        random_scenario: bool = False,
    ) -> None:
        """
        Args:
            forced_scene: Always return this scene. If None, infer from prompt.
            scenario_index: Which scenario variant to return (0=default).
            random_scenario: If True, pick a random scenario each call.
        """
        self._forced_scene = forced_scene
        self._scenario_index = scenario_index
        self._random_scenario = random_scenario

    @property
    def model_name(self) -> str:
        return "mock-vlm-v1"

    def call(self, prompt: str, image_base64: str) -> str:  # noqa: ARG002
        scene = self._forced_scene or self._infer_scene(prompt)
        return self._get_response(scene)

    def call_multi(self, prompt: str, images_base64: list[str]) -> str:  # noqa: ARG002
        """Mock ignores images; behaviour identical to call()."""
        if not images_base64:
            from src.vision_agent.llm.base import VLMError
            raise VLMError("call_multi() requires at least one image.")
        scene = self._forced_scene or self._infer_scene(prompt)
        return self._get_response(scene)

    def _get_response(self, scene: str) -> str:
        scenarios = _ALL_SCENARIOS.get(scene, _ALL_SCENARIOS["UNKNOWN"])
        if self._random_scenario:
            data = random.choice(scenarios)
        else:
            idx = min(self._scenario_index, len(scenarios) - 1)
            data = scenarios[idx]
        return json.dumps(data)

    def _infer_scene(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "food" in prompt_lower or "meal" in prompt_lower or "nutrition" in prompt_lower:
            return "FOOD"
        if "medication" in prompt_lower or "drug" in prompt_lower or "prescription" in prompt_lower:
            return "MEDICATION"
        if "report" in prompt_lower or "lab" in prompt_lower or "blood" in prompt_lower:
            return "REPORT"
        return "UNKNOWN"

    @classmethod
    def food_scenarios(cls) -> list[str]:
        """Return all food scenario names for parametrized testing."""
        return [s["food_name"] for s in _FOOD_SCENARIOS]

    @classmethod
    def medication_scenarios(cls) -> list[str]:
        """Return all medication scenario names for parametrized testing."""
        return [s["drug_name"] for s in _MEDICATION_SCENARIOS]

    @classmethod
    def supplement_scenario_index(cls) -> int:
        """Return the index of the supplement (multi-ingredient) scenario."""
        for i, s in enumerate(_MEDICATION_SCENARIOS):
            if s.get("ingredients"):
                return i
        return -1

    @classmethod
    def scenario_count(cls, scene: str) -> int:
        """Return number of available scenarios for a scene."""
        return len(_ALL_SCENARIOS.get(scene, []))
