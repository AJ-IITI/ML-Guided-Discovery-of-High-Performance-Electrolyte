"""Adapters consume validated physical inputs, never an OEDB target or whole row."""
from typing import Protocol, Any

class Predictor(Protocol):
    key: str
    def status(self) -> dict: ...
    def predict(self, formulation: dict[str, Any]) -> dict: ...

class UnloadedPredictor:
    key: str
    name: str

    def status(self):
        return {"model":self.name,"status":"MODEL_NOT_LOADED","loaded":False}

    def predict(self, formulation):
        return {**self.status(),"conductivity_mS_cm":None,"interval_mS_cm":None}
