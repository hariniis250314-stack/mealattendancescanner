import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Meal Attendance Scanner", page_icon="🍽️")

st.title("🍽️ Meal Attendance Logger")

# Load or create CSV
log_file = "meal_log.csv"

if os.path.exists(log_file):
    df = pd.read_csv(log_file)
else:
    df = pd.DataFrame(columns=["Student ID", "Timestamp"])

# Student input
student_id = st.text_input("Enter your Student ID")

if st.button("Submit"):
    if student_id.strip() != "":
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_entry = pd.DataFrame([[student_id, timestamp]], columns=["Student ID", "Timestamp"])
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(log_file, index=False)
        st.success(f"✅ {student_id} logged at {timestamp}")
    else:
        st.warning("Please enter a valid Student ID")

# Display total count
st.metric("Total Entries", len(df))

