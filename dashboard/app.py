import streamlit as st
import sqlite3
import pandas as pd
import os
import time
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="Smart Parking Dashboard", layout="wide")
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "smart_parking.db"))

# --- HELPER FUNCTIONS ---
def get_connection():
    return sqlite3.connect(DB_PATH)

def generate_demo_data():
    """Generates 3 days of synthetic historical data if the database is nearly empty for the presentation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM occupancy_readings")
    if cursor.fetchone()[0] < 100:
        st.toast("Generating historical demo data for Analytics & ML...")
        now = datetime.now()
        bays = ["A01", "A02", "A03"]
        
        for i in range(500):
            past_time = now - timedelta(hours=np.random.randint(0, 72), minutes=np.random.randint(0, 60))
            bay = np.random.choice(bays)
            
            # Create a realistic pattern: higher occupancy during daytime (8 AM - 5 PM)
            if 8 <= past_time.hour <= 17:
                status = np.random.choice(["OCCUPIED", "AVAILABLE"], p=[0.7, 0.3])
            else:
                status = np.random.choice(["OCCUPIED", "AVAILABLE"], p=[0.2, 0.8])
                
            dist = np.random.uniform(20, 45) if status == "OCCUPIED" else np.random.uniform(60, 200)
            
            cursor.execute('''
                INSERT INTO occupancy_readings (project_id, bay_id, occupancy_status, distance_cm, device_id, timestamp, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ("smart_parking", bay, status, dist, "ESP32_NODE_01", past_time.isoformat(), past_time.isoformat()))
        conn.commit()
    conn.close()

def get_historical_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM occupancy_readings", conn)
    conn.close()
    df['received_at'] = pd.to_datetime(df['received_at'])
    df['hour'] = df['received_at'].dt.hour
    return df

def get_latest_status():
    conn = get_connection()
    query = """
        SELECT bay_id, occupancy_status, distance_cm, received_at 
        FROM occupancy_readings 
        WHERE id IN (SELECT MAX(id) FROM occupancy_readings GROUP BY bay_id)
        ORDER BY bay_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- RUN DEMO GENERATOR ---
if os.path.exists(DB_PATH):
    generate_demo_data()

# --- UI LAYOUT ---
st.title("🚗 SMART PARKING INTELLIGENCE SYSTEM")
st.markdown("IoT Occupancy Monitoring & Predictive Demand | DeKUT Group 10")

if not os.path.exists(DB_PATH):
    st.error(f"Database not found at {DB_PATH}. Ensure the Python ingestion script is running.")
    st.stop()

st.sidebar.header("Dashboard Controls")
live_update = st.sidebar.checkbox("Enable Live Updates", value=True)

# Create Tabs
tab1, tab2, tab3 = st.tabs(["🔴 Live Status", "📈 Analytics & Trends", "🤖 ML Predictive Demand"])

# --- TAB 1: LIVE STATUS ---
with tab1:
    latest_data = get_latest_status()
    if not latest_data.empty:
        total_bays = 3
        occupied = len(latest_data[latest_data['occupancy_status'] == 'OCCUPIED'])
        available = total_bays - occupied
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Bays", total_bays)
        col2.metric("Available Bays", available)
        col3.metric("Occupied Bays", occupied)
        
        st.markdown("---")
        cols = st.columns(3)
        for index, row in latest_data.iterrows():
            bay = row['bay_id']
            status = row['occupancy_status']
            dist = row['distance_cm']
            timestamp = str(row['received_at']).split('.')[0].replace('T', ' ')
            
            card_color = "#28a745" if status == "AVAILABLE" else "#dc3545" if status == "OCCUPIED" else "#6c757d"
                
            with cols[index % 3]:
                st.markdown(f"""
                <div style="background-color: {card_color}; padding: 20px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h1 style="color: white; margin-bottom: 0px;">{bay}</h1>
                    <h3 style="color: white; margin-top: 0px;">{status}</h3>
                    <p style="font-size: 18px; margin-bottom: 5px;">Distance: {dist} cm</p>
                    <p style="font-size: 12px; margin-bottom: 0px;">Last updated: {timestamp}</p>
                </div>
                """, unsafe_allow_html=True)

# --- TAB 2: ANALYTICS & TRENDS ---
with tab2:
    st.subheader("Historical Occupancy Trends")
    hist_df = get_historical_data()
    
    if not hist_df.empty:
        # Group by hour and count occupied status
        trend_df = hist_df[hist_df['occupancy_status'] == 'OCCUPIED'].groupby('hour').size().reset_index(name='Occupied Count')
        
        fig = px.bar(trend_df, x='hour', y='Occupied Count', 
                     title="Peak Parking Hours (Historical Demand)",
                     labels={'hour': 'Time of Day (24H)', 'Occupied Count': 'Number of Parking Events'},
                     color='Occupied Count', color_continuous_scale='Reds')
        st.plotly_chart(fig, use_container_width=True)
        
        # Pie Chart for Utilization
        util_df = hist_df['occupancy_status'].value_counts().reset_index()
        util_df.columns = ['Status', 'Count']
        fig_pie = px.pie(util_df, values='Count', names='Status', title="Overall Bay Utilization", color='Status',
                         color_discrete_map={'AVAILABLE':'#28a745', 'OCCUPIED':'#dc3545', 'SENSOR_ERROR':'#6c757d'})
        st.plotly_chart(fig_pie, use_container_width=True)

# --- TAB 3: MACHINE LEARNING ---
with tab3:
    st.subheader("Predictive Demand Modeling (Random Forest)")
    st.markdown("This ML model learns from historical data to predict the probability of finding an empty parking spot at a specific time of day.")
    
    hist_df = get_historical_data()
    if len(hist_df) > 50:
        # Prepare ML data
        # Convert status to binary: 1 = OCCUPIED, 0 = AVAILABLE
        hist_df['is_occupied'] = hist_df['occupancy_status'].apply(lambda x: 1 if x == 'OCCUPIED' else 0)
        
        # Features (X) and Target (y)
        X = hist_df[['hour']]
        y = hist_df['is_occupied']
        
        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Prediction UI
        pred_hour = st.slider("Select an hour of the day to predict demand:", min_value=0, max_value=23, value=12, format="%d:00")
        
        # Predict probability
        prob = model.predict_proba([[pred_hour]])[0]
        occupied_prob = prob[1] * 100
        available_prob = prob[0] * 100
        
        st.markdown(f"### At **{pred_hour}:00**, the model predicts:")
        col_a, col_b = st.columns(2)
        col_a.metric("Chance of being OCCUPIED", f"{occupied_prob:.1f}%")
        col_b.metric("Chance of being AVAILABLE", f"{available_prob:.1f}%")
        
        if occupied_prob > 70:
            st.warning("⚠️ High demand expected. Recommend arriving early.")
        elif available_prob > 70:
            st.success("✅ Low demand expected. Plenty of parking available.")
        else:
            st.info("ℹ️ Moderate demand expected.")
    else:
        st.info("Gathering more data to train the Machine Learning model...")

if live_update:
    time.sleep(3)
    st.rerun()
    