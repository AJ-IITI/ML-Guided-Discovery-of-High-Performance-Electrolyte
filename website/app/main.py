import csv
import io
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import data_service as ds
from .model_registry import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
app = FastAPI(
    title="Electrolyte Atlas",
    version="1.0",
    description="OEDB simulation records and checkpoint-independent formulation validation.",
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(ds.DatasetError)
async def dataset_error(request, exc):
    return JSONResponse(
        status_code=503, content={"status": "DATASET_UNAVAILABLE", "detail": str(exc)}
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Avoid echoing untrusted input, including non-standard NaN/Infinity JSON.
    return JSONResponse(
        status_code=422,
        content={
            "status": "INVALID_INPUT",
            "detail": [
                {"field": str(e["loc"][-1]), "message": e["msg"]} for e in exc.errors()
            ],
        },
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "dataset": {"loaded": True, "rows": len(ds.dataset())},
        "models": statuses()["models"],
    }


@app.get("/api/models/status")
def statuses():
    return {"models": {k: p.status() for k, p in REGISTRY.items()}}


@app.get("/api/dataset/summary")
def summary():
    return ds.summary()


def filters(
    q: str = Query("", max_length=100),
    cation: str | None = None,
    anion: str | None = None,
    solvent: str | None = None,
    concentration: float | None = None,
    availability: Literal["reported", "missing"] | None = None,
):
    return {
        "q": q,
        "cation": cation,
        "anion": anion,
        "solvent": solvent,
        "concentration": concentration,
        "availability": availability,
    }


@app.get("/api/dataset/records")
def records(
    f: Annotated[dict, Depends(filters)],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    rows = list(ds.select(**f))
    return {
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "records": rows[offset : offset + limit],
    }


@app.get("/api/dataset/figures")
def figures(f: Annotated[dict, Depends(filters)]):
    return ds.figures(list(ds.select(**f)))


@app.get("/api/dataset/export.csv")
def export(f: Annotated[dict, Depends(filters)]):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=[*ds.FIELDS, "solvent_name"])
    writer.writeheader()
    writer.writerows(ds.select(**f))
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="oedb-filtered-records.csv"'
        },
    )


Positive = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]


class Formulation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cation: str
    anion: str
    solvent: str
    concentration_mol_kg: Positive
    viscosity_mpa_s: Positive
    coordination_cation_anion: Positive
    coordination_cation_solvent: Positive
    temperature_K: Literal[298] = 298
    models: list[Literal["hgb_svr", "smited"]] = Field(
        default_factory=lambda: list(REGISTRY), min_length=1, max_length=2
    )


@app.post(
    "/api/predict",
    responses={503: {"description": "Valid formulation; model weights not loaded"}},
)
def predict(form: Formulation):
    if len(form.models) != len(set(form.models)):
        raise HTTPException(422, "Choose each model at most once.")
    if (
        form.cation,
        form.anion,
        form.solvent,
        form.concentration_mol_kg,
    ) not in ds.domain():
        raise HTTPException(
            422,
            "Choose a cation, anion, solvent and molality combination present in this OEDB snapshot.",
        )
    inputs = form.model_dump(exclude={"models"})
    results = {key: REGISTRY[key].predict(inputs) for key in form.models}
    return JSONResponse(
        status_code=503,
        content={
            "status": "MODEL_NOT_LOADED",
            "input_valid": True,
            "formulation": inputs,
            "predictions": results,
            "comparison_mS_cm": None,
            "message": "Formulation validated. No trained model is loaded.",
        },
    )


NAV = [
    ("home", "/", "Home"),
    ("predict", "/predict", "Predict"),
    ("explore", "/explore", "Explore"),
    ("models", "/models", "Models"),
]


def page(key):
    nav = "".join(
        f'<a href="{url}"'
        + (' aria-current="page"' if key == k else "")
        + f">{title}</a>"
        for k, url, title in NAV
    )
    shell = (STATIC / "index.html").read_text()
    return HTMLResponse(
        shell.replace("{{nav}}", nav)
        .replace("{{page}}", key)
        .replace("{{title}}", key.title())
        .replace("{{body}}", (STATIC / "pages" / f"{key}.html").read_text())
    )


@app.get("/", include_in_schema=False)
def home():
    return page("home")


@app.get("/predict", include_in_schema=False)
def predict_page():
    return page("predict")


@app.get("/explore", include_in_schema=False)
def explore_page():
    return page("explore")


@app.get("/models", include_in_schema=False)
def models_page():
    return page("models")
