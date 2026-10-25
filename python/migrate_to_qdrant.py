import psycopg2
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from build_feature_vector import build_feature_vector
import uuid
import os

# 1. Connect to DBs
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "fraud_detection"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "root")
}

pg_conn = psycopg2.connect(**DB_CONFIG)
pg_cur = pg_conn.cursor()
q_client = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), port=int(os.getenv("QDRANT_PORT", "6333")))

COLLECTION_NAME = "transaction_behaviour"

# 2. Define Qdrant Schema
if not q_client.collection_exists(COLLECTION_NAME):
    q_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=9, distance=Distance.COSINE)
    )
    print("Created Qdrant collection:", COLLECTION_NAME)

# 3. Fetch PG Data
print("Fetching DA2 transactions from PostgreSQL...")
pg_cur.execute("""
    SELECT t.transaction_id, t.amount, t.merchant_id, 
           mc.risk_level, t.device_id
    FROM Transactions t
    JOIN Merchants m ON t.merchant_id = m.merchant_id
    JOIN Merchant_Cats mc ON m.mcc_code = mc.mcc_code
    ORDER BY t.transaction_id
""")
rows = pg_cur.fetchall()

points_to_upload = []

print(f"Vectorizing and preparing {len(rows)} records for Qdrant...")
for row in rows:
    txn_id, amount, merch_id, risk_lvl, device_id = row
    
    # Feature extraction for historical dataset
    mcc_risk = 3.0 if risk_lvl == 'HIGH' else (2.0 if risk_lvl == 'MEDIUM' else 1.0)
    is_new_device = 0  # Historical baseline assumption
    
    vector = build_feature_vector(
        amount=float(amount), time_delta=24.0, geo_delta=0.0, 
        mcc_risk_score=mcc_risk, is_new_device=is_new_device, 
        freq_24h=1, avg_amt_ratio=1.0, hour_sin=0.0, hour_cos=1.0
    )
    
    point_id = str(uuid.uuid4())
    
    # Create Qdrant Point
    points_to_upload.append(PointStruct(
        id=point_id,
        vector=vector,
        payload={"transaction_id": txn_id, "merchant_id": merch_id}
    ))
    
    # Satisfy DA2 -> DA3 Bridge: Record in Vector_Points table
    try:
        pg_cur.execute(
            """INSERT INTO Vector_Points (qdrant_point_id, transaction_id, merchant_id) 
               VALUES (%s, %s, %s) 
               ON CONFLICT DO NOTHING""",
            (point_id, txn_id, merch_id)
        )
    except Exception as e:
        pg_conn.rollback()

# 4. Batch Upload to Qdrant (in chunks of 250 for reliability)
BATCH_SIZE = 250
total_uploaded = 0
for i in range(0, len(points_to_upload), BATCH_SIZE):
    batch = points_to_upload[i:i + BATCH_SIZE]
    q_client.upsert(collection_name=COLLECTION_NAME, points=batch)
    total_uploaded += len(batch)
    print(f"  Uploaded {total_uploaded}/{len(points_to_upload)} points...")

pg_conn.commit()
pg_cur.close()
pg_conn.close()

print(f"✅ Successfully migrated {len(rows)} PostgreSQL transactions into Qdrant Vectors!")
