"""Phase 1 acceptance tests. The independent oracle is the pinned raw CSV, not the API."""

import csv
import io
import json
import math
import unittest
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from statistics import median

from app.main import app
from fastapi.testclient import TestClient

RAW = Path(__file__).resolve().parents[2] / "data/raw/oedb_electrolytes_v2026_05_11.csv"
Y = "Ionic Conductivity (mS/cm)"
C = "Concentration (mol/kg)"


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class Portal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        with RAW.open(encoding="utf-8-sig", newline="") as f:
            cls.raw = list(csv.DictReader(f))
        r = cls.raw[0]
        cls.form = {
            "cation": r["Cation"],
            "anion": r["Anion"],
            "solvent": r["Solvent"],
            "concentration_mol_kg": float(r[C]),
            "viscosity_mpa_s": float(r["Viscosity (mPa·s)"]),
            "coordination_cation_anion": float(r["Coordination (Cation←Anion)"]),
            "coordination_cation_solvent": float(r["Coordination (Cation ← Solvent)"]),
        }

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def get(self, path, **params):
        res = self.client.get(path, params=params)
        self.assertEqual(res.status_code, 200, res.text[:300])
        return res.json()

    def test_pages_navigation_and_assets(self):
        for path in ("/", "/predict", "/explore", "/models"):
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertEqual(res.status_code, 200)
                self.assertNotIn("{{", res.text)
                d = Document(res.text)
                self.assertEqual(sum(t == "h1" for t, _ in d.tags), 1)
                self.assertEqual(
                    [
                        a.get("href")
                        for t, a in d.tags
                        if a.get("aria-current") == "page"
                    ],
                    [path],
                )
                self.assertTrue(any(a.get("name") == "viewport" for _, a in d.tags))
        for filename in (
            "styles.css",
            "app.js",
            "ui.js",
            "charts.js",
            "explore.js",
            "predict.js",
            "mark.svg",
        ):
            self.assertEqual(self.client.get("/static/" + filename).status_code, 200)
        d = Document(self.client.get("/predict").text)
        self.assertEqual(
            {
                a["name"]
                for t, a in d.tags
                if t in ("input", "select") and "required" in a
            },
            set(self.form),
        )

    def test_health_and_schema_with_unloaded_models(self):
        health = self.get("/api/health")
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["dataset"]["rows"], len(self.raw))
        status = self.get("/api/models/status")["models"]
        self.assertEqual(set(status), {"hgb_svr", "smited"})
        self.assertTrue(
            all(
                not s["loaded"] and s["status"] == "MODEL_NOT_LOADED"
                for s in status.values()
            )
        )
        spec = self.get("/openapi.json")
        self.assertIn("post", spec["paths"]["/api/predict"])

    def test_summary_matches_snapshot(self):
        s = self.get("/api/dataset/summary")
        self.assertEqual((s["rows"], s["labelled"], s["missing"]), (5616, 5595, 21))
        self.assertEqual(s["labelled"], sum(bool(r[Y]) for r in self.raw))
        self.assertEqual(
            s["experimental_references"], sum(bool(r["exp-ID"]) for r in self.raw)
        )
        self.assertEqual(
            s["systems"],
            len({(r["Cation"], r["Anion"], r["Solvent"]) for r in self.raw}),
        )
        for field, raw_name in [
            ("cation", "Cation"),
            ("anion", "Anion"),
            ("solvent", "Solvent"),
        ]:
            self.assertEqual(set(s["choices"][field]), {r[raw_name] for r in self.raw})
        self.assertEqual(
            set(s["choices"]["concentration_mol_kg"]), {float(r[C]) for r in self.raw}
        )

    def test_pagination_search_export_and_solvent_labels(self):
        params = {
            "cation": "Li",
            "anion": "PF6",
            "q": "ethylene carbonate",
            "solvent": "EC",
        }
        expected = sorted(
            int(r["ID"])
            for r in self.raw
            if (r["Cation"], r["Anion"], r["Solvent"]) == ("Li", "PF6", "EC")
        )
        self.assertEqual(len(expected), 8)
        first = self.get("/api/dataset/records", **params, limit=3)
        second = self.get("/api/dataset/records", **params, limit=3, offset=3)
        self.assertEqual(first["total"], 8)
        self.assertEqual(
            [r["id"] for r in first["records"] + second["records"]], expected[:6]
        )
        out = self.client.get("/api/dataset/export.csv", params=params)
        self.assertEqual(out.status_code, 200)
        exported = list(csv.DictReader(io.StringIO(out.text)))
        self.assertEqual([int(r["id"]) for r in exported], expected)
        self.assertTrue(
            all(r["solvent_name"] == "Ethylene carbonate" for r in exported)
        )
        self.assertEqual(
            self.get("/api/dataset/records", q="not-an-oedb-record")["total"], 0
        )

    def test_full_and_filtered_chart_values_against_csv(self):
        for params in (
            {},
            {"cation": "Li", "anion": "PF6", "solvent": "EC"},
            {"concentration": 1.5},
        ):
            with self.subTest(params=params):
                r0 = [
                    r
                    for r in self.raw
                    if all(
                        (float(r[C]) if k == "concentration" else r[k.title()]) == v
                        for k, v in params.items()
                    )
                ]
                labels = [r for r in r0 if r[Y]]
                f = self.get("/api/dataset/figures", **params)
                self.assertEqual(
                    (f["n"], f["total"], f["missing"]),
                    (len(labels), len(r0), len(r0) - len(labels)),
                )
                bins = Counter(
                    math.floor(math.log10(float(r[Y])))
                    for r in labels
                    if float(r[Y]) > 0
                )
                self.assertEqual(
                    {
                        round(math.log10(b["low"])): b["count"]
                        for b in f["histogram"]
                        if b["count"]
                    },
                    dict(bins),
                )
                trend = defaultdict(list)
                sol = defaultdict(list)
                for r in labels:
                    trend[r["Cation"], float(r[C])].append(float(r[Y]))
                    sol[r["Solvent"]].append(float(r[Y]))
                self.assertEqual(
                    {(t["cation"], t["x"]): (t["median"], t["n"]) for t in f["trend"]},
                    {k: (median(v), len(v)) for k, v in trend.items()},
                )
                self.assertEqual(
                    {t["code"]: (t["median"], t["n"]) for t in f["solvents"]},
                    {k: (median(v), len(v)) for k, v in sol.items()},
                )

    def test_missing_is_not_zero(self):
        f = self.get("/api/dataset/figures", availability="missing")
        self.assertEqual((f["total"], f["n"], f["nonpositive"]), (21, 0, 0))
        self.assertEqual((f["histogram"], f["trend"], f["solvents"]), ([], [], []))
        records = self.get("/api/dataset/records", availability="missing", limit=100)[
            "records"
        ]
        self.assertTrue(all(r["ionic_conductivity_ms_cm"] is None for r in records))
        self.assertEqual(
            {r["id"] for r in records}, {int(r["ID"]) for r in self.raw if not r[Y]}
        )

    def test_valid_inputs_never_return_predictions(self):
        for keys in (["hgb_svr"], ["smited"], ["hgb_svr", "smited"]):
            res = self.client.post(
                "/api/predict",
                json={**self.form, "viscosity_mpa_s": 1.2, "models": keys},
            )
            self.assertEqual(res.status_code, 503)
            data = res.json()
            self.assertTrue(data["input_valid"])
            self.assertEqual(data["status"], "MODEL_NOT_LOADED")
            self.assertEqual(
                data["formulation"],
                {**self.form, "viscosity_mpa_s": 1.2, "temperature_K": 298},
            )
            self.assertIsNone(data["comparison_mS_cm"])
            self.assertEqual(set(data["predictions"]), set(keys))
            for model in data["predictions"].values():
                self.assertFalse(model["loaded"])
                self.assertEqual(model["status"], "MODEL_NOT_LOADED")
                self.assertIsNone(model["conductivity_mS_cm"])
                self.assertIsNone(model["interval_mS_cm"])

    def test_bad_or_target_bearing_formulations(self):
        invalid = [
            {k: v for k, v in self.form.items() if k != field} for field in self.form
        ]
        for patch in (
            {"cation": "Mg"},
            {"anion": "not-in-oedb"},
            {"solvent": "not-in-oedb"},
            {"concentration_mol_kg": 0.75},
            {"temperature_K": 300},
            {"viscosity_mpa_s": 0},
            {"coordination_cation_anion": -1},
            {"coordination_cation_solvent": None},
            {"viscosity_mpa_s": True},
            {"models": ["smited", "smited"]},
            {"ionic_conductivity_ms_cm": 2},
            {"id": 42},
            {"x": 1},
            {"diffusivity": 1},
        ):
            invalid.append({**self.form, **patch})
        for payload in invalid:
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.client.post("/api/predict", json=payload).status_code, 422
                )
        for x in (math.nan, math.inf):
            res = self.client.post(
                "/api/predict",
                content=json.dumps({**self.form, "viscosity_mpa_s": x}),
                headers={"content-type": "application/json"},
            )
            self.assertEqual(res.status_code, 422)

    def test_invalid_record_query(self):
        for params in (
            {"limit": 0},
            {"limit": 201},
            {"offset": -1},
            {"availability": "zero"},
        ):
            self.assertEqual(
                self.client.get("/api/dataset/records", params=params).status_code, 422
            )


if __name__ == "__main__":
    unittest.main()
