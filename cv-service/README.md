# PerX CV Service

Standalone FastAPI microservice for five vision tasks. All pipelines work **out of the box** with pip-installable libraries — no user-provided model weights required.

## Tasks

| Task | What it does | Technique | Limitations |
|------|--------------|-----------|-------------|
| `lifestyle` | Maps image to PerX lifestyle segments | Dominant colors, HSV stats, heuristic scoring | Not a trained classifier; best for clear color/scene cues |
| `receipt` | Extracts merchant, amounts, line items | Bright-region detection + OCR + regex parsing | Needs readable text; Tesseract improves accuracy |
| `ocr` | General text extraction | Tesseract OCR with OpenCV preprocess | Without Tesseract, returns text-region hints only |
| `catalog_tag` | Suggests perk category/tags | Color heuristics + OCR keyword matching | Keyword list is finite; no product recognition model |
| `visual_search` | Similarity-ready embedding | Normalized RGB histogram + phash/dhash/ahash | `matches` are hash-derived placeholders until a catalog index is added |

## Quick start

```bash
cd cv-service
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

Health check: `GET http://localhost:8010/health`

Analyze:

```bash
curl -X POST http://localhost:8010/analyze \
  -H "Content-Type: application/json" \
  -d '{"task":"lifestyle","image_base64":"<base64>"}'
```

## Optional: Tesseract (full OCR)

The service starts without Tesseract. For real text on `ocr` and `receipt`:

- **Debian/Ubuntu**: `sudo apt install tesseract-ocr tesseract-ocr-eng`
- **macOS**: `brew install tesseract`
- **Windows**: install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and ensure `tesseract` is on `PATH`

Docker builds include Tesseract automatically.

## Optional: custom model overrides

See [`models/README.md`](models/README.md). Place weights under `models/` and activate `manifest.yaml` to override paths in the future. Built-in heuristics always run today.

## Tests

```bash
cd cv-service
pip install -r requirements.txt
pytest -q
```

Tests generate synthetic images with NumPy/PIL — no fixture files required.

## Docker

```bash
docker build -t perx-cv-service .
docker run --rm -p 8010:8010 perx-cv-service
```

Or via compose from `infra/`:

```bash
docker compose up --build cv-service
```

## Backend integration

Set on the backend:

- `CV_ENABLED=true`
- `CV_SERVICE_URL=http://localhost:8010` (or `http://cv-service:8010` in compose)

Backend `POST /api/v1/vision/jobs` forwards to cv-service `/analyze`.
