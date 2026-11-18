from __future__ import annotations
import importlib
import os
from typing import Any

class ModelRegistry:
    """Loads exact project-specific inference adapters; never guesses preprocessing."""
    def __init__(self) -> None:
        self.predictors: dict[str, Any | None] = {"hgb_svr": None, "smited": None}
        self.errors: dict[str, str | None] = {"hgb_svr": "Adapter has not been loaded.", "smited": "Adapter has not been loaded."}

    def load(self) -> None:
        self._load_one("hgb_svr", os.getenv("HGB_ADAPTER_MODULE", "app.adapters.hgb_svr"))
        self._load_one("smited", os.getenv("SMITED_ADAPTER_MODULE", "app.adapters.smited"))

    def _load_one(self, key: str, module_name: str) -> None:
        try:
            module = importlib.import_module(module_name)
            predictor = module.load_predictor()
            if not callable(getattr(predictor, "predict_record", None)):
                raise TypeError("Adapter must return an object with predict_record(record).")
            self.predictors[key] = predictor
            self.errors[key] = None
        except Exception as exc:
            self.predictors[key] = None
            self.errors[key] = f"{type(exc).__name__}: {exc}"

    def status(self) -> dict[str, Any]:
        versions = {
            "hgb_svr": os.getenv("HGB_MODEL_VERSION", "unversioned"),
            "smited": os.getenv("SMITED_MODEL_VERSION", "unversioned"),
        }
        return {name: {"loaded": self.predictors[name] is not None, "version": versions[name], "error": self.errors[name]} for name in ("hgb_svr", "smited")}

    def predict(self, record: dict[str, Any], selected: set[str] | None = None) -> dict[str, Any]:
        selected = selected or {"hgb_svr", "smited"}
        results: dict[str, Any] = {}
        for name in ("hgb_svr", "smited"):
            if name not in selected:
                continue
            predictor = self.predictors[name]
            if predictor is None:
                results[name] = {"status": "not_loaded", "message": self.errors[name], "conductivity_mS_cm": None, "interval_mS_cm": None}
                continue
            try:
                value = float(predictor.predict_record(record))
                if value < 0:
                    raise ValueError(f"Adapter returned negative conductivity ({value}); check inverse target transformation.")
                results[name] = {"status": "ok", "conductivity_mS_cm": value, "interval_mS_cm": None, "message": "Prediction interval not calibrated yet."}
            except Exception as exc:
                results[name] = {"status": "error", "message": f"{type(exc).__name__}: {exc}", "conductivity_mS_cm": None, "interval_mS_cm": None}
        return results

registry = ModelRegistry()
