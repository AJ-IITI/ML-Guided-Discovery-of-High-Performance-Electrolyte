"""Explore the repository's MD snapshot. No model features or imputation here."""
import csv
import math
import os
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from statistics import median

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data/raw/oedb_electrolytes_v2026_05_11.csv"
TARGET = "ionic_conductivity_ms_cm"
CONC = "concentration_mol_kg"
FIELDS = {
    "id": "ID", "cation": "Cation", "anion": "Anion", "solvent": "Solvent",
    CONC: "Concentration (mol/kg)", TARGET: "Ionic Conductivity (mS/cm)",
    "viscosity_mpa_s": "Viscosity (mPa·s)", "coordination_cation_anion": "Coordination (Cation←Anion)",
    "coordination_cation_solvent": "Coordination (Cation ← Solvent)", "experimental_reference": "exp-ID"
}
# Display labels for this snapshot; codes defining the supported domain come from the CSV.
SOLVENT_NAMES = {
    'AN':'Acetonitrile','Ac':'Acetone','Ac2O':'Acetic anhydride','BC':'trans-2,3-Butylene carbonate',
    'DEC':'Diethyl carbonate','DMC':'Dimethyl carbonate','DMI':'1,3-Dimethyl-2-imidazolidinone',
    'DMSO':'Dimethyl sulfoxide','EA':'Ethyl acetate','EB':'Ethyl butyrate','EC':'Ethylene carbonate',
    'EMC':'Ethyl methyl carbonate','EP':'Ethyl propionate','FAN':'Fluoroacetonitrile','FEA':'2-Fluoroethyl acetate',
    'FEC':'Fluoroethylene carbonate','FEMC':'Methyl 2,2,2-trifluoroethyl carbonate','GBL':'Gamma-butyrolactone',
    'GN':'Glutaronitrile','MA':'Methyl acetoacetate','MB':'Methyl butyrate','MP':'Methyl pyruvate',
    'PC':'Propylene carbonate','SN':'Succinonitrile','TEP':'Triethyl phosphate','TMP':'Trimethyl phosphate'
}
class DatasetError(Exception):
    pass

@lru_cache(maxsize=1)
def dataset():
    path = Path(os.environ.get("OEDB_DATA_PATH", DEFAULT_DATA))
    rows = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if set(FIELDS.values()) - set(reader.fieldnames or ()):
                raise DatasetError("Dataset schema does not match the OEDB snapshot.")
            for raw in reader:
                r = {k: raw[v].strip() for k,v in FIELDS.items()}
                r["id"] = int(r["id"])
                for key in (CONC, TARGET, "viscosity_mpa_s","coordination_cation_anion","coordination_cation_solvent"):
                    r[key] = None if key == TARGET and not r[key] else float(r[key])
                    if r[key] is not None and not math.isfinite(r[key]):
                        raise DatasetError("Non-finite value in source dataset.")
                r["experimental_reference"] = r["experimental_reference"] or None
                r["solvent_name"] = SOLVENT_NAMES.get(r["solvent"], r["solvent"])
                rows.append(r)
    except (OSError, ValueError, KeyError) as exc:
        raise DatasetError("Cannot read the OEDB snapshot. Check OEDB_DATA_PATH.") from exc
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise DatasetError("Empty snapshot or duplicate source IDs.")
    return tuple(sorted(rows,key=lambda r:r['id']))

@lru_cache(maxsize=1)
def domain():
    return {(r["cation"],r["anion"],r["solvent"],r[CONC]) for r in dataset()}

def summary():
    rows=dataset()
    labels=[r[TARGET] for r in rows if r[TARGET] is not None]
    choices={k:sorted({r[k] for r in rows}) for k in ('cation','anion','solvent',CONC)}
    return dict(rows=len(rows),labelled=len(labels),missing=len(rows)-len(labels),
                experimental_references=sum(r['experimental_reference'] is not None for r in rows),
                median_conductivity=median(labels) if labels else None,temperature_K=298,
                source='OEDB molecular dynamics',snapshot='2026-05-11',choices=choices,
                solvent_names={s:SOLVENT_NAMES.get(s,s) for s in choices['solvent']},
                salt_pairs=len({k[:2] for k in domain()}),systems=len({k[:3] for k in domain()}))

def select(q='',cation=None,anion=None,solvent=None,availability=None,concentration=None):
    words=q.strip().casefold().split()
    for r in dataset():
        if any(v is not None and r[k]!=v for k,v in (('cation',cation),('anion',anion),('solvent',solvent),(CONC,concentration))):
            continue
        if availability=='reported' and r[TARGET] is None or availability=='missing' and r[TARGET] is not None:
            continue
        if words:
            hay=' '.join(str(r[k] or '') for k in ('id','cation','anion','solvent','solvent_name','experimental_reference')).casefold()
            if not all(w in hay for w in words): continue
        yield r

def figures(rows):
    # Counts are over every filtered record, not the visible table page.
    valid=[r for r in rows if r[TARGET] is not None]
    bins=Counter(); trend=defaultdict(list); sol=defaultdict(list)
    for r in valid:
        y=r[TARGET]
        # Zero is distinct from a missing result (no zeros in the pinned snapshot).
        if y>0: bins[math.floor(math.log10(y))]+=1
        trend[r['cation'],r[CONC]].append(y)
        sol[r['solvent']].append(y)
    return dict(total=len(rows),n=len(valid),missing=len(rows)-len(valid),
        nonpositive=sum(r[TARGET]<=0 for r in valid),
        histogram=[dict(low=10.**e,high=10.**(e+1),count=bins[e]) for e in range(min(bins),max(bins)+1)] if bins else [],
        trend=[dict(cation=c,x=x,median=median(v),n=len(v)) for (c,x),v in sorted(trend.items())],
        solvents=sorted([dict(code=s,name=SOLVENT_NAMES.get(s,s),median=median(v),n=len(v)) for s,v in sol.items()],key=lambda x:(-x['median'],x['code'])))
