"""
download_face_models.py  — UPDATED for SSD MobileNet (v2)

Downloads face-api.js model weights needed for:
  - ssd_mobilenetv1      (high-accuracy face detector — NEW)
  - face_landmark_68     (full 68-point landmark model — replaces 68_tiny)
  - face_recognition     (128-d descriptor)

Run from the project root:
    python download_face_models.py
    python manage.py collectstatic

Why SSD over tinyFaceDetector?
  - SSD MobileNet is ~3x more accurate in variable / dim lighting
  - It is the model originally trained alongside the FaceRecognitionNet
    so encodings are more consistent across sessions
  - Slight trade-off: ~200 KB more weights downloaded
"""

import os
import urllib.request

BASE = "https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights"
DEST = os.path.join("static", "models")

# ── Weight files required ──────────────────────────────────────────────────────
FILES = [
    # SSD MobileNet v1 — high-accuracy face detector
    "ssd_mobilenetv1_model-weights_manifest.json",
    "ssd_mobilenetv1_model-shard1",
    "ssd_mobilenetv1_model-shard2",

    # 68-point landmarks (full, not tiny — better alignment for recognition)
    "face_landmark_68_model-weights_manifest.json",
    "face_landmark_68_model-shard1",

    # Face recognition / descriptor net
    "face_recognition_model-weights_manifest.json",
    "face_recognition_model-shard1",
    "face_recognition_model-shard2",

    # Keep TinyFaceDetector as fallback (USE_SSD=false in staff.html)
    "tiny_face_detector_model-weights_manifest.json",
    "tiny_face_detector_model-shard1",

    # Tiny landmarks (fallback)
    "face_landmark_68_tiny_model-weights_manifest.json",
    "face_landmark_68_tiny_model-shard1",
]


def main():
    os.makedirs(DEST, exist_ok=True)
    print(f"Downloading {len(FILES)} face-api.js model files to '{DEST}/'...\n")

    for filename in FILES:
        url       = f"{BASE}/{filename}"
        dest_path = os.path.join(DEST, filename)

        if os.path.exists(dest_path):
            print(f"  [skip]  {filename}  (already exists)")
            continue

        print(f"  [down]  {filename}")
        try:
            urllib.request.urlretrieve(url, dest_path)
            print(f"  [ok]    {filename}")
        except Exception as e:
            print(f"  [FAIL]  {filename}: {e}")
            raise

    print(f"\nDone. All model files saved to '{DEST}'")
    print("\nNext step: python manage.py collectstatic")


if __name__ == "__main__":
    main()
