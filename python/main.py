from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import math
import os
from datetime import datetime
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

        # STEP 2: INSERT TRANSACTION (Fires Triggers)
        cur.execute(
            """INSERT INTO Transactions (card_id, merchant_id, device_id, amount, location_lat, location_long)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING transaction_id""",
            (txn.card_id, txn.merchant_id, device_id, txn.amount, txn.location_lat, txn.location_long)
        )
        transaction_id = cur.fetchone()[0]

        # STEP 3: UPDATE RISK PROFILE
        cur.execute("CALL update_user_risk_profile(%s)", (txn.user_id,))

        # STEP 4: BUILD NUMERIC FEATURE VECTOR
        # Extracting mcc risk score
        cur.execute("SELECT risk_level FROM Merchant_Cats mc JOIN Merchants m ON mc.mcc_code = m.mcc_code WHERE m.merchant_id = %s", (txn.merchant_id,))
        mcc_risk_str = cur.fetchone()[0]
        mcc_risk_num = 3.0 if mcc_risk_str == 'HIGH' else (2.0 if mcc_risk_str == 'MEDIUM' else 1.0)
        
        # Simulating complex features for real-time demo
        current_hour = datetime.now().hour
        vector = build_feature_vector(
            amount=txn.amount,
            time_delta=12.5,          # simulated hours since last txn
            geo_delta=0.0,            # simulated distance
            mcc_risk_score=mcc_risk_num,
            is_new_device=is_new_device,
            freq_24h=3,               # simulated txns in last 24h
            avg_amt_ratio=txn.amount / 150.0, # ratio against user avg
            hour_sin=math.sin(2 * math.pi * current_hour / 24),
            hour_cos=math.cos(2 * math.pi * current_hour / 24)
        )

        # STEP 5: QDRANT UPSERT & SEARCH
        qdrant_point_id = upsert_to_qdrant(vector, txn.merchant_id)
        similarity_score = search_qdrant(vector, exclude_id=qdrant_point_id)

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
