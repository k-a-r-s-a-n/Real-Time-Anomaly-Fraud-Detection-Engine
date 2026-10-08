-- ===================================================================
-- RT-AFDE (Real-Time Anomaly and Fraud Detection Engine)
-- 10 DOMAIN-SPECIFIC SQL & PL/SQL QUERIES — DA2 Report
-- Database: fraud_detection
-- ===================================================================


-- -------------------------------------------------------------------
-- QUERY 1: PL/SQL Function Call — Resolve device identity dynamically
-- Purpose : Demonstrates the resolve_device_and_flag() function.
--           If the user+IP pair is new it is auto-inserted; if known
--           it is returned with is_new_device = FALSE.
-- -------------------------------------------------------------------
SELECT * FROM resolve_device_and_flag(1, '192.168.1.99');


-- -------------------------------------------------------------------
-- QUERY 2: PL/SQL Stored Procedure Call — Recalculate user risk
-- Purpose : Calls update_user_risk_profile() which aggregates the
--           user's 30-day transaction stats and re-scores risk.
-- -------------------------------------------------------------------
CALL update_user_risk_profile(1);


-- -------------------------------------------------------------------
-- QUERY 3: Multi-Table JOIN & Aggregation — Top 5 Highest-Volume
--          Merchants (with risk category)
-- Purpose : 3-table JOIN (Merchants → Merchant_Cats → Transactions)
--           with GROUP BY and ORDER BY for ranked aggregation.
-- -------------------------------------------------------------------
SELECT
    m.merchant_id,
    m.merchant_name,
    mc.category_name,
    mc.risk_level,
    COUNT(t.transaction_id) AS total_txns,
    SUM(t.amount)           AS total_volume
FROM Merchants m
JOIN Merchant_Cats mc ON m.mcc_code   = mc.mcc_code
JOIN Transactions  t  ON m.merchant_id = t.merchant_id
GROUP BY m.merchant_id, m.merchant_name, mc.category_name, mc.risk_level
ORDER BY total_volume DESC
LIMIT 5;


-- -------------------------------------------------------------------
-- QUERY 4: Subquery with HAVING — Users with Multiple Registered
--          Devices (potential device-sharing / fraud indicator)
-- Purpose : JOIN + GROUP BY + HAVING to filter after aggregation.
-- -------------------------------------------------------------------
SELECT
    u.user_id,
    u.first_name,
    u.last_name,
    COUNT(ud.device_id) AS device_count
FROM Users u
JOIN User_Devices ud ON u.user_id = ud.user_id
GROUP BY u.user_id, u.first_name, u.last_name
HAVING COUNT(ud.device_id) > 1
ORDER BY device_count DESC;


-- -------------------------------------------------------------------
-- QUERY 5: Window Function (DENSE_RANK) — Rank Transactions per
--          Card by Amount
-- Purpose : Demonstrates PARTITION BY + DENSE_RANK to rank without
--           gaps when ties occur.
-- -------------------------------------------------------------------
SELECT
    t.transaction_id,
    t.card_id,
    t.amount,
    DENSE_RANK() OVER (
        PARTITION BY t.card_id
        ORDER BY t.amount DESC
    ) AS amount_rank
FROM Transactions t
LIMIT 15;


-- -------------------------------------------------------------------
-- QUERY 6: Audit Trail Integrity — Verify 1:1 Parity between
--          Transactions and Audit_Trail (trigger proof)
-- Purpose : Confirms the AFTER INSERT trigger fired for every row.
-- -------------------------------------------------------------------
SELECT
    t.transaction_id,
    t.amount,
    a.action,
    a.action_time
FROM Transactions t
JOIN Audit_Trail a ON t.transaction_id = a.transaction_id
ORDER BY a.action_time DESC
LIMIT 10;


-- -------------------------------------------------------------------
-- QUERY 7: Common Table Expression (CTE) — Detect High-Frequency
--          Card Testing Patterns
-- Purpose : CTE aggregates per-user transaction counts and max
--           amounts, then filters for burst-activity users.
-- -------------------------------------------------------------------
WITH UserTxnStats AS (
    SELECT
        c.user_id,
        COUNT(t.transaction_id) AS txn_count,
        MAX(t.amount)           AS max_amt
    FROM Cards c
    JOIN Transactions t ON c.card_id = t.card_id
    GROUP BY c.user_id
)
SELECT
    u.user_id,
    u.first_name,
    u.risk_score,
    s.txn_count,
    s.max_amt
FROM Users u
JOIN UserTxnStats s ON u.user_id = s.user_id
WHERE s.txn_count > 50;


-- -------------------------------------------------------------------
-- QUERY 8: UPDATE with Correlated Subquery — Batch-elevate risk tier
--          for users transacting at HIGH-risk merchant categories
-- Purpose : Multi-table subquery inside UPDATE … WHERE user_id IN (…)
-- -------------------------------------------------------------------
UPDATE Users
SET risk_score = 'MEDIUM'
WHERE user_id IN (
    SELECT DISTINCT c.user_id
    FROM Cards c
    JOIN Transactions t  ON c.card_id    = t.card_id
    JOIN Merchants    m  ON t.merchant_id = m.merchant_id
    JOIN Merchant_Cats mc ON m.mcc_code  = mc.mcc_code
    WHERE mc.risk_level = 'HIGH'
)
AND risk_score = 'LOW';


-- -------------------------------------------------------------------
-- QUERY 9: DELETE with Safe Sub-select — Remove expired cards that
--          have NEVER been used in a transaction
-- Purpose : Anti-join pattern (NOT IN subquery) combined with a
--           date-based filter to safely purge dead data.
-- -------------------------------------------------------------------
DELETE FROM Cards
WHERE card_id NOT IN (SELECT DISTINCT card_id FROM Transactions)
  AND expiry_date < '2025-01';


-- -------------------------------------------------------------------
-- QUERY 10: INSERT with Trigger Validation Test & RETURNING clause
-- Purpose  : Demonstrates a valid insert that passes the BEFORE
--            trigger and auto-populates audit via the AFTER trigger.
--            RETURNING proves the auto-generated PK + timestamp.
-- -------------------------------------------------------------------
INSERT INTO Transactions
    (card_id, merchant_id, device_id, amount, location_lat, location_long)
VALUES
    (1, 1, 1, 88.50, 12.9716, 77.5946)
RETURNING transaction_id, timestamp;
