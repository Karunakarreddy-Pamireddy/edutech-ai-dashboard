"""
AI Predictive Model - Day 9
Trains a Linear Regression model to predict student score from:
  - study_hours (numeric)
  - ai_tool_used (boolean → 0/1)
  - subject (one-hot encoded)

Saves the model + metadata with joblib for the /api/predict endpoint.
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score

_basedir = os.path.dirname(os.path.dirname(__file__))

# Write paths: on Vercel, write to /tmp. Otherwise write to the project's data/ folder.
if os.environ.get("VERCEL") == "1":
    MODEL_PATH_WRITE = os.path.join("/tmp", "model.pkl")
    META_PATH_WRITE = os.path.join("/tmp", "model_meta.json")
else:
    MODEL_PATH_WRITE = os.path.join(_basedir, "data", "model.pkl")
    META_PATH_WRITE = os.path.join(_basedir, "data", "model_meta.json")

# Default read paths (pre-packaged files in the deployment bundle)
MODEL_PATH_READ = os.path.join(_basedir, "data", "model.pkl")
META_PATH_READ = os.path.join(_basedir, "data", "model_meta.json")

def get_model_path_for_reading():
    if os.path.exists(MODEL_PATH_WRITE):
        return MODEL_PATH_WRITE
    return MODEL_PATH_READ

def get_meta_path_for_reading():
    if os.path.exists(META_PATH_WRITE):
        return META_PATH_WRITE
    return META_PATH_READ

FEATURES   = ["study_hours", "ai_tool_used", "subject"]
TARGET     = "score"


# ── Build sklearn pipeline ────────────────────────────────────────────────────
def _build_pipeline():
    """
    ColumnTransformer:
      - study_hours  → passthrough (numeric)
      - ai_tool_used → passthrough (0/1)
      - subject      → one-hot encoded (drop first to avoid multicollinearity)
    Then LinearRegression.
    """
    preprocessor = ColumnTransformer(transformers=[
        ("num",  "passthrough", ["study_hours", "ai_tool_used"]),
        ("subj", OneHotEncoder(drop="first", sparse_output=False), ["subject"]),
    ])
    return Pipeline([
        ("preprocessor", preprocessor),
        ("regressor",    LinearRegression()),
    ])


# ── Train ─────────────────────────────────────────────────────────────────────
def train_model(clean_df: pd.DataFrame) -> dict:
    """
    Train the model on the full cleaned DataFrame.
    Returns a results dict with metrics + feature importance.
    Saves model and metadata to disk.
    """
    if clean_df.empty or len(clean_df) < 30:
        return {"error": "Not enough data to train. Need at least 30 records."}

    # Prepare data
    df = clean_df[FEATURES + [TARGET]].dropna().copy()
    df["ai_tool_used"] = df["ai_tool_used"].astype(int)

    X = df[FEATURES]
    y = df[TARGET]

    # Train / test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train
    model = _build_pipeline()
    model.fit(X_train, y_train)

    # Evaluate
    y_pred   = model.predict(X_test)
    r2       = round(r2_score(y_test, y_pred), 4)
    mae      = round(mean_absolute_error(y_test, y_pred), 2)
    rmse     = round(np.sqrt(np.mean((y_test - y_pred) ** 2)), 2)

    # Feature importance (coefficients from the linear model)
    reg       = model.named_steps["regressor"]
    pre       = model.named_steps["preprocessor"]
    subj_cats = pre.transformers_[1][1].categories_[0][1:]  # drop-first removes first cat
    feat_names= ["study_hours", "ai_tool_used"] + list(subj_cats)
    coefs     = dict(zip(feat_names, [round(c, 4) for c in reg.coef_]))

    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH_WRITE), exist_ok=True)
    joblib.dump(model, MODEL_PATH_WRITE)

    # Save metadata
    meta = {
        "trained_on":   len(df),
        "train_size":   len(X_train),
        "test_size":    len(X_test),
        "r2":           r2,
        "mae":          mae,
        "rmse":         rmse,
        "intercept":    round(float(reg.intercept_), 4),
        "coefficients": coefs,
        "subjects":     sorted(df["subject"].unique().tolist()),
        "interpretation": {
            "r2":   "Proportion of score variance explained by the model (1.0 = perfect)",
            "mae":  "Average prediction error in score points",
            "rmse": "Root mean squared error — penalises large errors more",
        },
        "disclaimer": (
            "This model is for demonstration purposes only. "
            "Predictions are based on synthetic data and should not be used "
            "for real academic assessment or decision-making."
        ),
    }
    os.makedirs(os.path.dirname(META_PATH_WRITE), exist_ok=True)
    with open(META_PATH_WRITE, "w") as f:
        json.dump(meta, f, indent=2)

    return {"status": "trained", "metrics": meta}


# ── Predict ───────────────────────────────────────────────────────────────────
def predict_score(study_hours: float, ai_tool_used: bool, subject: str) -> dict:
    """
    Load saved model and return a predicted score.
    Also returns a confidence band (±MAE from training).
    """
    model_path = get_model_path_for_reading()
    if not os.path.exists(model_path):
        return {"error": "Model not trained yet. Call /api/model/train first."}

    model = joblib.load(model_path)

    input_df = pd.DataFrame([{
        "study_hours":  float(study_hours),
        "ai_tool_used": int(bool(ai_tool_used)),
        "subject":      str(subject),
    }])

    predicted = float(model.predict(input_df)[0])
    predicted = round(max(0.0, min(100.0, predicted)), 1)  # clip to valid score range

    # Load MAE for confidence band
    mae = 5.0  # fallback
    meta_path = get_meta_path_for_reading()
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        mae = meta.get("mae", 5.0)

    return {
        "predicted_score": predicted,
        "confidence_band": {
            "low":  round(max(0,   predicted - mae), 1),
            "high": round(min(100, predicted + mae), 1),
        },
        "inputs": {
            "study_hours":  study_hours,
            "ai_tool_used": ai_tool_used,
            "subject":      subject,
        },
        "disclaimer": "Prediction based on synthetic training data. For demonstration only.",
    }


# ── Model status ──────────────────────────────────────────────────────────────
def model_status() -> dict:
    """Check if a trained model exists and return its metadata."""
    model_path = get_model_path_for_reading()
    meta_path = get_meta_path_for_reading()
    if not os.path.exists(model_path):
        return {"trained": False, "message": "No trained model found. POST /api/model/train to train."}
    if not os.path.exists(meta_path):
        return {"trained": True, "message": "Model file exists but metadata missing."}
    with open(meta_path) as f:
        meta = json.load(f)
    return {"trained": True, "meta": meta}
