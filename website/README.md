# Electrolyte Intelligence

A FastAPI website for OEDB electrolyte exploration and dual-model ionic-conductivity prediction.

## Current state

- OEDB composition options and record exploration are connected to the repository dataset.
- Prediction API and UI are implemented.
- HGB-SVR and SMI-TED adapter interfaces are present.
- The actual trained model artifacts and exact inference adapters are not yet connected. The API reports this honestly rather than returning mock predictions.
- Prediction intervals are withheld until a separate calibration split has been evaluated.

## Dataset

By default, the app reads:

    ../data/raw/oedb_electrolytes_v2026_05_11.csv

This is the dataset version currently stored in this repository. Do not replace it with a newer OEDB version for model inference unless the training pipeline is revalidated against that version.

The conductivity target, row IDs and t-SNE coordinates are removed before any row is passed to a model adapter.

## Run locally on the IIT server

From the repository root:

    cd website
    source /home/anshuman/electrolyte/.venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Open http://SERVER_HOST:8000

API health: http://SERVER_HOST:8000/api/health
API docs: http://SERVER_HOST:8000/docs

## Model adapter contract

Each adapter module must export load_predictor(). The returned object must implement:

    def predict_record(self, record_without_target) -> float:
        ...

Return final conductivity in mS/cm. The adapter is responsible for the exact original feature engineering, preprocessing, inference and inverse target transformation.

### HGB-SVR

Implement app/adapters/hgb_svr.py using the exact saved HGB-SVR model and preprocessing pipeline from the research run. Do not refit or infer feature ordering.

### SMI-TED

Implement app/adapters/smited.py using the selected fine-tuned checkpoint and original SMI-TED inference code, tokenizer, molecular representation and 47-feature ordering.

Validate both adapters against the original standalone inference scripts on several supported formulations before using website predictions for research.

## Scientific limitations

- The current lookup domain only supports exact composition/concentration combinations in the supplied dataset.
- The displayed 298 K is an initial fixed interface assumption; it is not silently added to model features.
- Model predictions remain unavailable until real adapters are connected.
- No error interval is claimed until calibrated on a separate calibration set.
