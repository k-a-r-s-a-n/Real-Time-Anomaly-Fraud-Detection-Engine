import numpy as np
from sklearn.preprocessing import StandardScaler

# Simulated fit for the scaler (in production, this is fit on historical training data)
dummy_history = np.random.rand(100, 9) * 100 
scaler = StandardScaler()
scaler.fit(dummy_history)

def build_feature_vector(amount, time_delta, geo_delta, mcc_risk_score, is_new_device, freq_24h, avg_amt_ratio, hour_sin, hour_cos):
    """
    Converts transaction context into a purely numeric, 9-dimensional explainable vector.
    device_change_flag (is_new_device) is directly injected from PostgreSQL Step 1.
    """
    raw_features = np.array([
        amount, 
        time_delta, 
        geo_delta, 
        mcc_risk_score, 
        int(is_new_device),  # True -> 1, False -> 0
        freq_24h, 
        avg_amt_ratio, 
        hour_sin, 
        hour_cos
    ]).reshape(1, -1)

    # Scale the vector
    scaled_vector = scaler.transform(raw_features)
    return scaled_vector.flatten().tolist()
