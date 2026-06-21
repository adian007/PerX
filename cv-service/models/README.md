# CV model assets (optional override)

The cv-service runs **out of the box** with built-in heuristics (OpenCV, Pillow, imagehash, optional Tesseract). You do **not** need to upload anything here for the service to work.

Use this folder only when you want to **override** a pipeline with custom ONNX/Torch weights in the future.

## Expected layout (optional)

```
cv-service/models/
├── manifest.yaml              # optional; enables custom weight paths
├── lifestyle/
│   ├── model.onnx
│   └── labels.txt
├── receipt/
│   ├── model.onnx
│   └── vocab.json
├── ocr/
│   ├── model.onnx
│   └── charset.txt
├── catalog_tag/
│   ├── model.onnx
│   └── tags.json
├── visual_search/
│   ├── encoder.onnx
│   └── index/
│       ├── embeddings.npy
│       └── item_ids.json
└── fixtures/                  # optional sample images for manual testing
```

Supported weight formats: `.onnx`, `.pt`, `.pth`. Custom inference helpers can live next to each task folder and be referenced from `manifest.yaml`.

## manifest.yaml (optional)

Uncomment and adjust paths in `manifest.yaml` when custom weights are available. Until then, pipelines ignore this file and use built-in techniques.

## Pipeline mapping

| Task | Built-in technique | Typical output |
|------|-------------------|----------------|
| `lifestyle` | Color/scene heuristics | `primary_label`, `confidence`, `secondary_labels` |
| `receipt` | Receipt region + OCR + regex parse | `merchant`, `total_cents`, `line_items` |
| `ocr` | Tesseract (fallback: OpenCV text-region hint) | `text`, `blocks`, `ocr_available` |
| `catalog_tag` | Color + OCR keyword heuristics | `tags`, `category_hint`, `score` |
| `visual_search` | RGB histogram + perceptual hashes | `embedding`, `query_embedding_hash`, `matches` |

## System dependencies

- **Docker image** includes Tesseract for full OCR.
- **Local dev without Docker**: install Tesseract for best OCR (`apt install tesseract-ocr` on Debian/Ubuntu). The service starts without it and falls back to OpenCV heuristics.

## After adding custom weights

1. Drop files under `cv-service/models/` using the structure above.
2. Activate `manifest.yaml`.
3. Restart cv-service: `docker compose up --build` from `infra/`, or `uvicorn app.main:app --port 8010` from `cv-service/`.
4. Set backend `CV_ENABLED=true` and `CV_SERVICE_URL=http://localhost:8010`.
