-- ============================================================
-- FUNCTION: validate_transaction()
-- Rejects transactions with non-positive amounts.
-- ============================================================
CREATE OR REPLACE FUNCTION validate_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.amount <= 0 THEN
        RAISE EXCEPTION 'Invalid transaction: amount must be positive (got %)', NEW.amount;
    END IF;
    RETURN NEW;  -- returning NEW allows the INSERT to proceed
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGER: fires BEFORE every INSERT on Transactions
-- ============================================================
CREATE OR REPLACE TRIGGER trg_validate_txn
BEFORE INSERT ON Transactions
FOR EACH ROW
EXECUTE FUNCTION validate_transaction();
-- ============================================================
-- FUNCTION: log_transaction_audit()
-- Automatically logs every new transaction into Audit_Trail.
-- ============================================================
CREATE OR REPLACE FUNCTION log_transaction_audit()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO Audit_Trail (transaction_id, action, action_time)
    VALUES (NEW.transaction_id, 'INSERT', now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGER: fires AFTER every INSERT on Transactions
-- ============================================================
CREATE OR REPLACE TRIGGER trg_audit_txn
AFTER INSERT ON Transactions
FOR EACH ROW
EXECUTE FUNCTION log_transaction_audit();
-- ============================================================
-- FUNCTION: resolve_device_and_flag()
-- Lookup-or-insert into User_Devices.
-- Returns: device_id (INT), is_new_device (BOOLEAN)
-- ============================================================
CREATE OR REPLACE FUNCTION resolve_device_and_flag(
    p_user_id INT,
    p_ip_address VARCHAR
)
RETURNS TABLE(device_id INT, is_new_device BOOLEAN)
LANGUAGE plpgsql AS $$
DECLARE
    existing_id INT;
BEGIN
    -- Check if this user+IP combination already exists
    SELECT ud.device_id INTO existing_id
    FROM User_Devices ud
    WHERE ud.user_id = p_user_id
      AND ud.ip_address = p_ip_address;

    IF existing_id IS NOT NULL THEN
        -- Known device: return it with flag = FALSE
        RETURN QUERY SELECT existing_id, FALSE;
    ELSE
        -- New device: insert a row, then return it with flag = TRUE
        INSERT INTO User_Devices (user_id, ip_address)
        VALUES (p_user_id, p_ip_address)
        RETURNING User_Devices.device_id INTO existing_id;

        RETURN QUERY SELECT existing_id, TRUE;
    END IF;
END;
$$;