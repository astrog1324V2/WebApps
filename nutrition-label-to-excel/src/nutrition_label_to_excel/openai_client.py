from __future__ import annotations

import base64
import json
import os
from typing import Protocol

import httpx

from .logic import ExtractionValidationError, validate_extraction
from .models import NutritionLabelExtraction


RESPONSES_URL = "https://api.openai.com/v1/responses"

EXTRACTION_PROMPT = """You extract nutrition label data from a single food package photo.

Return JSON only and follow the schema exactly.

Rules:
- Read the serving size in grams from the label.
- If the label does not specify grams for the serving, set serving_grams to null and add a warning explaining that grams were not found.
- Extract values for calories, protein, carbs, fats, sugars, and fibre for the printed serving size.
- Use grams for all nutrient fields.
- If a nutrient is unreadable or missing, set it to null and add a warning.
- Ignore % daily value numbers and do not derive missing nutrients from them.
- serving_label_text should be the printed serving-size text exactly as seen on the label when possible.
- warnings should be short and actionable.
"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "serving_grams": {"type": ["number", "null"], "minimum": 0},
        "serving_label_text": {"type": "string"},
        "calories": {"type": ["number", "null"], "minimum": 0},
        "protein_g": {"type": ["number", "null"], "minimum": 0},
        "carbs_g": {"type": ["number", "null"], "minimum": 0},
        "fats_g": {"type": ["number", "null"], "minimum": 0},
        "sugars_g": {"type": ["number", "null"], "minimum": 0},
        "fibre_g": {"type": ["number", "null"], "minimum": 0},
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "serving_grams",
        "serving_label_text",
        "calories",
        "protein_g",
        "carbs_g",
        "fats_g",
        "sugars_g",
        "fibre_g",
        "warnings",
    ],
}


class LabelExtractor(Protocol):
    async def extract_label(self, image_bytes: bytes, content_type: str) -> NutritionLabelExtraction:
        """Extract macros from a nutrition label image."""


class OpenAIResponsesLabelExtractor:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self._client = client

    async def extract_label(self, image_bytes: bytes, content_type: str) -> NutritionLabelExtraction:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        payload = self._build_payload(image_bytes=image_bytes, content_type=content_type)
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=45.0)

        try:
            response = await client.post(
                RESPONSES_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            message = exc.response.text.strip() or "OpenAI request failed."
            raise RuntimeError(message) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("Unable to reach OpenAI.") from exc
        finally:
            if owns_client:
                await client.aclose()

        parsed = self._parse_response(response.json())
        try:
            extraction = NutritionLabelExtraction.model_validate(parsed)
            return validate_extraction(extraction)
        except ExtractionValidationError:
            raise
        except Exception as exc:
            if parsed.get("serving_grams") in (None, 0):
                raise ExtractionValidationError(
                    "Serving size in grams is required. The label must show grams for the serving."
                ) from exc
            raise RuntimeError("The label data could not be validated.") from exc

    def _build_payload(self, image_bytes: bytes, content_type: str) -> dict:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{content_type};base64,{encoded}"
        return {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": EXTRACTION_PROMPT,
                        },
                        {
                            "type": "input_image",
                            "image_url": data_url,
                            "detail": "low",
                        },
                    ],
                }
            ],
            "max_output_tokens": 500,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "nutrition_label_extraction",
                    "schema": SCHEMA,
                    "strict": True,
                }
            },
        }

    def _parse_response(self, response_json: dict) -> dict:
        if response_json.get("status") == "incomplete":
            raise RuntimeError("OpenAI returned an incomplete response.")

        output_text = response_json.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return json.loads(output_text)

        for item in response_json.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return json.loads(content["text"])
                if isinstance(content.get("text"), str):
                    return json.loads(content["text"])

        raise RuntimeError("OpenAI response did not include parseable JSON.")
