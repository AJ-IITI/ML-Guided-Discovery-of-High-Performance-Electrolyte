"""HGB-SVR integration point.

Implement only after locating the exact fitted estimator and preprocessing
pipeline used for the reported HGB-SVR results.

Required contract:
    predictor = load_predictor()
    value_mS_cm = predictor.predict_record(record_without_target)

The adapter must reproduce original feature construction, preprocessing,
prediction and inverse log-target transformation. Do not refit the model.
"""

def load_predictor():
    raise NotImplementedError(
        "HGB-SVR artifact and exact preprocessing pipeline have not yet been connected."
    )
