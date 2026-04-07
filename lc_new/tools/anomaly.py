# tools/anomaly.py
import numpy as np
from typing import List, Dict

def analyze_series_anomaly(values: List[float]) -> Dict:
    xs = [v for v in values if isinstance(v, (int, float))]
    if len(xs) < 10:
        return {"status": "unknown", "reason": "not_enough_points"}

    median = np.median(xs)
    mad = np.median([abs(x - median) for x in xs])

    if mad == 0:
        return {"status": "normal"}

    robust_z = [0.6745 * (x - median) / mad for x in xs]
    max_z = max(abs(z) for z in robust_z)

    return {
        "status": "abnormal" if max_z >= 3.5 else "normal",
        "latest": xs[-1],
        "max_robust_z": round(max_z, 2),
    }