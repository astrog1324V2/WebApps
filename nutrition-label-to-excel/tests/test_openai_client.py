import asyncio
import json

import httpx

from nutrition_label_to_excel.openai_client import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    RETRY_MAX_OUTPUT_TOKENS,
    OpenAIResponsesLabelExtractor,
)


def test_extractor_retries_when_openai_hits_max_output_tokens() -> None:
    seen_max_tokens = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        seen_max_tokens.append(payload["max_output_tokens"])
        if len(seen_max_tokens) == 1:
            return httpx.Response(
                200,
                json={
                    "status": "incomplete",
                    "incomplete_details": {"reason": "max_output_tokens"},
                    "output": [],
                },
            )

        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output_text": json.dumps(
                    {
                        "serving_grams": 100,
                        "serving_label_text": "Per 1/2 cup (100 g)",
                        "calories": 120,
                        "protein_g": 19,
                        "carbs_g": 0,
                        "fats_g": 5,
                        "sugars_g": 0,
                        "fibre_g": 0,
                        "warnings": [],
                    }
                ),
            },
        )

    async def run_test() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        extractor = OpenAIResponsesLabelExtractor(api_key="test-key", client=client)
        try:
            extraction = await extractor.extract_label(b"fake-image", "image/jpeg")
        finally:
            await client.aclose()

        assert extraction.serving_grams == 100
        assert seen_max_tokens == [DEFAULT_MAX_OUTPUT_TOKENS, RETRY_MAX_OUTPUT_TOKENS]

    asyncio.run(run_test())


def test_extractor_surfaces_incomplete_reason_after_retry() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output": [],
            },
        )

    async def run_test() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        extractor = OpenAIResponsesLabelExtractor(api_key="test-key", client=client)
        try:
            try:
                await extractor.extract_label(b"fake-image", "image/jpeg")
            except RuntimeError as exc:
                assert str(exc) == "OpenAI returned an incomplete response (max_output_tokens)."
            else:
                raise AssertionError("Expected incomplete response to raise.")
        finally:
            await client.aclose()

    asyncio.run(run_test())
