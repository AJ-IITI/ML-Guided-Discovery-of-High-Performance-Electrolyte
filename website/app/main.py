from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.data_service import AmbiguousFormulation, DatasetError, UnsupportedFormulation, explore_rows, get_options, lookup_formulation
from app.model_registry import registry

load_dotenv()
APP_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = APP_DIR / "static"
app = FastAPI(title="Electrolyte Intelligence API", version="0.1.0", description="OEDB ionic conductivity prediction using HGB-SVR and SMI-TED.")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class PredictionRequest(BaseModel):
    cation: str = Field(min_length=1)
    anion: str = Field(min_length=1)
    solvent: str = Field(min_length=1)
    concentration_mol_kg: float = Field(gt=0)
    models: list[str] = Field(default_factory=lambda: ["hgb_svr", "smited"])

@app.on_event("startup")
def startup() -> None:
    registry.load()

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        options = get_options()
        dataset_status = {"loaded": True, "rows": options["dataset_rows"], "file": options["dataset_file"]}
    except Exception as exc:
        dataset_status = {"loaded": False, "error": str(exc)}
    return {"status": "ok" if dataset_status["loaded"] else "degraded", "dataset": dataset_status, "models": registry.status()}

@app.get("/api/options")
def options() -> dict[str, Any]:
    try:
        return get_options()
    except DatasetError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.get("/api/explore")
def explore(cation: str | None = None, anion: str | None = None, solvent: str | None = None, limit: int = Query(default=250, ge=1, le=1000)) -> dict[str, Any]:
    try:
        return explore_rows(cation, anion, solvent, limit)
    except DatasetError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.post("/api/predict")
def predict(request: PredictionRequest) -> dict[str, Any]:
    allowed = {"hgb_svr", "smited"}
    selected = set(request.models)
    if not selected or not selected.issubset(allowed):
        raise HTTPException(status_code=422, detail="models must contain hgb_svr, smited, or both.")
    try:
        record = lookup_formulation(request.cation, request.anion, request.solvent, request.concentration_mol_kg)
    except UnsupportedFormulation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AmbiguousFormulation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatasetError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    all_results = registry.predict(record)
    results = {name: all_results[name] for name in selected}
    ready = [value for value in results.values() if value["status"] == "ok"]
    if not ready:
        raise HTTPException(status_code=503, detail={"message": "The website is running, but trained model adapters are not connected yet.", "models": results})
    return {
        "formulation": {"cation": request.cation, "anion": request.anion, "solvent": request.solvent, "concentration_mol_kg": request.concentration_mol_kg, "temperature_K": 298},
        "predictions": results,
        "uncertainty_note": "Prediction intervals are withheld until calibrated on a separate calibration split.",
    }
