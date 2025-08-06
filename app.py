import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import pandas as pd
import os

# CSV log file
log_file = "meal_attendance_log.csv"

# Initialize CSV if not present
if not os.path.exists(log_file):
    df = pd.DataFrame(columns=["Timestamp", "QR_Data"])
    df.to_csv(log_file, index=False)

# Load log
df = pd.read_csv(log_file)

st.set_page_config(page_title="QR Meal Scanner", page_icon="🍽️")
st.title("🍽️ Meal Attendance QR Scanner (Streamlit Cloud)")
st.metric("🍽️ Total Students Counted", len(df))

# Handle scanned QR data from frontend
qr_data = st.experimental_get_query_params().get("scanned", [None])[0]
if qr_data:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = pd.DataFrame([[current_time, qr_data]], columns=["Timestamp", "QR_Data"])
    new_entry.to_csv(log_file, mode="a", header=False, index=False)
    st.success(f"✅ Scanned and logged: {qr_data}")
    st.experimental_set_query_params(scanned=None)

# Load the HTML QR scanner
with open("qr_component.html", "r") as f:
    html_content = f.read()

components.html(html_content, height=600)

