import os
import re
import torch
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image
import torchvision.transforms as T
from unet import UNet
from datetime import datetime

# -----------------------
# App setup
# -----------------------
app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INFERENCE_DIR = os.path.join(BASE_DIR, "inference_data")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
ORIGINALS_DIR = os.path.join(PROCESSED_DIR, "originals")
MASKS_DIR = os.path.join(PROCESSED_DIR, "masks")

os.makedirs(ORIGINALS_DIR, exist_ok=True)
os.makedirs(MASKS_DIR, exist_ok=True)

# -----------------------
# Lake configuration
# -----------------------
LAKES = {
    "lhonakh": {
        "name": "Lhonakh Lake",
        "model_path": "models/lhonakh_unet.pth"
    },
    "gurudongmar": {
        "name": "Gurudongmar Lake",
        "model_path": "models/gurudongmar_unet.pth"
    },
    "ghepang": {
        "name": "Ghepang Lake",
        "model_path": "models/ghepang_unet.pth"
    }
}


# -----------------------
# Load models (once)
# -----------------------
models = {}

for lake, cfg in LAKES.items():
    model = UNet()
    model.load_state_dict(torch.load(cfg["model_path"], map_location="cpu"))
    model.eval()
    models[lake] = model
    print(f"✅ Loaded model for {lake}")

# -----------------------
# Image transform
# -----------------------
transform = T.Compose([
    T.Resize((256, 256)),
    T.ToTensor(),
    T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
])

# -----------------------
# Utility functions
# -----------------------
DATE_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}")

def extract_date(filename):
    match = DATE_REGEX.search(filename)
    return match.group() if match else None

def assess_risk(area):
    if area > 10000:
        return "High"
    elif area > 8000:
        return "Moderate"
    return "Low"

# -----------------------
# APIs
# -----------------------

@app.route("/api/lakes")
def get_lakes():
    return jsonify({
        "lakes": [
            {"key": k, "name": v["name"]}
            for k, v in LAKES.items()
        ]
    })


@app.route("/api/dates")
def get_dates():
    lake = request.args.get("lake")
    if lake not in LAKES:
        return jsonify({"error": "Invalid lake"}), 400

    lake_dir = os.path.join(INFERENCE_DIR, lake)
    files = os.listdir(lake_dir)

    dates = []
    for f in files:
        if f.lower().endswith(".jpg"):
            d = extract_date(f)
            if d:
                dates.append(d)

    dates = sorted(list(set(dates)), key=lambda x: datetime.strptime(x, "%Y-%m-%d"))
    return jsonify({"dates": dates})


@app.route("/api/analyze")
def analyze():
    lake = request.args.get("lake")
    date = request.args.get("date")

    if lake not in LAKES:
        return jsonify({"error": "Invalid lake"}), 400

    lake_dir = os.path.join(INFERENCE_DIR, lake)
    model = models[lake]

    image_file = None
    for f in os.listdir(lake_dir):
        if date in f and f.lower().endswith(".jpg"):
            image_file = f
            break

    if image_file is None:
        return jsonify({"error": "Image not found"}), 404

    image_path = os.path.join(lake_dir, image_file)
    image = Image.open(image_path).convert("RGB")

    input_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        output = model(input_tensor)

    mask = (output.squeeze().numpy() > 0.5).astype(np.uint8)
    area_pixels = int(mask.sum())

    # Save outputs
    base_name = f"{lake}_{date}"
    orig_out = f"{base_name}.jpg"
    mask_out = f"{base_name}_mask.png"

    image.resize((256, 256)).save(os.path.join(ORIGINALS_DIR, orig_out))
    Image.fromarray(mask * 255).save(os.path.join(MASKS_DIR, mask_out))

    return jsonify({
        "original_image_url": f"/processed/originals/{orig_out}",
        "mask_image_url": f"/processed/masks/{mask_out}",
        "lake_area_pixels": area_pixels,
        "risk_level": assess_risk(area_pixels)
    })


@app.route("/processed/originals/<filename>")
def serve_original(filename):
    return send_from_directory(ORIGINALS_DIR, filename)


@app.route("/processed/masks/<filename>")
def serve_mask(filename):
    return send_from_directory(MASKS_DIR, filename)
@app.route("/")
def home():
    return send_from_directory("static", "index.html")


# -----------------------
# Run app
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
