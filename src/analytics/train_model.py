import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
import joblib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import DB_PATH, BASE_DIR

def train():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM lot_occupancy_hourly", conn, index_col="interval_start")
    
    features = ["occupancy_rate", "sin_hour", "cos_hour", "day_of_week", "is_weekend", "lag_1h", "lag_2h", "lag_24h", "rolling_3h_mean"]
    X = df[features]
    y = df["target_next_hour"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    r2 = r2_score(y_test, preds)
    print(f"[ML] Random Forest R2 Score: {r2:.4f}")
    
    model_path = BASE_DIR / "models" / "parking_model.joblib"
    joblib.dump(model, model_path)
    print(f"[ML] Champion model saved to: {model_path}")

if __name__ == "__main__":
    train()