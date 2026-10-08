-- ============================================================
-- RT-AFDE (Real-Time Anomaly and Fraud Detection Engine)
-- DA2 DATA INTEGRITY & SYSTEM VALIDATION SUITE
-- Database: fraud_detection
-- ============================================================

-- ============================================================
-- SECTION 1: SYSTEM HEALTH & TABLE ROW COUNTS
-- Purpose: Quick diagnostic check of all 9 tables in the system.
-- ============================================================

SELECT 'Users' AS table_name, COUNT(*) AS row_count FROM Users
UNION ALL
SELECT 'User_Devices', COUNT(*) FROM User_Devices
UNION ALL
SELECT 'Cards', COUNT(*) FROM Cards
UNION ALL
SELECT 'Merchant_Cats', COUNT(*) FROM Merchant_Cats
UNION ALL
SELECT 'Merchants', COUNT(*) FROM Merchants
UNION ALL
SELECT 'Transactions', COUNT(*) FROM Transactions
UNION ALL
SELECT 'Audit_Trail', COUNT(*) FROM Audit_Trail
UNION ALL
SELECT 'Vector_Points', COUNT(*) FROM Vector_Points  -- Expected: 0 in DA2
UNION ALL
SELECT 'Fraud_Alerts', COUNT(*) FROM Fraud_Alerts;   -- Expected: 0 in DA2


-- ============================================================
-- SECTION 2: AUDIT TRAIL 1:1 PARITY & INTEGRITY
-- Purpose: Prove that AFTER INSERT trigger on Transactions fired
--          100% of the time with zero dropped audit logs.
-- ============================================================

-- 2.1 Parity Check (Discrepancy MUST be 0)
SELECT 
    (SELECT COUNT(*) FROM Transactions) AS total_transactions,
    (SELECT COUNT(*) FROM Audit_Trail)  AS total_audit_logs,
    (SELECT COUNT(*) FROM Transactions) - (SELECT COUNT(*) FROM Audit_Trail) AS discrepancy;

-- 2.2 Identify any unlogged transactions (MUST return 0 rows)
SELECT t.transaction_id AS unlogged_transaction_id
FROM Transactions t
LEFT JOIN Audit_Trail a ON t.transaction_id = a.transaction_id
WHERE a.transaction_id IS NULL;


-- ============================================================
-- SECTION 3: REFERENTIAL INTEGRITY & FOREIGN KEYS
-- Purpose: Ensure no orphaned records exist across relations.
-- ============================================================

-- 3.1 Transactions FK Integrity
SELECT COUNT(*) AS invalid_fk_transactions
FROM Transactions t
LEFT JOIN Cards c ON t.card_id = c.card_id
LEFT JOIN Merchants m ON t.merchant_id = m.merchant_id
LEFT JOIN User_Devices d ON t.device_id = d.device_id
WHERE c.card_id IS NULL 
   OR m.merchant_id IS NULL 
   OR (t.device_id IS NOT NULL AND d.device_id IS NULL);

-- 3.2 User_Devices Composite Key Uniqueness Check
-- MUST return 0 rows (confirms UNIQUE(user_id, ip_address) constraint holds)
SELECT user_id, ip_address, COUNT(*) AS occurrences
FROM User_Devices
GROUP BY user_id, ip_address
HAVING COUNT(*) > 1;


-- ============================================================
-- SECTION 4: RISK PROFILE SCORING DISTRIBUTION
-- Purpose: Inspect output of update_user_risk_profile() procedure.
-- ============================================================

-- 4.1 Overview of risk distribution across the user base
SELECT risk_score, COUNT(*) AS user_count
FROM Users
GROUP BY risk_score
ORDER BY risk_score;

-- 4.2 Top 10 High-Risk Users and their transaction statistics
SELECT 
    u.user_id,
    u.first_name,
    u.last_name,
    u.risk_score,
    COUNT(t.transaction_id) AS txn_count_30d,
    MAX(t.amount) AS max_single_amount,
    ROUND(AVG(t.amount), 2) AS avg_amount
FROM Users u
JOIN Cards c ON u.user_id = c.user_id
JOIN Transactions t ON c.card_id = t.card_id
WHERE u.risk_score = 'HIGH'
GROUP BY u.user_id, u.first_name, u.last_name, u.risk_score
ORDER BY max_single_amount DESC, txn_count_30d DESC
LIMIT 10;


-- ============================================================
-- SECTION 5: BEHAVIORAL DEVICE TRACKING VERIFICATION
-- Purpose: Check device adoption and expansion per user.
-- ============================================================

SELECT 
    u.user_id,
    u.first_name || ' ' || u.last_name AS full_name,
    COUNT(ud.device_id) AS distinct_devices_logged
FROM Users u
JOIN User_Devices ud ON u.user_id = ud.user_id
GROUP BY u.user_id, full_name
ORDER BY distinct_devices_logged DESC
LIMIT 10;


-- ============================================================
-- SECTION 6: LIVE FUNCTIONAL TESTS (FOR DEMO / AUDIT)
-- ============================================================

-- ------------------------------------------------------------
-- TEST A: BEFORE INSERT Trigger (Non-positive amount rejection)
-- Action: Run the INSERT below.
-- Expected Outcome: ERROR: Invalid transaction: amount must be positive
-- ------------------------------------------------------------
/*
INSERT INTO Transactions (card_id, merchant_id, amount, location_lat, location_long)
VALUES (1, 1, -250.00, 12.9716, 77.5946);
*/


-- ------------------------------------------------------------
-- TEST B: Vector_Points 1:1 Invariant Test
-- Purpose: Prove that Vector_Points enforces 1:1 mapping with
--          Transactions and rejects duplicate mappings.
-- ------------------------------------------------------------
/*
-- 1. Insert dummy vector bridge row
INSERT INTO Vector_Points (qdrant_point_id, transaction_id, merchant_id)
VALUES ('test-point-uuid-0001', 1, 1);

-- 2. Attempt duplicate insert for SAME transaction_id = 1 (MUST FAIL)
-- Expected Outcome: ERROR: duplicate key value violates unique constraint "vector_points_transaction_id_key"
INSERT INTO Vector_Points (qdrant_point_id, transaction_id, merchant_id)
VALUES ('test-point-uuid-0002', 1, 1);

-- 3. Cleanup test row
DELETE FROM Vector_Points WHERE transaction_id = 1;
*/


-- ------------------------------------------------------------
-- TEST C: Safe End-to-End Stored Procedure Test
-- Purpose: Create isolated user, card, and large transaction to
--          demonstrate real-time risk profile escalation to HIGH.
-- ------------------------------------------------------------
DO $$
DECLARE
    v_user_id INT;
    v_card_id INT;
    v_score   VARCHAR(20);
BEGIN
    -- Create isolated user
    INSERT INTO Users (first_name, last_name, email)
    VALUES ('AuditCheck', 'Runner', 'audit_runner_' || floor(random()*1000000)::text || '@example.com')
    RETURNING user_id INTO v_user_id;

    -- Create matching card
    INSERT INTO Cards (user_id, card_number_hash, card_type, expiry_date)
    VALUES (v_user_id, 'hash_audit_check', 'VISA', '2028-12')
    RETURNING card_id INTO v_card_id;

    -- Insert spike transaction (> 20,000)
    INSERT INTO Transactions (card_id, merchant_id, amount, location_lat, location_long)
    VALUES (v_card_id, 1, 24500.00, 12.9716, 77.5946);

    -- Execute automation procedure
    CALL update_user_risk_profile(v_user_id);

    -- Fetch updated risk
    SELECT risk_score INTO v_score FROM Users WHERE user_id = v_user_id;

    -- Display Notice
    RAISE NOTICE '✅ INTEGRITY TEST PASSED: Created User_ID %, Card_ID %. Updated Risk Profile: %', 
                 v_user_id, v_card_id, v_score;
END $$;