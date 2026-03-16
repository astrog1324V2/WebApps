from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import NutritionLabelExtraction


MACRO_FIELDS = (
    "calories",
    "protein_g",
    "carbs_g",
    "fats_g",
    "sugars_g",
    "fibre_g",
)


class ExtractionValidationError(ValueError):
    """Raised when the extracted nutrition payload cannot be used."""


@dataclass(slots=True)
class IngredientTotals:
    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fats_g: float = 0.0
    sugars_g: float = 0.0
    fibre_g: float = 0.0


def validate_extraction(extraction: NutritionLabelExtraction) -> NutritionLabelExtraction:
    if extraction.serving_grams <= 0:
        raise ExtractionValidationError("Serving size in grams is required.")
    return extraction


def scaled_field(value: Optional[float], serving_grams: float, consumed_grams: float) -> Optional[float]:
    if value is None:
        return None
    if serving_grams <= 0 or consumed_grams < 0:
        raise ValueError("Invalid gram values.")
    return value * (consumed_grams / serving_grams)


def sum_complete_ingredients(
    ingredients: list[NutritionLabelExtraction],
    consumed_grams: list[float],
) -> IngredientTotals:
    totals = IngredientTotals()
    for extraction, grams in zip(ingredients, consumed_grams, strict=True):
        validate_extraction(extraction)
        for field_name in MACRO_FIELDS:
            value = getattr(extraction, field_name)
            if value is None:
                raise ExtractionValidationError(f"{field_name} is missing.")
            scaled_value = scaled_field(value, extraction.serving_grams, grams)
            setattr(totals, field_name, getattr(totals, field_name) + (scaled_value or 0.0))
    return totals


def format_calories(value: float) -> str:
    return str(int(round(value)))


def format_grams(value: float) -> str:
    rounded = round(value, 1)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.1f}"
