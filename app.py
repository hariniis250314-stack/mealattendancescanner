import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Meal Attendance Scanner", page_icon="🍽️")
st.title("🍽️ Meal Attendance Logger")

# Load master list
students_df = pd.read_csv("students.csv")

# Excel log file
log_file = "meal_log.xlsx"

# Load existing log or create new DataFrame
if os.path.exists(log_file):
    df = pd.read_excel(log_file)
else:
    df = pd.DataFrame(columns=["Student ID", "Name", "Date", "Time"])

# Input field
student_id = st.text_input("Enter your Student ID")

if st.button("Submit"):
    student_id = student_id.strip()
    match = students_df[students_df["StudentID"] == student_id]

    if not match.empty:
        name = match.iloc[0]["Name"]
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%I:%M %p")

        new_entry = pd.DataFrame([[student_id, name, date, time]],
                                 columns=["Student ID", "Name", "Date", "Time"])

        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_excel(log_file, index=False)

        st.success(f"✅ {name} ({student_id}) logged at {time} on {date}")
    else:
        st.error("❌ Student ID not found in master list.")

# Display total count
st.metric("Total Entries", len(df))



