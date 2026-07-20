# Research Repository Instructions

This repository contains academic research on ML-guided electrolyte conductivity prediction using OEDB.

## Rules

- Never overwrite completed notebooks unless explicitly instructed.
- Preserve all historical experiment results.
- Add new experiments as new notebooks or scripts.
- Reuse identical validation splits for fair model comparisons.
- Prevent data leakage.
- Fit scaling only on training folds.
- Keep entire solvent/anion groups out of training during GroupKFold.
- Save metrics under `outputs/metrics/`.
- Save figures under `outputs/figures/`.
- Use `RANDOM_STATE = 42` unless testing seed sensitivity.
- Keep notebooks reproducible from a fresh kernel.
- Do not silently change methodology.

## Completed work

- Notebook 1: baseline Random Forest + Morgan fingerprints
- Notebook 2: log target + RDKit descriptors + model comparison
- Notebook 3: leakage-safe grouped validation
- Notebook 4: scaling + viscosity/coordination + solvent analysis
- Notebook 5: dataset, descriptor, dependency and chemical-space analysis

## Research priority

Focus on understanding and improving unseen-solvent generalization.

Do not introduce neural networks, GNNs, transformers, or foundation models without a clearly defined scientific hypothesis and baseline comparison.
