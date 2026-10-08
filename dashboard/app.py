import streamlit as st
import psycopg2
import pandas as pd
import time

# -------------------------------------------------------------------
# Database Connection Configuration
# -------------------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "fraud_detection",
    "user": "postgres",
    "password": "root",
}


def get_connection():
    """Return a fresh psycopg2 connection to PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def fetch_df(query, params=None):
    """Fetch query results as a clean Pandas DataFrame without DBAPI warnings."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if cur.description:
                cols = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=cols)
            return pd.DataFrame()


# -------------------------------------------------------------------
# Streamlit Page Setup
# -------------------------------------------------------------------
st.set_page_config(
    page_title="RT-AFDE • Fraud Engine Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------
# Neobrutalist Theme & 100% Contrast Fixes
# -------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Space+Mono:wght@400;700&display=swap');

:root {
    --nb-bg:        #FFFDF7;
    --nb-black:     #121212;
    --nb-yellow:    #FFE156;
    --nb-pink:      #FF6B9D;
    --nb-blue:      #4ECDC4;
    --nb-green:     #A8E06E;
    --nb-orange:    #FF8C42;
    --nb-purple:    #C77DFF;
    --nb-border:    3px solid #121212;
    --nb-shadow:    5px 5px 0px #121212;
    --nb-shadow-sm: 3px 3px 0px #121212;
}

/* Force light canvas background */
.stApp {
    background-color: var(--nb-bg) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* CRITICAL CONTRAST FIX 1: Solid black text across all standard elements */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp label, .stApp span:not([class*="dvn"]), .stApp strong, .stApp b, .stApp em,
.stApp div[data-testid="stMarkdownContainer"] p,
.stApp div[data-testid="stMarkdownContainer"] li,
.stApp [data-testid="stWidgetLabel"] * {
    color: #121212 !important;
}

/* CRITICAL CONTRAST FIX 2: High-contrast yellow badge for ALL inline code tags (`code`) */
code, 
.stApp code, 
.stMarkdown code, 
div[data-testid="stMarkdownContainer"] code, 
p code, 
li code, 
span code,
.nb-card code {
    background-color: #FFE156 !important;
    color: #121212 !important;
    border: 1.5px solid #121212 !important;
    border-radius: 4px !important;
    padding: 2px 7px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.88em !important;
    font-weight: 800 !important;
    box-shadow: 2px 2px 0px #121212 !important;
    display: inline-block !important;
    margin: 1px 3px !important;
}

/* Headings */
h1 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 2.6rem !important;
    font-weight: 800 !important;
    letter-spacing: -1.2px !important;
    margin-bottom: 6px !important;
    color: #121212 !important;
}
h2 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    border-bottom: 3.5px solid #121212 !important;
    padding-bottom: 8px !important;
    margin-top: 14px !important;
    margin-bottom: 14px !important;
    color: #121212 !important;
}

/* CRITICAL FIX: Make Sidebar Reopen Button permanently visible and styled */
header[data-testid="stHeader"] {
    background: transparent !important;
    z-index: 99999 !important;
}
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    position: fixed !important;
    top: 14px !important;
    left: 14px !important;
    background-color: #FFE156 !important;
    border: 3.5px solid #121212 !important;
    box-shadow: 4px 4px 0px #121212 !important;
    border-radius: 0px !important;
    z-index: 9999999 !important;
    width: 44px !important;
    height: 44px !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
}
[data-testid="collapsedControl"]:hover {
    background-color: #ffd214 !important;
    transform: translate(2px, 2px) !important;
    box-shadow: 2px 2px 0px #121212 !important;
}
[data-testid="collapsedControl"] button {
    background: transparent !important;
    border: none !important;
    width: 100% !important;
    height: 100% !important;
}
[data-testid="collapsedControl"] svg {
    fill: #121212 !important;
    color: #121212 !important;
    stroke: #121212 !important;
    stroke-width: 1.5px !important;
    width: 24px !important;
    height: 24px !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: var(--nb-yellow) !important;
    border-right: 4px solid #121212 !important;
}
section[data-testid="stSidebar"] * {
    color: #121212 !important;
}

/* Neobrutalist Buttons */
.stButton > button {
    background-color: var(--nb-yellow) !important;
    color: #121212 !important;
    border: var(--nb-border) !important;
    border-radius: 0px !important;
    box-shadow: var(--nb-shadow) !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.1s ease !important;
}
.stButton > button:hover {
    transform: translate(2px, 2px) !important;
    box-shadow: 3px 3px 0px #121212 !important;
    background-color: #ffd214 !important;
}
.stButton > button:active {
    transform: translate(5px, 5px) !important;
    box-shadow: 0px 0px 0px #121212 !important;
}

/* Form Submit Button */
.stFormSubmitButton > button {
    background-color: var(--nb-green) !important;
    color: #121212 !important;
    border: var(--nb-border) !important;
    border-radius: 0px !important;
    box-shadow: var(--nb-shadow) !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    padding: 0.7rem 1.8rem !important;
}
.stFormSubmitButton > button:hover {
    transform: translate(2px, 2px) !important;
    box-shadow: 3px 3px 0px #121212 !important;
    background-color: #8ed24c !important;
}

/* Inputs & Form Fields */
.stTextInput input, .stNumberInput input {
    border: var(--nb-border) !important;
    border-radius: 0px !important;
    font-family: 'Space Mono', monospace !important;
    background: #FFFFFF !important;
    color: #121212 !important;
    box-shadow: var(--nb-shadow-sm) !important;
    font-weight: 700 !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #121212 !important;
    box-shadow: 4px 4px 0px var(--nb-pink) !important;
}

/* Selectboxes & Radio groups */
.stSelectbox > div > div {
    border: var(--nb-border) !important;
    border-radius: 0px !important;
    box-shadow: var(--nb-shadow-sm) !important;
    background: #FFFFFF !important;
    font-weight: 700 !important;
}
.stSelectbox [data-baseweb="select"] * {
    color: #121212 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    border-bottom: 3.5px solid #121212 !important;
}
.stTabs [data-baseweb="tab"] {
    border: 3px solid #121212 !important;
    border-bottom: none !important;
    background: #FFFFFF !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    font-size: 0.85rem !important;
    padding: 8px 18px !important;
    border-radius: 0px !important;
    color: #121212 !important;
}
.stTabs [aria-selected="true"] {
    background: var(--nb-yellow) !important;
}

/* Dataframe box */
.stDataFrame {
    border: var(--nb-border) !important;
    box-shadow: var(--nb-shadow) !important;
    border-radius: 0px !important;
    background: #FFFFFF !important;
}

/* Custom Neobrutalist Cards */
.nb-card {
    background: #FFFFFF;
    border: var(--nb-border);
    box-shadow: var(--nb-shadow);
    padding: 18px 22px;
    margin-bottom: 18px;
}
.nb-card-yellow { background: #FFF8CC; }
.nb-card-blue   { background: #D9F7F5; }
.nb-card-pink   { background: #FFE3ED; }
.nb-card-green  { background: #E7FAD2; }
.nb-card-purple { background: #F1E2FF; }
.nb-card-orange { background: #FFE6D6; }

.nb-card h3 {
    margin-top: 0;
    font-size: 1.25rem;
    font-weight: 800;
    border-bottom: 2px solid #121212;
    padding-bottom: 6px;
    margin-bottom: 10px;
    color: #121212 !important;
}
.nb-card p, .nb-card li, .nb-card strong {
    font-size: 0.95rem;
    line-height: 1.55;
    margin-bottom: 4px;
    color: #121212 !important;
}
.nb-badge {
    display: inline-block;
    background: #FFE156 !important;
    color: #121212 !important;
    border: 2px solid #121212 !important;
    box-shadow: 2px 2px 0px #121212 !important;
    padding: 2px 8px;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    font-weight: 800 !important;
    text-transform: uppercase;
    margin-right: 6px;
}

/* Metric widgets */
div[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: var(--nb-border) !important;
    box-shadow: var(--nb-shadow-sm) !important;
    padding: 10px 14px !important;
    border-radius: 0px !important;
}
div[data-testid="stMetric"] label {
    font-family: 'Space Mono', monospace !important;
    font-weight: 800 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    color: #121212 !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #121212 !important;
    font-weight: 800 !important;
}

/* Splash Hero Screen */
.splash-hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 55vh;
    text-align: center;
    padding: 20px;
}
.splash-icon {
    font-size: 5.5rem;
    filter: drop-shadow(4px 4px 0px #121212);
}
.splash-title {
    font-size: 4rem;
    font-weight: 900;
    letter-spacing: -2.5px;
    margin-top: 4px;
    margin-bottom: 0px;
    color: #121212 !important;
}
.splash-sub {
    font-family: 'Space Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 6px;
    color: #121212 !important;
}

#MainMenu, footer { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)


# ===================================================================
# Session State: Splash Screen Control (Runs ONCE, No Replay Bloat)
# ===================================================================
if "splash_done" not in st.session_state:
    st.session_state.splash_done = False

if not st.session_state.splash_done:
    st.markdown(
        """
    <div class="splash-hero">
        <div class="splash-icon">🛡️</div>
        <div class="splash-title">RT-AFDE</div>
        <div class="splash-sub">Real-Time Anomaly & Fraud Detection Engine</div>
        <div style="margin: 16px 0;">
            <span class="nb-badge" style="background: #FFE156 !important; padding: 4px 12px;">POSTGRESQL 16</span>
            <span class="nb-badge" style="background: #4ECDC4 !important; padding: 4px 12px;">STRICT BCNF</span>
            <span class="nb-badge" style="background: #FF6B9D !important; padding: 4px 12px;">PL/PGSQL AUTOMATION</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col_s1, col_s2, col_s3 = st.columns([1, 1, 1])
    with col_s2:
        if st.button("⚡ ENTER DASHBOARD", use_container_width=True):
            st.session_state.splash_done = True
            st.rerun()

    time.sleep(1.0)
    st.session_state.splash_done = True
    st.rerun()


# ===================================================================
# Sidebar Navigation & Live Monitor
# ===================================================================
with st.sidebar:
    st.markdown(
        """
    <div style="text-align:center; padding: 6px 0 10px 0;">
        <span style="font-size:2.4rem; filter: drop-shadow(2px 2px 0px #121212);">🛡️</span>
        <div style="font-family:'Space Grotesk',sans-serif; font-weight:800; font-size:1.45rem; letter-spacing:-1px; color:#121212;">
            RT-AFDE
        </div>
        <div style="font-family:'Space Mono',monospace; font-size:0.68rem; text-transform:uppercase; letter-spacing:1px; font-weight:700; color:#121212;">
            DBMS Management GUI
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    menu = st.selectbox(
        "Select Action",
        [
            "View Data (READ)",
            "Add Record (INSERT)",
            "Modify Record (UPDATE)",
            "Remove Record (DELETE)",
            "About System",
        ],
        index=0,
    )

    st.markdown("---")
    st.markdown(
        "<p style='font-family:Space Mono,monospace; font-size:0.75rem; font-weight:800; text-transform:uppercase; color:#121212;'>🔴 LIVE DATABASE STATS</p>",
        unsafe_allow_html=True,
    )

    # Dynamic live metrics directly from PostgreSQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM Users;")
                u_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM Transactions;")
                t_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM Audit_Trail;")
                a_count = cur.fetchone()[0]

        st.metric("Total Users", f"{u_count:,}")
        st.metric("Transactions", f"{t_count:,}")
        st.metric("Audit Logs (1:1)", f"{a_count:,}")
    except Exception as e:
        st.caption(f"⚠️ Database connecting... ({e})")


# ===================================================================
# MODULE 1: READ OPERATION (VIEW DATA)
# ===================================================================
if menu == "View Data (READ)":
    st.header("📊 Database Table Inspector")

    st.markdown(
        """
    <div class="nb-card nb-card-blue">
        <h3>💡 Table Inspector Guide</h3>
        <p>Inspect any of the <strong>9 normalized tables</strong> in real time without writing SQL.</p>
        <p><strong>Review Tip:</strong> Open <code>transactions</code> to inspect the populated rows, or <code>audit_trail</code> to prove 1:1 automated parity maintained by the trigger.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    TABLES = [
        "users",
        "cards",
        "merchants",
        "transactions",
        "audit_trail",
        "user_devices",
        "merchant_cats",
        "vector_points",
        "fraud_alerts",
    ]

    col1, col2 = st.columns([1, 2])
    with col1:
        table = st.selectbox("Select Table to View", TABLES, index=0)

    table_meta = {
        "users": "👤 Users table with calculated risk levels ('LOW', 'MEDIUM', 'HIGH').",
        "cards": "💳 Cards table with SHA-256 hashed credit/debit card numbers.",
        "merchants": "🏪 Merchants table linked to MCC categories.",
        "transactions": "💸 Transactions table with timestamps, amounts, and geo-coordinates.",
        "audit_trail": "📜 Audit_Trail table populated automatically by trg_audit_txn on every insert.",
        "user_devices": "📱 User_Devices table with unique IP bindings per user.",
        "merchant_cats": "🏬 Merchant Categories (MCC) with pre-assigned risk levels.",
        "vector_points": "🧩 Vector bridge table (prepared for Qdrant similarity search in DA3).",
        "fraud_alerts": "🚨 Fraud alerts flagged by downstream similarity detection.",
    }

    with col2:
        st.markdown(
            f"""
        <div class="nb-card nb-card-yellow" style="padding:12px 16px; margin-top:26px;">
            <span class="nb-badge">SCHEMA</span> <strong style="color:#121212;">{table.upper()}</strong>
            <p style="margin:4px 0 0 0; font-size:0.9rem; color:#121212;">{table_meta.get(table, "")}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    try:
        df = fetch_df(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT 100;")
        st.write(f"Showing last 100 rows from **{table}** ({len(df)} returned):")
        st.dataframe(df, use_container_width=True, height=440)
    except Exception as e:
        st.error(f"❌ Failed to load table data: {e}")


# ===================================================================
# MODULE 2: INSERT OPERATION (TRIGGERS DEMO)
# ===================================================================
elif menu == "Add Record (INSERT)":
    st.header("➕ Insert New Transaction")

    st.markdown(
        """
    <div class="nb-card nb-card-green">
        <h3>⚡ Demonstrates BEFORE & AFTER Database Triggers</h3>
        <p>Submitting this form executes two automated database triggers in PostgreSQL:</p>
        <ul>
            <li><code>trg_validate_txn</code> <strong>(BEFORE INSERT):</strong> Intercepts and rejects any transaction where <code>amount <= 0</code> before disk write.</li>
            <li><code>trg_audit_txn</code> <strong>(AFTER INSERT):</strong> Automatically writes a corresponding log into <code>Audit_Trail</code>.</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Fetch available real Cards, Merchants, and Devices dynamically from PostgreSQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT card_id, user_id, card_type FROM Cards ORDER BY card_id LIMIT 50;")
                db_cards = cur.fetchall()
                cur.execute("SELECT merchant_id, merchant_name FROM Merchants ORDER BY merchant_id LIMIT 50;")
                db_merchants = cur.fetchall()
                cur.execute("SELECT device_id, user_id, ip_address FROM User_Devices ORDER BY device_id LIMIT 50;")
                db_devices = cur.fetchall()
    except Exception:
        db_cards, db_merchants, db_devices = [], [], []

    # Quick test presets
    st.markdown("### 🎯 Quick Test Presets")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        load_valid = st.button("🟢 Preset A: Valid Transaction ($150.00)", use_container_width=True)
    with col_p2:
        load_invalid = st.button("🔴 Preset B: Trigger Rejection Test (-$500.00)", use_container_width=True)

    def_amt = 150.00
    if load_invalid:
        def_amt = -500.00
    elif load_valid:
        def_amt = 150.00

    with st.form("insert_txn_form"):
        st.markdown("#### Transaction Parameters (Dynamically Populated from DB)")
        c1, c2, c3 = st.columns(3)
        with c1:
            if db_cards:
                card_options = {f"Card #{c[0]} (User #{c[1]} - {c[2]})": c[0] for c in db_cards}
                selected_card_label = st.selectbox("Select Card (FK -> Cards)", list(card_options.keys()))
                card_id = card_options[selected_card_label]
            else:
                card_id = st.number_input("Card ID", min_value=1, value=1)

        with c2:
            if db_merchants:
                merchant_options = {f"Merchant #{m[0]} ({m[1]})": m[0] for m in db_merchants}
                selected_merch_label = st.selectbox("Select Merchant (FK -> Merchants)", list(merchant_options.keys()))
                merchant_id = merchant_options[selected_merch_label]
            else:
                merchant_id = st.number_input("Merchant ID", min_value=1, value=1)

        with c3:
            if db_devices:
                device_options = {f"Device #{d[0]} ({d[2]} - User #{d[1]})": d[0] for d in db_devices}
                selected_dev_label = st.selectbox("Select Device (FK -> User_Devices)", list(device_options.keys()))
                device_id = device_options[selected_dev_label]
            else:
                device_id = st.number_input("Device ID", min_value=1, value=1)

        c4, c5, c6 = st.columns(3)
        with c4:
            amount = st.number_input("Amount ($)", value=def_amt, format="%.2f")
        with c5:
            lat = st.number_input("Latitude", value=12.9716, format="%.4f")
        with c6:
            long = st.number_input("Longitude", value=77.5946, format="%.4f")

        submitted = st.form_submit_button("Submit Transaction")

        if submitted:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO Transactions (card_id, merchant_id, device_id, amount, location_lat, location_long)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING transaction_id;
                            """,
                            (card_id, merchant_id, device_id, amount, lat, long),
                        )
                        new_id = cur.fetchone()[0]
                        conn.commit()

                st.success(f"✅ Transaction #{new_id} inserted successfully! Audit Trail automatically logged.")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Database Trigger Rejected Insert: {e}")


# ===================================================================
# MODULE 3: UPDATE OPERATION (STORED PROCEDURES)
# ===================================================================
elif menu == "Modify Record (UPDATE)":
    st.header("🔄 Update User Risk Profile / Details")

    st.markdown(
        """
    <div class="nb-card nb-card-purple">
        <h3>🧠 What This Demonstrates</h3>
        <p>Demonstrates two update methodologies:</p>
        <ul>
            <li><strong>Manual User Details Update:</strong> Direct SQL <code>UPDATE Users SET email = ...</code></li>
            <li><strong>Run Risk Scoring Procedure (PL/SQL):</strong> Invokes the enterprise stored procedure <code>CALL update_user_risk_profile(user_id)</code> which inspects 30-day transaction volume and spikes to recalculate risk scores.</li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Fetch dynamic list of users from PostgreSQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, first_name, last_name, email, risk_score FROM Users ORDER BY user_id;")
                db_users = cur.fetchall()
    except Exception:
        db_users = []

    option = st.radio("Choose Update Type", ["Manual User Details Update", "Run Risk Scoring Procedure (PL/SQL)"])

    if option == "Manual User Details Update":
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            if db_users:
                user_map = {f"User #{u[0]} - {u[1]} {u[2]} ({u[3]})": u[0] for u in db_users}
                sel_u_label = st.selectbox("Select Target User", list(user_map.keys()))
                user_id = user_map[sel_u_label]
            else:
                user_id = st.number_input("Target User ID", min_value=1, value=1)

        with col_u2:
            new_email = st.text_input("New Email Address", placeholder="newemail@example.com")

        if st.button("Update Email"):
            if not new_email:
                st.warning("Please enter an email address.")
            else:
                try:
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("UPDATE Users SET email = %s WHERE user_id = %s;", (new_email, user_id))
                            affected = cur.rowcount
                            conn.commit()

                    if affected > 0:
                        st.success(f"✅ User #{user_id} email updated to {new_email}")
                    else:
                        st.warning(f"⚠️ User #{user_id} not found.")
                except Exception as e:
                    st.error(f"❌ Update failed: {e}")

    elif option == "Run Risk Scoring Procedure (PL/SQL)":
        col_proc1, col_proc2 = st.columns([2, 1])
        with col_proc1:
            if db_users:
                user_proc_map = {f"User #{u[0]} - {u[1]} {u[2]} (Current Risk: {u[4]})": u[0] for u in db_users}
                sel_proc_label = st.selectbox("Target User for Stored Procedure", list(user_proc_map.keys()))
                user_id = user_proc_map[sel_proc_label]
            else:
                user_id = st.number_input("Target User ID for Stored Procedure", min_value=1, value=1)

        with col_proc2:
            st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
            run_proc = st.button("Execute `CALL update_user_risk_profile()`", use_container_width=True)

        if run_proc:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        # Fetch stats before execution
                        cur.execute("SELECT risk_score FROM Users WHERE user_id = %s;", (user_id,))
                        old_score_row = cur.fetchone()
                        old_score = old_score_row[0] if old_score_row else "N/A"

                        # Call Stored Procedure
                        cur.execute("CALL update_user_risk_profile(%s);", (user_id,))
                        conn.commit()

                        # Fetch updated status
                        cur.execute("SELECT risk_score FROM Users WHERE user_id = %s;", (user_id,))
                        updated_score = cur.fetchone()[0]

                st.success(f"✅ Procedure Executed! User #{user_id} risk score recalculated from **{old_score}** to: **{updated_score}**")
            except Exception as e:
                st.error(f"❌ Procedure failed: {e}")


# ===================================================================
# MODULE 4: DELETE OPERATION (REFERENTIAL INTEGRITY)
# ===================================================================
elif menu == "Remove Record (DELETE)":
    st.header("🗑️ Delete Record")
    st.warning("⚠️ Foreign Key constraints enforce integrity. Cards with active transactions cannot be deleted directly.")

    # Fetch users dynamically from database
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, first_name, last_name FROM Users ORDER BY user_id;")
                all_users = cur.fetchall()
    except Exception:
        all_users = []

    # One-click demo test user creation button
    st.markdown("### 🧪 Demo Helper: Quick Deletable Test User")
    st.caption("PostgreSQL blocks deleting users who have cards/txns. Click below to insert an isolated test user that CAN be deleted to prove normal deletes work!")
    if st.button("✨ Create Clean Deletable Test User"):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    test_email = f"delete_test_{int(time.time())}@example.com"
                    cur.execute(
                        "INSERT INTO Users (first_name, last_name, email) VALUES ('ToDelete', 'TestUser', %s) RETURNING user_id;",
                        (test_email,),
                    )
                    created_id = cur.fetchone()[0]
                    conn.commit()
            st.session_state["default_del_uid"] = created_id
            st.success(f"✅ Created isolated User #{created_id} ('{test_email}'). You can now delete them successfully below!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to create test user: {e}")

    col_d1, col_d2 = st.columns([1, 1.2])

    # Dynamic default deletion ID
    default_del_val = st.session_state.get("default_del_uid", all_users[0][0] if all_users else 1)

    with col_d1:
        user_id_to_del = st.number_input("User ID to Delete", min_value=1, value=int(default_del_val))

        if st.button("Delete User", use_container_width=True):
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM Users WHERE user_id = %s;", (user_id_to_del,))
                        affected = cur.rowcount
                        conn.commit()

                if affected > 0:
                    st.success(f"✅ User #{user_id_to_del} deleted successfully.")
                    if "default_del_uid" in st.session_state:
                        del st.session_state["default_del_uid"]
                else:
                    st.warning(f"⚠️ User #{user_id_to_del} not found.")
            except Exception as e:
                st.error(f"❌ FK Constraint Protection: Cannot delete user because linked active records exist. ({e})")

    with col_d2:
        st.markdown("### Linked Record Inspector")
        try:
            preview_query = """
                SELECT u.user_id, u.first_name, u.last_name, u.email, u.risk_score,
                       COUNT(DISTINCT c.card_id) AS cards,
                       COUNT(DISTINCT t.transaction_id) AS txns
                FROM Users u
                LEFT JOIN Cards c ON u.user_id = c.user_id
                LEFT JOIN Transactions t ON c.card_id = t.card_id
                WHERE u.user_id = %s
                GROUP BY u.user_id, u.first_name, u.last_name, u.email, u.risk_score;
            """
            user_preview = fetch_df(preview_query, (user_id_to_del,))

            if not user_preview.empty:
                row = user_preview.iloc[0]
                has_links = (row["cards"] > 0) or (row["txns"] > 0)
                st.markdown(
                    f"""
                <div class="nb-card">
                    <span class="nb-badge">RISK: {row['risk_score']}</span>
                    <h3 style="margin-top:8px; color:#121212;">{row['first_name']} {row['last_name']} (ID #{row['user_id']})</h3>
                    <p style="color:#121212;"><strong>Email:</strong> {row['email']}</p>
                    <p style="color:#121212;"><strong>Linked Cards:</strong> {row['cards']} | <strong>Transactions:</strong> {row['txns']}</p>
                    <p style="font-family:'Space Mono',monospace; font-size:0.82rem; font-weight:800; margin-top:8px; color:#121212;">
                        {'🔒 ACTIVE RECORDS DETECTED — DELETION WILL BE BLOCKED BY FK CONSTRAINTS' if has_links else '🟢 ISOLATED RECORD — SAFE TO DELETE (CASE B)'}
                    </p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.info(f"User #{user_id_to_del} not found in database.")
        except Exception:
            st.caption("Unable to fetch user preview.")


# ===================================================================
# MODULE 5: ABOUT SYSTEM
# ===================================================================
elif menu == "About System":
    st.markdown(
        """
    <div style="background:var(--nb-yellow); border:3px solid #121212; box-shadow:6px 6px 0px #121212; padding:26px; text-align:center; margin-bottom:22px;">
        <span style="font-size:3.5rem;">🛡️</span>
        <h1 style="font-size:2.8rem; margin:0; color:#121212;">RT-AFDE SYSTEM ARCHITECTURE</h1>
        <p style="font-family:'Space Mono',monospace; font-size:0.95rem; font-weight:800; text-transform:uppercase; margin-top:4px; color:#121212;">
            Real-Time Anomaly & Fraud Detection Engine • DA2 Coursework
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
        <div class="nb-card nb-card-blue">
            <h3>📋 Project Purpose</h3>
            <p><strong>RT-AFDE</strong> is a financial fraud prevention DBMS architecture that ingests transactions in real time, validates inputs via triggers, enforces 1:1 audit trails, and recalculates risk profiles.</p>
        </div>
        <div class="nb-card nb-card-yellow">
            <h3>🗄️ 9 BCNF Tables</h3>
            <ul>
                <li><code>Users</code>, <code>User_Devices</code>, <code>Cards</code></li>
                <li><code>Merchant_Cats</code>, <code>Merchants</code></li>
                <li><code>Transactions</code>, <code>Audit_Trail</code></li>
                <li><code>Vector_Points</code> (DA3), <code>Fraud_Alerts</code> (DA3)</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
        <div class="nb-card nb-card-green">
            <h3>⚙️ PL/pgSQL Database Objects</h3>
            <ul>
                <li><code>trg_validate_txn</code> <strong>(BEFORE INSERT):</strong> Rejects non-positive charges ($ <= 0).</li>
                <li><code>trg_audit_txn</code> <strong>(AFTER INSERT):</strong> Maintains 1:1 immutable audit trail logs.</li>
                <li><code>update_user_risk_profile()</code> <strong>(Procedure):</strong> Recomputes risk scores based on 30-day activity.</li>
                <li><code>resolve_device_and_flag()</code> <strong>(Function):</strong> Dynamic lookup/registration of client IPs.</li>
            </ul>
        </div>
        <div class="nb-card nb-card-purple">
            <h3>🛠️ Tech Stack</h3>
            <p><strong>DB:</strong> PostgreSQL 16 | <strong>Backend:</strong> PL/pgSQL</p>
            <p><strong>Connector:</strong> psycopg2-binary | <strong>UI:</strong> Streamlit</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
