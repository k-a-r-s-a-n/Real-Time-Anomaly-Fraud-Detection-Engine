from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import math
import os
from datetime import datetime
import sys
from pathlib import Path
# Ensure python/ directory is on sys.path regardless of execution directory
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from build_feature_vector import build_feature_vector
from sync_to_qdrant import init_qdrant, upsert_to_qdrant, search_qdrant, record_vector_point

app = FastAPI(title="RT-AFDE Verdict Engine")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "fraud_detection"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "root")
}

@app.on_event("startup")
def startup():
    try:
        init_qdrant()
    except Exception as e:
        print(f"⚠️ Note: Qdrant init deferred or waiting for container: {e}")

@app.get("/")
def root():
    return {
        "engine": "RT-AFDE Verdict Engine",
        "status": "online",
        "vector_db": "Qdrant",
        "relational_db": "PostgreSQL",
        "endpoints": {
            "docs": "/docs",
            "transaction": "POST /transaction"
        }
    }

class TransactionInput(BaseModel):
    user_id: int
    card_id: int
    merchant_id: int
    ip_address: str
    amount: float
    location_lat: float
    location_long: float

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate Great-Circle distance in km between two lat/long points."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

@app.post("/transaction")
def process_transaction(txn: TransactionInput):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # Ensure collection exists
        try:
            init_qdrant()
        except Exception:
            pass

        # STEP 1: DEVICE RESOLUTION
        cur.execute("SELECT * FROM resolve_device_and_flag(%s, %s)", (txn.user_id, txn.ip_address))
        device_id, is_new_device = cur.fetchone()

        # STEP 1b: PREVIOUS TRANSACTION LOCATION & IMPOSSIBLE TRAVEL CHECK
        cur.execute(
            """SELECT t.location_lat, t.location_long, t.timestamp
               FROM Transactions t
               JOIN Cards c ON t.card_id = c.card_id
               WHERE c.user_id = %s
               ORDER BY t.transaction_id DESC LIMIT 1""",
            (txn.user_id,)
        )
        prev_txn = cur.fetchone()

        if prev_txn and prev_txn[0] is not None and prev_txn[1] is not None:
            prev_lat, prev_long = float(prev_txn[0]), float(prev_txn[1])
            geo_delta = haversine_distance(prev_lat, prev_long, txn.location_lat, txn.location_long)
            prev_time = prev_txn[2]
            if prev_time:
                time_delta = max((datetime.now() - prev_time).total_seconds() / 3600.0, 0.1)
            else:
                time_delta = 1.0
        else:
            geo_delta = 0.0
            time_delta = 24.0

        # Velocity in km/h (speed between last known transaction and this one)
        velocity_kmh = geo_delta / max(time_delta, 0.05)
        is_impossible_travel = geo_delta > 500 and velocity_kmh > 700

        # STEP 2: INSERT TRANSACTION (Fires Triggers)
        cur.execute(
            """INSERT INTO Transactions (card_id, merchant_id, device_id, amount, location_lat, location_long)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING transaction_id""",
            (txn.card_id, txn.merchant_id, device_id, txn.amount, txn.location_lat, txn.location_long)
        )
        transaction_id = cur.fetchone()[0]

        # STEP 3: UPDATE RISK PROFILE
        cur.execute("CALL update_user_risk_profile(%s)", (txn.user_id,))

        # STEP 4: BUILD NUMERIC FEATURE VECTOR (With real geo_delta)
        cur.execute("SELECT risk_level FROM Merchant_Cats mc JOIN Merchants m ON mc.mcc_code = m.mcc_code WHERE m.merchant_id = %s", (txn.merchant_id,))
        mcc_risk_str = cur.fetchone()[0]
        mcc_risk_num = 3.0 if mcc_risk_str == 'HIGH' else (2.0 if mcc_risk_str == 'MEDIUM' else 1.0)
        
        current_hour = datetime.now().hour
        vector = build_feature_vector(
            amount=txn.amount,
            time_delta=time_delta,
            geo_delta=geo_delta,
            mcc_risk_score=mcc_risk_num,
            is_new_device=is_new_device,
            freq_24h=3,
            avg_amt_ratio=txn.amount / 150.0,
            hour_sin=math.sin(2 * math.pi * current_hour / 24),
            hour_cos=math.cos(2 * math.pi * current_hour / 24)
        )

        # STEP 5: QDRANT UPSERT & SEARCH
        qdrant_point_id = upsert_to_qdrant(vector, txn.merchant_id)
        similarity_score = search_qdrant(vector, exclude_id=qdrant_point_id)

        # If impossible travel is detected, vector matches high-risk geo fraud pattern
        if is_impossible_travel:
            similarity_score = max(similarity_score, 0.9450)

        # STEP 6: INSERT BRIDGE ROW INTO VECTOR_POINTS
        record_vector_point(cur, qdrant_point_id, transaction_id, txn.merchant_id)

        # STEP 7: DECISION ENGINE
        if similarity_score > 0.8:
            verdict = "FRAUD"
        elif similarity_score >= 0.5:
            verdict = "SUSPICIOUS"
        else:
            verdict = "SAFE"

        # STEP 8: WRITE VERDICT TO FRAUD_ALERTS
        cur.execute(
            """INSERT INTO Fraud_Alerts (transaction_id, similarity_score, decision_status)
               VALUES (%s, %s, %s)""",
            (transaction_id, similarity_score, verdict)
        )

        conn.commit()

        return {
            "status": "success",
            "transaction_id": transaction_id,
            "device_id": device_id,
            "new_device_detected": is_new_device,
            "geo_delta_km": round(geo_delta, 1),
            "time_delta_hrs": round(time_delta, 2),
            "impossible_travel": is_impossible_travel,
            "qdrant_point_id": qdrant_point_id,
            "similarity_score": round(similarity_score, 4),
            "verdict": verdict
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()
