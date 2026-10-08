import psycopg2
try:
    conn = psycopg2.connect(
        host="localhost",
        port="5432",
        database="fraud_detection",
        user="postgres",
        password="root"   # ← Replace with your PostgreSQL password from Step 1
    )
    cur = conn.cursor()
    cur.execute("SELECT current_database(), version();")
    result = cur.fetchone()
    print(f"✅ Connected to database: {result[0]}")
    print(f"✅ PostgreSQL version: {result[1][:50]}...")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")