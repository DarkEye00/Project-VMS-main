"""
userauth/services/face_service.py

Server-side face comparison using numpy.

Why not face_recognition (dlib)?
  face_recognition.face_distance() internally runs:
      np.linalg.norm(encodings - face_to_compare, axis=1)
  Our architecture generates encodings client-side via face-api.js and only
  sends the 128-float vector to the server, so dlib's image processing is
  never needed. numpy gives identical maths with zero extra C++ dependencies.

Confidence thresholds (face-api.js FaceRecognitionNet L2-normalised vectors):
  distance <= 0.35  ->  confidence >= 90%  ->  matched  (auto check-in)
  distance <= 0.50  ->  confidence >= 60%  ->  warned   (security override optional)
  distance  > 0.50  ->  confidence <  60%  ->  blocked  (override required)
"""

import math
from decimal import Decimal
import numpy as np

MATCH_CONFIDENCE = Decimal("90.00")
WARN_CONFIDENCE  = Decimal("60.00")
MAX_DISTANCE     = 0.80   # distance at which confidence reaches 0%


def _euclidean_distance(a: list, b: list) -> float:
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    return float(np.linalg.norm(va - vb))


def _distance_to_confidence(distance: float) -> Decimal:
    pct = 100.0 - (distance / MAX_DISTANCE) * 100.0
    pct = max(0.0, min(100.0, pct))
    return Decimal(str(round(pct, 2)))


def compare_encodings(stored: list, candidate: list) -> dict:
    """
    Compare two 128-d face descriptors.
    Returns: {distance, confidence (Decimal 0-100), verdict}
    """
    if len(stored) != 128 or len(candidate) != 128:
        return {
            "distance": None,
            "confidence": Decimal("0.00"),
            "verdict": "blocked",
            "error": f"Expected 128-d vectors, got {len(stored)} vs {len(candidate)}.",
        }

    distance   = _euclidean_distance(stored, candidate)
    confidence = _distance_to_confidence(distance)

    if confidence >= MATCH_CONFIDENCE:
        verdict = "matched"
    elif confidence >= WARN_CONFIDENCE:
        verdict = "warned"
    else:
        verdict = "blocked"

    return {"distance": round(distance, 4), "confidence": confidence, "verdict": verdict}


def validate_encoding(encoding: list) -> tuple:
    """
    Validate a received 128-float encoding list.
    Returns (is_valid: bool, error_message: str).
    """
    if not isinstance(encoding, list):
        return False, "Encoding must be a JSON array."
    if len(encoding) != 128:
        return False, f"Expected 128 values, got {len(encoding)}."
    try:
        floats = [float(v) for v in encoding]
    except (TypeError, ValueError):
        return False, "Encoding contains non-numeric values."
    norm = math.sqrt(sum(v * v for v in floats))
    if not (0.5 <= norm <= 1.5):
        return False, f"Encoding norm {norm:.3f} is outside expected range (approx 1.0)."
    return True, ""
