from flask import Flask, request, render_template
from catboost import CatBoostClassifier
import pandas as pd
import folium

app = Flask(__name__)

df = pd.read_csv("data/urban_pluvial_flood_risk_dataset.csv")

categorical_cols = [
    "dem_source",
    "land_use",
    "soil_group",
    "storm_drain_type",
    "rainfall_source"
]

model = CatBoostClassifier()
model.load_model("model/flood_risk_model.cbm")


def preprocess_city_data(df_city):
    X = df_city.drop(columns=[
        "risk_labels", "segment_id", "city_name",
        "admin_ward", "catchment_id"
    ])

    for col in categorical_cols:
        if col in X.columns:
            X[col] = X[col].astype(str).fillna("missing")

    for col in X.columns:
        if col not in categorical_cols:
            X[col] = X[col].fillna(0)

    return X


def compute_risk_metrics(df_city):
    counts = df_city["predicted_label"].value_counts()
    high_risk = df_city["predicted_label"].str.contains(
        "extreme_rain_history|ponding_hotspot|low_lying"
    ).sum()
    score = int((high_risk / len(df_city)) * 100)
    return counts, score


def build_map(df_city):
    center = [df_city.latitude.mean(), df_city.longitude.mean()]
    m = folium.Map(location=center, zoom_start=12)

    color_map = {
        "extreme_rain_history": "red",
        "ponding_hotspot": "orange",
        "low_lying": "blue",
        "sparse_drainage": "purple",
        "monitor": "green"
    }

    for _, r in df_city.iterrows():
        color = next(
            (v for k, v in color_map.items() if k in r.predicted_label),
            "gray"
        )
        folium.CircleMarker(
            [r.latitude, r.longitude],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=r.predicted_label
        ).add_to(m)

    return m._repr_html_()


@app.route("/", methods=["GET", "POST"])
def index():
    prediction = None
    city_data = None
    map_html = None
    risk_labels = []
    risk_counts = []
    risk_score = 0

    if request.method == "POST":
        city_name = request.form["city_name"].strip().lower()
        df_city = df[df["city_name"].str.lower() == city_name].copy()

        if df_city.empty:
            prediction = f"No data found for {city_name}"
        else:
            X_city = preprocess_city_data(df_city)
            preds = model.predict(X_city).ravel()
            df_city["predicted_label"] = preds

            prediction = f"Risk Analysis for {city_name.title()}"
            city_data = df_city[["latitude", "longitude", "predicted_label"]].to_dict(orient="records")

            counts, risk_score = compute_risk_metrics(df_city)
            risk_labels = counts.index.astype(str).tolist()
            risk_counts = counts.values.tolist()

            map_html = build_map(df_city)

    return render_template(
        "index.html",
        prediction=prediction,
        city_data=city_data,
        map_html=map_html,
        risk_labels=risk_labels,
        risk_counts=risk_counts,
        risk_score=risk_score
    )


if __name__ == "__main__":
    app.run(debug=True,port=5001)
