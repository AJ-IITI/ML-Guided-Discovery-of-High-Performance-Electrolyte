from .adapters.base import Predictor
from .adapters.hgb_svr import HGBSVRPredictor
from .adapters.smited import SMITEDPredictor

# Explicit instances: no dynamic imports, model deserialization or training at startup.
REGISTRY: dict[str, Predictor] = {
    p.key: p for p in (HGBSVRPredictor(), SMITEDPredictor())
}
