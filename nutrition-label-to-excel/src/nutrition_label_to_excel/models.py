from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class NutritionLabelExtraction(BaseModel):
    serving_grams: float = Field(gt=0)
    serving_label_text: str = Field(min_length=1)
    calories: Optional[float] = Field(default=None, ge=0)
    protein_g: Optional[float] = Field(default=None, ge=0)
    carbs_g: Optional[float] = Field(default=None, ge=0)
    fats_g: Optional[float] = Field(default=None, ge=0)
    sugars_g: Optional[float] = Field(default=None, ge=0)
    fibre_g: Optional[float] = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("serving_label_text")
    @classmethod
    def strip_serving_label_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("serving_label_text must not be blank")
        return text

    @field_validator("warnings", mode="before")
    @classmethod
    def normalize_warnings(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("warnings must be a list of strings")


class ExtractionResponse(BaseModel):
    extraction: NutritionLabelExtraction


class ErrorResponse(BaseModel):
    detail: str
