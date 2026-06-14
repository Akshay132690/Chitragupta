from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import zipfile
import cv2
import torch

from ml.model import load_model
from ml.inference import run_inference
from utils.image_utils import make_overlay, make_heatmap
from geo.postprocess import mask_to_geojson

# ------------------ APP SETUP ------------------

app = Flask(__name__)

UPLOAD_DIR = "uploads"
RESULT_DIR = "static/results"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 🔥 LOAD TRAINED MODEL
model = load_model("model/unet_mumbai_roads.pth", device)
model.eval()

# ------------------ ROUTES ------------------

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", result=False)


@app.route("/predict", methods=["POST"])
def predict():
    file = request.files.get("image")
    if not file:
        return redirect(url_for("index"))

    # ---------- SAVE UPLOADED IMAGE ----------
    img_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(img_path)

    # ---------- READ + PREPROCESS ----------
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 🔥 MUST MATCH TRAINING SIZE
    img = cv2.resize(img, (512, 512))

    # ---------- INFERENCE ----------
    mask, inf_time = run_inference(model, img, device)

    # 🔍 DEBUG (VERY IMPORTANT – KEEP FOR NOW)
    print(
        "MASK DEBUG ->",
        "min:", float(mask.min()),
        "max:", float(mask.max()),
        "mean:", float(mask.mean())
    )

    # ---------- SAVE INPUT ----------
    cv2.imwrite(
        os.path.join(RESULT_DIR, "input_image.png"),
        cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    )

    # ---------- SAVE BINARY MASK ----------
    cv2.imwrite(
        os.path.join(RESULT_DIR, "predicted_mask.png"),
        (mask > 0.3).astype("uint8") * 255
    )

    # ---------- OVERLAY ----------
    overlay = make_overlay(img, mask, threshold=0.3)
    cv2.imwrite(
        os.path.join(RESULT_DIR, "overlay.png"),
        cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
    )

    # ---------- HEATMAP ----------
    heat = make_heatmap(mask)
    cv2.imwrite(
        os.path.join(RESULT_DIR, "confidence_heatmap.png"),
        cv2.cvtColor(heat, cv2.COLOR_RGB2BGR)
    )

    # ---------- GEOJSON ----------
    mask_to_geojson(
        mask,
        os.path.join(RESULT_DIR, "road_centerlines.geojson"),
        threshold=0.3
    )

    info = {
        "model": "U-Net (ResNet34)",
        "device": str(device),
        "inference_time_s": inf_time
    }

    return render_template("index.html", result=True, info=info)


# ---------- DOWNLOAD ZIP ----------
@app.route("/download_results", methods=["GET"])
def download_results():
    zip_path = os.path.join(RESULT_DIR, "road_segmentation_results.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in [
            "input_image.png",
            "predicted_mask.png",
            "overlay.png",
            "confidence_heatmap.png",
            "road_centerlines.geojson"
        ]:
            fp = os.path.join(RESULT_DIR, fname)
            if os.path.exists(fp):
                zf.write(fp, arcname=fname)

    return send_file(zip_path, as_attachment=True)


# ------------------ RUN ------------------

if __name__ == "__main__":
    app.run(debug=True,port=5002)
