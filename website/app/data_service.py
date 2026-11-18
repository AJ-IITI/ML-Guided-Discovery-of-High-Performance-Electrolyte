from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "raw" / "oedb_electrolytes_v2026_05_11.csv"

RENAME_MAP = {
    "ID": "id", "exp-ID": "exp_id", "Cation": "cation", "Anion": "anion",
    "Solvent": "solvent", "Concentration (mol/kg)": "concentration_mol_kg",
    "Ionic Conductivity (mS/cm)": "ionic_conductivity_ms_cm",
    "Viscosity (mPa·s)": "viscosity_mpa_s",
    "Cation's Diffusivity (m²/s)": "cation_diffusivity_m2_s",
    "Anion's Diffusivity (m²/s)": "anion_diffusivity_m2_s",
    "Solvent's Diffusivity (m²/s)": "solvent_diffusivity_m2_s",
    "Coordination (Cation←Anion)": "coordination_cation_anion",
    "Coordination (Cation ← Solvent)": "coordination_cation_solvent",
    "Density (g/cm³)": "density_g_cm3", "Anion SMILES": "anion_smiles",
    "Solvent SMILES": "solvent_smiles", "Anion PubChem CID": "anion_pubchem_cid",
    "Solvent PubChem CID": "solvent_pubchem_cid", "x": "tsne_x", "y": "tsne_y",
}
TARGET_COLUMNS = {"ionic_conductivity_ms_cm", "log_conductivity", "conductivity", "target"}

class DatasetError(RuntimeError): pass
class UnsupportedFormulation(ValueError): pass
class AmbiguousFormulation(ValueError): pass

def _dataset_path() -> Path:
    configured = os.getenv("OEDB_DATA_PATH")
    if not configured: return DEFAULT_DATA
    path = Path(configured).expanduser()
    return path if path.is_absolute() else (Path.cwd() / path).resolve()

@lru_cache(maxsize=1)
def get_dataset() -> pd.DataFrame:
    path = _dataset_path()
    if not path.exists():
        raise DatasetError(f"OEDB dataset not found at {path}. Set OEDB_DATA_PATH.")
    data = pd.read_csv(path, encoding="utf-8-sig").rename(columns=RENAME_MAP).copy()
    required = {"cation", "anion", "solvent", "concentration_mol_kg", "ionic_conductivity_ms_cm"}
    missing = required.difference(data.columns)
    if missing: raise DatasetError("Dataset is missing columns: " + ", ".join(sorted(missing)))
    for column in ("cation", "anion", "solvent"):
        data[column] = data[column].astype(str).str.strip()
    data["concentration_mol_kg"] = pd.to_numeric(data["concentration_mol_kg"], errors="coerce")
    data["ionic_conductivity_ms_cm"] = pd.to_numeric(data["ionic_conductivity_ms_cm"], errors="coerce")
    return data

def get_options() -> dict[str, Any]:
    data = get_dataset()
    return {
        "cations": sorted(data["cation"].dropna().unique().tolist()),
        "anions": sorted(data["anion"].dropna().unique().tolist()),
        "solvents": sorted(data["solvent"].dropna().unique().tolist()),
        "concentrations_mol_kg": sorted(data["concentration_mol_kg"].dropna().unique().astype(float).tolist()),
        "temperature_K": 298,
        "temperature_note": "Initial fixed interface assumption; not passed as a model feature unless the validated training pipeline requires it.",
        "dataset_rows": int(len(data)),
        "dataset_file": _dataset_path().name,
    }

def lookup_formulation(cation: str, anion: str, solvent: str, concentration_mol_kg: float) -> dict[str, Any]:
    data = get_dataset()
    concentration = float(concentration_mol_kg)
    mask = (
        data["cation"].eq(cation) & data["anion"].eq(anion) & data["solvent"].eq(solvent)
        & np.isclose(data["concentration_mol_kg"].to_numpy(dtype=float), concentration, rtol=0, atol=1e-8, equal_nan=False)
    )
    matches = data.loc[mask]
    if matches.empty:
        raise UnsupportedFormulation("This exact composition and concentration is not present in the current OEDB model lookup domain.")
    if len(matches) > 1:
        raise AmbiguousFormulation("Multiple OEDB rows match this composition. The lookup key must be disambiguated before inference.")
    row = matches.iloc[0].to_dict()
    # Leakage guard: the conductivity target, row identifiers and t-SNE coordinates never reach model adapters.
    for key in list(row):
        if key in TARGET_COLUMNS or key in {"id", "exp_id", "tsne_x", "tsne_y"}:
            row.pop(key, None)
    return row

def explore_rows(cation: str | None = None, anion: str | None = None, solvent: str | None = None, limit: int = 250) -> dict[str, Any]:
    data = get_dataset()
    filtered = data.copy()
    if cation: filtered = filtered[filtered["cation"] == cation]
    if anion: filtered = filtered[filtered["anion"] == anion]
    if solvent: filtered = filtered[filtered["solvent"] == solvent]
    columns = ["id", "cation", "anion", "solvent", "concentration_mol_kg", "ionic_conductivity_ms_cm", "viscosity_mpa_s", "density_g_cm3"]
    columns = [c for c in columns if c in filtered.columns]
    view = filtered[columns].head(max(1, min(int(limit), 1000)))
    return {
        "total_matching": int(len(filtered)),
        "returned": int(len(view)),
        "records": view.astype(object).where(pd.notna(view), None).to_dict(orient="records"),
        "concentration": filtered["concentration_mol_kg"].fillna(0).astype(float).tolist(),
        "conductivity": filtered["ionic_conductivity_ms_cm"].fillna(0).astype(float).tolist(),
    }
