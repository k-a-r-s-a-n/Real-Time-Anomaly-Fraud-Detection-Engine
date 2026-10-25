from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
import os

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Connect to local Qdrant
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

COLLECTION_NAME = "transaction_behaviour"

def init_qdrant():
    """Initialize the collection if it doesn't exist."""
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=9, distance=Distance.COSINE)
        )
        print("✅ Qdrant Collection Created")

def upsert_to_qdrant(feature_vector, merchant_id):
    """STEP 5a: Writes to Qdrant and returns the generated UUID."""
    point_id = str(uuid.uuid4())
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(
            id=point_id,
            vector=feature_vector,
            payload={"merchant_id": merchant_id}
        )]
    )
    return point_id

def search_qdrant(feature_vector, limit=5, exclude_id=None):
    """STEP 5b: Searches Qdrant for ANN similarity score."""
    try:
        if hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=COLLECTION_NAME,
                query=feature_vector,
                limit=limit + 1 if exclude_id else limit,
                with_payload=True
            )
            results = response.points
        else:
            results = client.search(
                collection_name=COLLECTION_NAME,
                query_vector=feature_vector,
                limit=limit + 1 if exclude_id else limit
            )
    except Exception as e:
        print(f"Error querying Qdrant: {e}")
        return 0.0

    # Filter out current point if exclude_id is supplied
    filtered = [r for r in results if exclude_id is None or str(r.id) != str(exclude_id)]
    return filtered[0].score if filtered else 0.0

def record_vector_point(db_cursor, qdrant_point_id, transaction_id, merchant_id):
    """STEP 6: The 1:1 Postgres Bridge Write. Ties Qdrant UUID to PG Transaction ID."""
    db_cursor.execute(
        """
        INSERT INTO Vector_Points (qdrant_point_id, transaction_id, merchant_id)
        VALUES (%s, %s, %s)
        """,
        (qdrant_point_id, transaction_id, merchant_id)
    )
