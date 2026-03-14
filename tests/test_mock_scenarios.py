"""Parametrized tests across all MockVLM scenarios.

Verifies that every mock scenario produces valid, schema-compliant output.
"""

import json
import pytest

from src.vision_agent.agent import VisionAgent
from src.vision_agent.llm.mock import MockVLM, _FOOD_SCENARIOS, _MEDICATION_SCENARIOS, _REPORT_SCENARIOS, _UNKNOWN_SCENARIOS
from src.vision_agent.schemas.outputs import FoodOutput, MedicationOutput, ReportOutput, UnknownOutput


# ─── Parametrized food scenarios ─────────────────────────────────────────────

@pytest.mark.parametrize("scenario_index,expected_dish", [
    (0, "Hainanese Chicken Rice"),
    (1, "Nasi Lemak"),
    (2, "Char Kway Teow"),
    (3, "Kaya Toast"),
])
def test_food_scenario_valid_schema(mock_image_path, scenario_index, expected_dish):
    agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD", scenario_index=scenario_index))
    result = agent.analyze(mock_image_path)
    assert result.is_food
    food = result.as_food
    assert food is not None
    assert expected_dish in food.food_name, f"Expected '{expected_dish}' in '{food.food_name}'"


@pytest.mark.parametrize("scenario_index", range(len(_FOOD_SCENARIOS)))
def test_food_has_required_fields(mock_image_path, scenario_index):
    """All food scenarios must have food_name, gi_level, and total_calories."""
    agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD", scenario_index=scenario_index))
    result = agent.analyze(mock_image_path)
    food = result.as_food
    assert food is not None
    assert len(food.food_name) > 0
    assert food.gi_level in ("high", "medium", "low")
    assert food.total_calories > 0


# ─── Parametrized medication scenarios ───────────────────────────────────────

@pytest.mark.parametrize("scenario_index,expected_drug", [
    (0, "Metformin Hydrochloride"),
    (1, "Insulin Glargine (Lantus)"),
    (2, "Amlodipine Besylate (Norvasc)"),
    (3, "Rosuvastatin Calcium (Crestor)"),
    (4, "BioFinest Magnesium Complex"),
])
def test_medication_scenario_valid_schema(mock_image_path, scenario_index, expected_drug):
    agent = VisionAgent(vlm=MockVLM(forced_scene="MEDICATION", scenario_index=scenario_index))
    result = agent.analyze(mock_image_path)
    assert result.is_medication
    med = result.as_medication
    assert med is not None
    assert med.drug_name == expected_drug


@pytest.mark.parametrize("scenario_index", range(len(_MEDICATION_SCENARIOS)))
def test_medication_has_dosage(mock_image_path, scenario_index):
    """All medication scenarios must have a dosage. Frequency is optional (supplements may omit it)."""
    agent = VisionAgent(vlm=MockVLM(forced_scene="MEDICATION", scenario_index=scenario_index))
    result = agent.analyze(mock_image_path)
    med = result.as_medication
    assert med is not None
    assert len(med.dosage) > 0


def test_supplement_scenario_has_ingredients(mock_image_path):
    """Supplement scenario (index 4) must have multi-ingredient list and no frequency."""
    supplement_idx = MockVLM.supplement_scenario_index()
    assert supplement_idx >= 0, "No supplement scenario found in mock data"
    agent = VisionAgent(vlm=MockVLM(forced_scene="MEDICATION", scenario_index=supplement_idx))
    result = agent.analyze(mock_image_path)
    med = result.as_medication
    assert med is not None
    assert med.ingredients is not None
    assert len(med.ingredients) > 1
    assert med.frequency is None


# ─── Parametrized report scenarios ───────────────────────────────────────────

@pytest.mark.parametrize("scenario_index,report_type", [
    (0, "blood_test"),
    (1, "health_screening"),
    (2, "renal_panel"),
])
def test_report_scenario_valid_schema(mock_image_path, scenario_index, report_type):
    agent = VisionAgent(vlm=MockVLM(forced_scene="REPORT", scenario_index=scenario_index))
    result = agent.analyze(mock_image_path)
    assert result.is_report
    report = result.as_report
    assert report is not None
    assert report.report_type == report_type


@pytest.mark.parametrize("scenario_index", range(len(_REPORT_SCENARIOS)))
def test_report_has_indicators(mock_image_path, scenario_index):
    agent = VisionAgent(vlm=MockVLM(forced_scene="REPORT", scenario_index=scenario_index))
    result = agent.analyze(mock_image_path)
    report = result.as_report
    assert report is not None
    assert len(report.indicators) > 0
    for ind in report.indicators:
        assert ind.name
        assert ind.value


@pytest.mark.parametrize("scenario_index", range(len(_REPORT_SCENARIOS)))
def test_report_has_abnormal_indicators(mock_image_path, scenario_index):
    """All mock report scenarios should have at least one abnormal indicator (chronic disease context)."""
    agent = VisionAgent(vlm=MockVLM(forced_scene="REPORT", scenario_index=scenario_index))
    result = agent.analyze(mock_image_path)
    report = result.as_report
    abnormal = [i for i in report.indicators if i.is_abnormal]
    assert len(abnormal) > 0, f"Scenario {scenario_index} has no abnormal indicators"


# ─── Unknown scenarios ────────────────────────────────────────────────────────

@pytest.mark.parametrize("scenario_index", range(len(_UNKNOWN_SCENARIOS)))
def test_unknown_scenarios_valid(mock_image_path, scenario_index):
    agent = VisionAgent(vlm=MockVLM(forced_scene="UNKNOWN", scenario_index=scenario_index))
    result = agent.analyze(mock_image_path)
    assert result.is_unknown
    assert result.structured_output is not None
    assert len(result.structured_output.reason) > 0


# ─── Scenario count helpers ───────────────────────────────────────────────────

def test_mock_vlm_scenario_counts():
    assert MockVLM.scenario_count("FOOD") == len(_FOOD_SCENARIOS)
    assert MockVLM.scenario_count("MEDICATION") == len(_MEDICATION_SCENARIOS)
    assert MockVLM.scenario_count("REPORT") == len(_REPORT_SCENARIOS)
    assert MockVLM.scenario_count("UNKNOWN") == len(_UNKNOWN_SCENARIOS)
    assert MockVLM.scenario_count("INVALID") == 0


def test_mock_vlm_food_scenarios_list():
    names = MockVLM.food_scenarios()
    assert any("Hainanese Chicken Rice" in n for n in names)
    assert any("Nasi Lemak" in n for n in names)
    assert len(names) == len(_FOOD_SCENARIOS)


def test_mock_vlm_medication_scenarios_list():
    names = MockVLM.medication_scenarios()
    assert "Metformin Hydrochloride" in names
    assert len(names) == len(_MEDICATION_SCENARIOS)


def test_mock_vlm_out_of_bounds_index_clamps(mock_image_path):
    """scenario_index > available scenarios should not raise, should clamp."""
    agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD", scenario_index=999))
    result = agent.analyze(mock_image_path)
    assert result.is_food  # Should return last scenario, not crash


def test_mock_vlm_random_scenario_returns_valid(mock_image_path):
    """random_scenario=True should still return valid schema."""
    import random
    random.seed(42)
    agent = VisionAgent(vlm=MockVLM(forced_scene="FOOD", random_scenario=True))
    for _ in range(5):
        result = agent.analyze(mock_image_path)
        assert result.is_food
        assert result.as_food is not None
