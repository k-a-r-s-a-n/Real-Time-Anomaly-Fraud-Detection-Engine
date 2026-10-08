import psycopg2
from faker import Faker
import random
import hashlib
from datetime import datetime, timedelta
import numpy as np

# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "fraud_detection",
    "user": "postgres",
    "password": "root"  # <-- Update with your postgres password
}

NUM_USERS = 50          # Number of synthetic users
NUM_TRANSACTIONS = 2000 # Number of synthetic transactions to simulate

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# -------------------------------------------------------------
# Seed Data Definitions
# -------------------------------------------------------------
MCC_DATA = [
    ('5411', 'Grocery Stores & Supermarkets', 'LOW'),
    ('5812', 'Eating Places and Restaurants', 'LOW'),
    ('5311', 'Department Stores', 'LOW'),
    ('5541', 'Service Stations & Gas Stations', 'MEDIUM'),
    ('5732', 'Electronic Sales', 'MEDIUM'),
    ('4829', 'Wire Transfer & Money Orders', 'HIGH'),
    ('6012', 'Financial Institutions / ATMs', 'HIGH'),
    ('7995', 'Gambling & Betting Operations', 'HIGH'),
    ('5944', 'Jewelry and Precious Stones', 'HIGH'),
]

CARD_TYPES = ['VISA', 'MASTERCARD', 'AMEX', 'DISCOVER']

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def reset_database(cursor):
    """Clean tables and reset auto-increment counters."""
    print("🧹 Cleaning existing data...")
    cursor.execute("""
        TRUNCATE Users, User_Devices, Cards, Merchant_Cats, Merchants, 
                 Transactions, Vector_Points, Fraud_Alerts, Audit_Trail 
        RESTART IDENTITY CASCADE;
    """)

def seed_merchants(cursor):
    """Seed Merchant Categories and Merchants."""
    print("🏪 Seeding Merchant Categories and Merchants...")
    
    # Insert MCC Categories
    cursor.executemany(
        "INSERT INTO Merchant_Cats (mcc_code, category_name, risk_level) VALUES (%s, %s, %s)",
        MCC_DATA
    )
    
    # Generate 25 realistic Merchants linked to the MCC categories
    merchants = []
    for _ in range(25):
        mcc = random.choice(MCC_DATA)[0]
        name = fake.company().replace("'", "") + " Store"
        merchants.append((name, mcc))
        
    cursor.executemany(
        "INSERT INTO Merchants (merchant_name, mcc_code) VALUES (%s, %s)",
        merchants
    )

def seed_users_and_cards(cursor, num_users):
    """Generate Users and assign 1-3 Cards per user."""
    print(f"👥 Seeding {num_users} Users and their Cards...")
    
    card_id_map = {}  # user_id -> list of card_ids
    
    for _ in range(num_users):
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{first_name.lower()}.{last_name.lower()}.{random.randint(100, 9999)}@{fake.free_email_domain()}"
        
        cursor.execute(
            """
            INSERT INTO Users (first_name, last_name, email)
            VALUES (%s, %s, %s)
            RETURNING user_id;
            """,
            (first_name, last_name, email)
        )
        user_id = cursor.fetchone()[0]
        card_id_map[user_id] = []
        
        # Assign 1 to 3 cards to this user
        num_cards = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
        for _ in range(num_cards):
            card_raw = fake.credit_card_number()
            card_hash = hashlib.sha256(card_raw.encode()).hexdigest()
            card_type = random.choice(CARD_TYPES)
            expiry = fake.credit_card_expire(start="now", end="+4y", date_format="%Y-%m")
            
            cursor.execute(
                """
                INSERT INTO Cards (user_id, card_number_hash, card_type, expiry_date)
                VALUES (%s, %s, %s, %s)
                RETURNING card_id;
                """,
                (user_id, card_hash, card_type, expiry)
            )
            card_id = cursor.fetchone()[0]
            card_id_map[user_id].append(card_id)
            
    return card_id_map

def generate_transactions(cursor, card_id_map, total_txns):
    """Generate transactions with mixed regular and anomalous behavior."""
    print(f"💳 Simulating {total_txns} transactions (Triggering PL/pgSQL Engine)...")
    
    # Fetch all merchant_ids
    cursor.execute("SELECT merchant_id FROM Merchants;")
    merchant_ids = [row[0] for row in cursor.fetchall()]
    
    users = list(card_id_map.keys())
    
    # Track primary home IP and base location per user for realism
    user_profiles = {}
    for uid in users:
        user_profiles[uid] = {
            "primary_ip": fake.ipv4(),
            "lat": float(fake.latitude()),
            "long": float(fake.longitude())
        }

    # Pre-designate special users to simulate specific fraud behaviors:
    card_tester_user = users[0]       # Will receive 55+ rapid transactions (burst)
    high_spender_user = users[1]      # Will receive a high single transaction (> 20,000)

    txn_count = 0
    base_time = datetime.now() - timedelta(days=25)

    # 1. Simulate Normal Transactions across the user base
    for _ in range(total_txns - 60):
        user_id = random.choice(users)
        card_id = random.choice(card_id_map[user_id])
        merchant_id = random.choice(merchant_ids)
        profile = user_profiles[user_id]
        
        # 10% chance of connecting from a novel IP address (device change)
        if random.random() < 0.10:
            ip_address = fake.ipv4()
        else:
            ip_address = profile["primary_ip"]

        # Resolve device using the PL/pgSQL function
        cursor.execute("SELECT device_id, is_new_device FROM resolve_device_and_flag(%s, %s)", (user_id, ip_address))
        device_id, _ = cursor.fetchone()

        # Regular transaction amounts (log-normal distribution)
        amount = round(float(np.random.lognormal(mean=3.5, sigma=0.8)), 2)
        amount = max(5.00, min(amount, 4500.00))

        # Minor location drift (+/- 0.05 degrees)
        lat = profile["lat"] + random.uniform(-0.05, 0.05)
        lon = profile["long"] + random.uniform(-0.05, 0.05)
        
        txn_time = base_time + timedelta(minutes=random.randint(1, 36000))

        cursor.execute(
            """
            INSERT INTO Transactions (card_id, merchant_id, device_id, amount, timestamp, location_lat, location_long)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (card_id, merchant_id, device_id, amount, txn_time, lat, lon)
        )
        txn_count += 1

    # 2. Simulate Fraud Shape A: Rapid Card-Testing Burst (> 50 transactions on card_tester_user)
    print(f"⚠️  Injecting card-testing burst pattern on User {card_tester_user}...")
    card_id_burst = card_id_map[card_tester_user][0]
    burst_time = datetime.now() - timedelta(days=2)
    for i in range(55):
        # Resolve novel device
        ip = f"198.51.100.{i + 1}"
        cursor.execute("SELECT device_id, is_new_device FROM resolve_device_and_flag(%s, %s)", (card_tester_user, ip))
        dev_id, _ = cursor.fetchone()
        
        amt = round(random.uniform(1.00, 15.00), 2)  # Micro charges
        burst_time += timedelta(seconds=random.randint(10, 45))
        
        cursor.execute(
            """
            INSERT INTO Transactions (card_id, merchant_id, device_id, amount, timestamp, location_lat, location_long)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (card_id_burst, random.choice(merchant_ids), dev_id, amt, burst_time, 13.0827, 80.2707)
        )
        txn_count += 1

    # 3. Simulate Fraud Shape B: Single High-Value Spike (> 20,000 on high_spender_user)
    print(f"⚠️  Injecting high-value spike pattern on User {high_spender_user}...")
    card_id_spike = card_id_map[high_spender_user][0]
    cursor.execute("SELECT device_id, is_new_device FROM resolve_device_and_flag(%s, %s)", (high_spender_user, fake.ipv4()))
    dev_id, _ = cursor.fetchone()
    
    cursor.execute(
        """
        INSERT INTO Transactions (card_id, merchant_id, device_id, amount, timestamp, location_lat, location_long)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (card_id_spike, random.choice(merchant_ids), dev_id, 28500.00, datetime.now() - timedelta(hours=3), 28.6139, 77.2090)
    )
    txn_count += 1

    print(f"✅ Finished writing {txn_count} transactions.")

def update_all_user_risk_scores(cursor, card_id_map):
    """Executes the update_user_risk_profile stored procedure for each user."""
    print("⚙️  Calling update_user_risk_profile() procedure across all users...")
    for user_id in card_id_map.keys():
        cursor.execute("CALL update_user_risk_profile(%s)", (user_id,))

# -------------------------------------------------------------
# Main Execution Flow
# -------------------------------------------------------------
def main():
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cur = conn.cursor()

        print("🚀 Starting synthetic mock data generation...")
        
        reset_database(cur)
        seed_merchants(cur)
        card_id_map = seed_users_and_cards(cur, NUM_USERS)
        generate_transactions(cur, card_id_map, NUM_TRANSACTIONS)
        update_all_user_risk_scores(cur, card_id_map)

        conn.commit()
        print("\n🎉 ALL DATA GENERATED & COMMITTED SUCCESSFULLY!")
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print("\n❌ Error during data generation:", e)
        raise e
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()