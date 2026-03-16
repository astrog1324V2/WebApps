from nutrition_label_to_excel.logic import (
    ExtractionValidationError,
    format_calories,
    format_grams,
    scaled_field,
    sum_complete_ingredients,
)
from nutrition_label_to_excel.models import NutritionLabelExtraction


def test_scaled_field_doubles_values_for_200g_from_100g_serving() -> None:
    assert scaled_field(120, serving_grams=100, consumed_grams=200) == 240


def test_sum_complete_ingredients_combines_multiple_items() -> None:
    chicken = NutritionLabelExtraction(
        serving_grams=100,
        serving_label_text="Per 1/2 cup (100 g)",
        calories=120,
        protein_g=19,
        carbs_g=0,
        fats_g=5,
        sugars_g=0,
        fibre_g=0,
        warnings=[],
    )
    rice = NutritionLabelExtraction(
        serving_grams=50,
        serving_label_text="Per 1/4 cup (50 g)",
        calories=180,
        protein_g=4,
        carbs_g=40,
        fats_g=1,
        sugars_g=0,
        fibre_g=1,
        warnings=[],
    )

    totals = sum_complete_ingredients([chicken, rice], [200, 150])

    assert totals.calories == 780
    assert totals.protein_g == 50
    assert totals.carbs_g == 120
    assert totals.fats_g == 13
    assert totals.sugars_g == 0
    assert totals.fibre_g == 3


def test_sum_complete_ingredients_rejects_missing_macros() -> None:
    extraction = NutritionLabelExtraction(
        serving_grams=100,
        serving_label_text="100 g",
        calories=None,
        protein_g=10,
        carbs_g=10,
        fats_g=10,
        sugars_g=1,
        fibre_g=1,
        warnings=["Calories unreadable."],
    )

    try:
        sum_complete_ingredients([extraction], [100])
    except ExtractionValidationError as exc:
        assert str(exc) == "calories is missing."
    else:
        raise AssertionError("Expected missing calories to raise an error.")


def test_format_helpers_follow_excel_output_rules() -> None:
    assert format_calories(239.6) == "240"
    assert format_grams(38.0) == "38"
    assert format_grams(2.25) == "2.2"
