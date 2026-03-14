"""Pydantic v2 output schemas for each scene type."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SceneType(str, Enum):
    FOOD = "FOOD"
    MEDICATION = "MEDICATION"
    REPORT = "REPORT"
    UNKNOWN = "UNKNOWN"


# ─── Food ────────────────────────────────────────────────────────────────────

class FoodOutput(BaseModel):
    scene_type: SceneType = SceneType.FOOD
    food_name: str                                  # comma-separated if multiple items
    gi_level: str                                   # high / medium / low
    total_calories: float                           # kcal
    confidence: float = Field(ge=0.0, le=1.0)


# ─── Medication ───────────────────────────────────────────────────────────────

class Ingredient(BaseModel):
    name: str    # e.g. "Magnesium (as Magnesium Glycinate)"
    amount: str  # e.g. "400mg", "5mcg"


class MedicationOutput(BaseModel):
    scene_type: SceneType = SceneType.MEDICATION
    drug_name: str
    dosage: str
    frequency: Optional[str] = None       # may be absent on supplement labels
    route: Optional[str] = None           # oral / injection / topical
    warnings: Optional[List[str]] = None
    expiry_date: Optional[str] = None
    ingredients: Optional[List[Ingredient]] = None  # supplement multi-ingredient list
    confidence: float = Field(ge=0.0, le=1.0)


# ─── Medical Report ───────────────────────────────────────────────────────────

class ReportIndicator(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: bool = False


class ReportOutput(BaseModel):
    scene_type: SceneType = SceneType.REPORT
    report_type: str                   # blood_test / urine_test / imaging / etc.
    indicators: List[ReportIndicator]
    report_date: Optional[str] = None
    lab_name: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


# ─── Unknown / Rejected ───────────────────────────────────────────────────────

class UnknownOutput(BaseModel):
    scene_type: SceneType = SceneType.UNKNOWN
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
