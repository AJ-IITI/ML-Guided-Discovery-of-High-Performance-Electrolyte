# Model integration audit — website MVP

## Repository assets verified

- Repository: AJ-IITI/ML-Guided-Discovery-of-High-Performance-Electrolyte
- Website branch: website-mvp
- Dataset file present: data/raw/oedb_electrolytes_v2026_05_11.csv
- Dataset version: 2026-05-11
- Dataset record count in the existing project notes: 5,595 labelled rows
- Source notebooks present: notebooks/01 through notebooks/05
- Existing outputs include historical analysis CSVs and figures.

The repository dataset exposes composition, concentration, conductivity target, viscosity, cation/anion/solvent diffusivities, coordination values, density, anion/solvent SMILES, PubChem identifiers and t-SNE coordinates.

## SMI-TED findings from the current research work

- Selected candidate for initial portal integration: Partial fine-tuning, seed 42.
- Best validation log RMSE reported in the current project discussion: 0.2567.
- SMI-TED representation: 768-dimensional molecular representation plus 47 numerical features.
- The fine-tuned checkpoint is on the IIT server under the local SMI-TED project outputs; it is not stored in this GitHub repository.
- The exact inference script, tokenizer path, feature ordering and checkpoint path must be confirmed from the server before writing the adapter.

## HGB-SVR findings

- HGB-SVR is a separate trained tabular model from the user's current research workflow.
- Its exact fitted artifact path, preprocessing object, feature order and inference code are not present in this repository inspection.
- Do not retrain or approximate HGB-SVR for the website.

## Model input policy

The user-facing form is cation, anion, solvent and concentration. The backend performs exact lookup in the model's training-domain OEDB table and passes a target-free record to the model-specific adapter.

The adapter must use the exact preprocessing and feature-generation pipeline from the original training run. Conductivity target, row IDs and t-SNE coordinates must not enter the model input.

The initial interface displays 298 K as a fixed assumption. It must not be added to model inputs unless the original training pipeline explicitly requires it.

## Blocking items before real inference is enabled

1. Locate and expose the selected SMI-TED checkpoint and its original inference code.
2. Locate the fitted HGB-SVR artifact and its complete preprocessing pipeline.
3. Confirm the exact OEDB file and 47-feature manifest used by the current SMI-TED training run.
4. Implement both adapters against their original inference code.
5. Compare adapter predictions against the original standalone inference scripts on several fixed formulations.
6. Only then mark both models as loaded.

## Prediction intervals

The MVP intentionally returns no numerical uncertainty interval. A separate calibration split and a documented calibration method must be used before displaying an error range.
