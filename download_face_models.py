"""
download_face_models.py
Run from your project root on any OS (Windows/Mac/Linux):

    python download_face_models.py

Downloads the 7 face-api.js weight files into static/models/
"""

import os
import urllib.request

DEST = os.path.join("static", "models")
BASE = "https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights"

FILES = [
    "tiny_face_detector_model-shard1",
    "tiny_face_detector_model-weights_manifest.json",
    "face_landmark_68_tiny_model-shard1",
    "face_landmark_68_tiny_model-weights_manifest.json",
    "face_recognition_model-shard1",
    "face_recognition_model-shard2",
    "face_recognition_model-weights_manifest.json",
]


def download():
    os.makedirs(DEST, exist_ok=True)
    print(f"\nDownloading face-api.js model weights into '{DEST}' ...\n")
    failed = []

    for filename in FILES:
        dest_path = os.path.join(DEST, filename)
        if os.path.exists(dest_path):
            print(f"  [skip]  {filename}")
            continue
        try:
            print(f"  [down]  {filename} ...", end=" ", flush=True)
            urllib.request.urlretrieve(f"{BASE}/{filename}", dest_path)
            print("OK")
        except Exception as e:
            print(f"FAILED — {e}")
            failed.append(filename)

    if failed:
        print(f"\n[!] {len(failed)} file(s) failed. Check your internet connection and retry.")
    else:
        print(f"\nAll model files saved to '{DEST}'")
        print("Next: python manage.py collectstatic\n")


if __name__ == "__main__":
    download()
