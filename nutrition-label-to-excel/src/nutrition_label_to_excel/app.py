from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .logic import ExtractionValidationError
from .models import ErrorResponse, ExtractionResponse
from .openai_client import LabelExtractor, OpenAIResponsesLabelExtractor


STATIC_DIR = Path(__file__).with_name("static")
load_dotenv()


def create_app(extractor: LabelExtractor | None = None) -> FastAPI:
    app = FastAPI(title="Nutrition Label To Excel")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.extractor = extractor or OpenAIResponsesLabelExtractor()
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/api/extract-label",
        response_model=ExtractionResponse,
        responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )
    async def extract_label(file: UploadFile = File(...)) -> ExtractionResponse:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Please upload an image file.")

        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="The uploaded image is empty.")

        try:
            extraction = await app.state.extractor.extract_label(image_bytes, file.content_type)
        except ExtractionValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return ExtractionResponse(extraction=extraction)

    return app


app = create_app()
