from fastapi.testclient import TestClient

from nutrition_label_to_excel.app import create_app
from nutrition_label_to_excel.logic import ExtractionValidationError
from nutrition_label_to_excel.models import NutritionLabelExtraction


class StubExtractor:
    def __init__(self, result: NutritionLabelExtraction | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def extract_label(self, image_bytes: bytes, content_type: str) -> NutritionLabelExtraction:
        if self.error:
            raise self.error
        assert image_bytes
        assert content_type.startswith("image/")
        assert self.result is not None
        return self.result


def sample_extraction() -> NutritionLabelExtraction:
    return NutritionLabelExtraction(
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


def test_extract_label_returns_normalized_payload() -> None:
    client = TestClient(create_app(extractor=StubExtractor(result=sample_extraction())))

    response = client.post(
        "/api/extract-label",
        files={"file": ("label.jpg", b"fake-image", "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["extraction"]["serving_grams"] == 100
    assert body["extraction"]["protein_g"] == 19


def test_extract_label_rejects_non_images() -> None:
    client = TestClient(create_app(extractor=StubExtractor(result=sample_extraction())))

    response = client.post(
        "/api/extract-label",
        files={"file": ("label.txt", b"not-an-image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Please upload an image file."


def test_extract_label_surfaces_missing_gram_serving() -> None:
    client = TestClient(
        create_app(
            extractor=StubExtractor(
                error=ExtractionValidationError(
                    "Serving size in grams is required. The label must show grams for the serving."
                )
            )
        )
    )

    response = client.post(
        "/api/extract-label",
        files={"file": ("label.jpg", b"fake-image", "image/jpeg")},
    )

    assert response.status_code == 422
    assert "Serving size in grams is required" in response.json()["detail"]
