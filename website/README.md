# Electrolyte Atlas

A local research portal for electrolyte ionic conductivity at 298 K. Home introduces the dataset; Explore filters and charts actual OEDB simulation results; Predict validates a seven-input formulation; Models describes HGB-SVR and SMI-TED separately. The models are offline in Phase 1. No training, GPU, checkpoint, API key, external data service or JavaScript build is required.

## Run locally

Use Python 3.10 or later. From the root of a checkout of the `website-mvp` branch:

```bash
cd website
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows PowerShell use `.\.venv\Scripts\Activate.ps1` for activation. Open [Home](http://127.0.0.1:8000/), [Explore](http://127.0.0.1:8000/explore), [Predict](http://127.0.0.1:8000/predict) or [Models](http://127.0.0.1:8000/models). Stop with Ctrl+C. To use a different port, change `--port` and the URL. Serve the website through FastAPI, not by opening the HTML files directly.

## Data and interpretation

The default source is [the repository CSV](../data/raw/oedb_electrolytes_v2026_05_11.csv) from 11 May 2026. It contains **5,616 records; 5,595 have conductivity and 21 do not**. The snapshot spans Li, Na and K, 9 anions and 26 solvents. The 8 sampled molalities are 0.5 through 4.0 mol/kg in steps of 0.5. All choices and supported combinations are read from the file. For an alternate location of the *same* snapshot set `OEDB_DATA_PATH` to an absolute CSV path before starting; restart after changing the file.

- **Provenance:** the conductivity column is from molecular dynamics. An `exp-ID` links a row to a related experiment; it is not an experimental conductivity measurement. See the [dataset paper](https://doi.org/10.1038/s41524-026-02093-y).
- **Plots:** the distribution counts positive conductivity values per decade. The concentration plot shows medians by cation and sampled molality. Solvent comparisons rank within-filter medians. These are descriptive statistics across the selected records; composition and sample size can differ between groups. View the values table below a chart for exact counts.
- **Missingness:** blank conductivity stays null in JSON, blank in CSV and “Missing” in the table. It never becomes zero. All plots use the full filtered set, independently of pagination.
- **Form:** cation, anion, solvent and molality must match an observed combination. Enter viscosity (mPa·s) and the two dimensionless coordination numbers separately, as positive finite numbers. Fractional coordination is allowed. The example copies only the seven inputs; changing the physical values does not alter the source record. Validation is a schema/domain check, not a claim of chemical feasibility or predictive reliability.

## API

Interactive schema: [Swagger UI](http://127.0.0.1:8000/docs); machine-readable: `/openapi.json`. The portal UI uses only same-origin assets and API calls.

| Method and path | Returns |
| --- | --- |
| GET /api/health | Service, dataset availability and model statuses |
| GET /api/models/status | Separate availability flags for HGB-SVR and SMI-TED |
| GET /api/dataset/summary | Counts, chemistry choices, molalities and solvent display names |
| GET /api/dataset/records | Filtered source rows, stable source-ID order, total count, offset and limit |
| GET /api/dataset/figures | Distribution bins, concentration medians, solvent medians and counts |
| GET /api/dataset/export.csv | All filtered records in CSV, including missing labels |
| POST /api/predict | Validates the formulation; returns HTTP 503 and MODEL_NOT_LOADED when valid, HTTP 422 when invalid |

Shared record/figure/export filters: `q` (case-insensitive text), `cation`, `anion`, `solvent`, `concentration` (mol/kg) and `availability=reported|missing`. Pagination is only for records: `offset` ≥ 0 and `limit` between 1 and 200. For example, `/api/dataset/records?cation=Li&anion=PF6&solvent=EC&limit=8`. The API uses source chemical codes, not display names.

To exercise POST, open Predict, choose **Use a dataset example**, then **Validate formulation**. Both panels report **NOT LOADED**. The JSON contains a null conductivity and interval per requested model, and a null comparison. A valid request does not cause a fit, file download, lookup of simulated conductivity, or fallback estimate.

## Code and checks

`app/main.py` defines request validation and routes; `app/data_service.py` reads and summarizes the CSV; `app/adapters/` and `app/model_registry.py` isolate model-specific code. `static/pages/` contains the four views; `static/` contains local styles, browser modules and accessible SVG charts. The browser also provides tabular equivalents for charts.

From the activated environment in `website/`:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

These checks compare the API to the raw CSV, test the no-result and invalid-input cases, check pagination/export and verify that all four pages and their assets are served. For a browser check: filter to Li/PF6/EC, switch among the three plots, export, then select only missing conductivity and confirm the empty plots. On Predict, try an empty form, zero viscosity and a valid dataset example.

See the [Phase 2 integration guide](MODEL_INTEGRATION_AUDIT.md) before enabling prediction or posting metrics.

For repeatable browser checks at 360, 768 and 1440 px, leave the server running and use a second terminal in the same environment. Install `playwright`, run `python -m playwright install chromium`, then run `python tests/check_layout.py http://127.0.0.1:8000`. Alternatively, set `CHROMIUM_PATH` to an existing Chromium executable. Playwright is only for this optional check.
