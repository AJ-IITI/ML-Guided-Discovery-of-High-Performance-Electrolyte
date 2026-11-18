# Enabling the original models in Phase 2

**Phase 1 state:** the OEDB snapshot and research code are available; the IIT cluster artifacts have not been loaded or verified here. Both adapters return `MODEL_NOT_LOADED`. No reported test score, prediction interval or numeric prediction is exposed as a portal result.

## Input boundary

The form and POST schema accept cation, anion, solvent, concentration (mol/kg), viscosity (mPa·s), cation–anion coordination and cation–solvent coordination. The fixed temperature is 298 K. The backend checks the composition–molality tuple against the dataset, then passes only the seven user values plus temperature metadata to the adapters. Do not replace viscosity or coordination with a source lookup. Do not append temperature to the trained feature vector unless the original inference pipeline did so.

Resolve molecular metadata from the approved identity table and use the **original** feature code. Do not pass the entire OEDB row. Conductivity, Nernst–Einstein conductivity, diffusivities, source IDs, experimental reference IDs and visualization coordinates must never enter the prediction vector.

## Required artifacts

| Adapter | Required originals |
| --- | --- |
| `HGBSVRPredictor` | Fitted HGB correction model and its Walden baseline, fitted SVR, final blend parameters, exact feature generator and ordered 47-feature manifest, encoders, scaling/imputation objects from training, original target and inverse-transform code. |
| `SMITEDPredictor` | The selected Partial FT checkpoint and compatible generic SMI-TED base checkpoint, tokenizer/vocabulary, architecture/configuration, formulation-to-token builder, original molecular embedding and pooling, original numerical preprocessing and 47-feature order, and the trained fusion/regression head. |
| Both | Dataset version/hash, original code revision and dependency versions, split and row-ID manifests, standalone inference command, trusted artifact hashes and paired reference predictions. |

Artifact paths on the cluster are not assumed. Bank the reference predictions before changing dependencies or porting code. Use training-fitted preprocessing without refitting. Keep separate model environments if necessary.

## Adapter and release checks

1. Implement the original inference call in `app/adapters/hgb_svr.py` or `app/adapters/smited.py` using the `Predictor` protocol. Keep their lifecycles independent. Missing artifacts or a failed check must leave that adapter unavailable; loading a base checkpoint alone does not constitute a fitted conductivity model.
2. Reproduce the stored per-row predictions, both in the training target space and after the original inverse transform to mS/cm. Cover different ions, solvents, molalities and conductivity levels. Compare to a documented numeric tolerance appropriate to the original runtime; stop on an unexplained mismatch. The HGB correction term or a standalone transformer embedding is not a conductivity prediction.
3. Only then extend the Phase 1 `/api/predict` response dispatcher and browser output renderer for loaded and partially loaded states. Return values only for verified adapters. Keep the other model, comparison and interval null when they are unavailable. Test single-model, both-model and partial-failure cases.
4. Document metrics from the same manifest and evaluation setup for each model. Separate the random split from complete-solvent holdout. Validation selects checkpoints; keep test data out of selection. Publish comparisons only after identical row IDs, targets, units and transformation rules are confirmed.
5. Enable uncertainty intervals only after documenting a separate calibration procedure, evaluation of coverage and applicability domain. Do not use the difference between two predictors as an uncertainty interval.
