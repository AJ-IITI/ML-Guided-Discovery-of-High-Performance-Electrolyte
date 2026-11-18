"""SMI-TED integration point.

Connect the selected fine-tuned checkpoint and the exact IIT-server inference
pipeline. Preserve the original tokenizer, molecular representation,
47-feature ordering, scaling, fusion architecture and inverse target transform.

Required contract:
    predictor = load_predictor()
    value_mS_cm = predictor.predict_record(record_without_target)
"""

def load_predictor():
    raise NotImplementedError(
        "SMI-TED fine-tuned checkpoint and exact inference pipeline have not yet been connected."
    )
