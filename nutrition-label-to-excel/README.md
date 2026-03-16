# nutrition-label-to-excel

Phone-friendly FastAPI app for extracting nutrition facts from label photos, scaling them by grams consumed, combining multiple ingredients into one meal total, and copying a tab-separated row for Excel.

## Features

- Take or upload nutrition label photos from your phone
- Extract calories, protein, carbs, fats, sugars, fibre, and serving grams with OpenAI vision
- Edit extracted values before using them
- Add multiple ingredients to a temporary meal builder
- Copy a single TSV row in this order:

  `Calories	Protein	Carbs	Fats	Sugars	Fibre	Time`

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
Copy-Item .env.example .env
python -m uvicorn nutrition_label_to_excel.app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) on your phone or desktop browser.

## Notes

- The backend requires `OPENAI_API_KEY`.
- v1 expects the label to include a serving size in grams.
- `Time` is generated in the browser so it matches the device you are using.
