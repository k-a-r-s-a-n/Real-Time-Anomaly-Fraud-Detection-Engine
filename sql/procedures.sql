-- ============================================================
-- PROCEDURE: update_user_risk_profile()
-- Recalculates Users.risk_score based on last 30 days of activity.
-- Uses OR'd conditions (patched version) — catches both
-- high-frequency card-testing AND large one-off fraud shapes.
-- ============================================================
CREATE OR REPLACE PROCEDURE update_user_risk_profile(p_user_id INT)
LANGUAGE plpgsql AS $$
DECLARE
    avg_amt     NUMERIC;
    max_amt     NUMERIC;
    txn_count   INT;
BEGIN
    -- Aggregate the user's transaction stats over the last 30 days
    SELECT COALESCE(AVG(t.amount), 0),
           COALESCE(MAX(t.amount), 0),
           COUNT(*)
    INTO avg_amt, max_amt, txn_count
    FROM Transactions t
    JOIN Cards c ON t.card_id = c.card_id
    WHERE c.user_id = p_user_id
      AND t.timestamp > now() - INTERVAL '30 days';

    -- Update risk score using OR'd conditions
    UPDATE Users
    SET risk_score = CASE
        WHEN txn_count > 50 THEN 'HIGH'
        WHEN max_amt > 20000 THEN 'HIGH'
        WHEN txn_count > 20 OR avg_amt > 5000 THEN 'MEDIUM'
        ELSE 'LOW'
    END
    WHERE user_id = p_user_id;
END;
$$;