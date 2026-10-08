-- ============================================================
-- RT-AFDE: Complete Schema — 8 Tables (DA2)
-- Run this ONCE on a fresh database.
-- ============================================================

-- 1. Users (no dependencies)
CREATE TABLE Users (
    user_id      SERIAL PRIMARY KEY,
    first_name   VARCHAR(50) NOT NULL,
    last_name    VARCHAR(50) NOT NULL,
    email        VARCHAR(100) UNIQUE NOT NULL,
    risk_score   VARCHAR(20) DEFAULT 'LOW',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. User_Devices (depends on Users)
CREATE TABLE User_Devices (
    device_id     SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES Users(user_id),
    ip_address    VARCHAR(45) NOT NULL,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, ip_address)
);

-- 3. Cards (depends on Users)
CREATE TABLE Cards (
    card_id          SERIAL PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES Users(user_id),
    card_number_hash VARCHAR(256) NOT NULL,
    card_type        VARCHAR(20) NOT NULL,
    expiry_date      VARCHAR(7) NOT NULL
);

-- 4. Merchant_Cats (no dependencies)
CREATE TABLE Merchant_Cats (
    mcc_code      VARCHAR(10) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    risk_level    VARCHAR(20) NOT NULL
);

-- 5. Merchants (depends on Merchant_Cats)
CREATE TABLE Merchants (
    merchant_id   SERIAL PRIMARY KEY,
    merchant_name VARCHAR(100) NOT NULL,
    mcc_code      VARCHAR(10) NOT NULL REFERENCES Merchant_Cats(mcc_code)
);

-- 6. Transactions (depends on Cards, Merchants, User_Devices)
CREATE TABLE Transactions (
    transaction_id SERIAL PRIMARY KEY,
    card_id        INT NOT NULL REFERENCES Cards(card_id),
    merchant_id    INT NOT NULL REFERENCES Merchants(merchant_id),
    device_id      INT REFERENCES User_Devices(device_id),
    amount         DECIMAL(10,2) NOT NULL,
    timestamp      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location_lat   DECIMAL(9,6) NOT NULL,
    location_long  DECIMAL(9,6) NOT NULL
);

-- 7. Vector_Points (depends on Transactions, Merchants)
--    This table will remain EMPTY during DA2.
--    It exists now so the schema is architecturally complete.
--    DA3's orchestrator will populate it on every Qdrant upsert.
CREATE TABLE Vector_Points (
    qdrant_point_id VARCHAR(36) PRIMARY KEY,
    transaction_id  INT UNIQUE NOT NULL REFERENCES Transactions(transaction_id),
    merchant_id     INT NOT NULL REFERENCES Merchants(merchant_id)
);

-- 8. Fraud_Alerts (depends on Transactions)
CREATE TABLE Fraud_Alerts (
    alert_id         SERIAL PRIMARY KEY,
    transaction_id   INT UNIQUE NOT NULL REFERENCES Transactions(transaction_id),
    similarity_score FLOAT NOT NULL,
    decision_status  VARCHAR(20) NOT NULL
);

-- 9. Audit_Trail (depends on Transactions)
CREATE TABLE Audit_Trail (
    audit_id       SERIAL PRIMARY KEY,
    transaction_id INT NOT NULL REFERENCES Transactions(transaction_id),
    action         VARCHAR(20) NOT NULL,
    action_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);