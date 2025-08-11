import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Meal Attendance Scanner", page_icon="🍽️")

st.title("🍽️ Meal Attendance Logger")

# Load master student list
master_file = "GMS Trainees list.xlsx"
if os.path.exists(master_file):
    students_df = pd.read_excel(master_file)
else:
    st.error(f"❌ Master file not found: {master_file}. Upload it next to app.py and redeploy.")
    st.stop()

# Ensure correct column names
students_df.columns = students_df.columns.str.strip()

# Load or create log file
log_file = "meal_log.csv"
if os.path.exists(log_file):
    log_df = pd.read_csv(log_file)
else:
    log_df = pd.DataFrame(columns=["Student ID", "Student Name", "Timestamp"])

# Time restriction: Only allow between 8:00 PM and 9:30 PM
current_time = datetime.now().time()
start_time = datetime.strptime("20:00", "%H:%M").time()
end_time = datetime.strptime("21:30", "%H:%M").time()

if start_time <= current_time <= end_time:
    # Student input (last 4 digits of phone number)
    phone_last4 = st.text_input("Enter last 4 digits of your phone number")

    if st.button("Submit"):
        if phone_last4.strip() != "":
            # Match student
            match = students_df[students_df["Phone"].astype(str).str[-4:] == phone_last4]
            if not match.empty:
                student_id = match.iloc[0]["StudentID"]
                student_name = match.iloc[0]["Name"]

                # Prevent duplicate entries for the day
                today = datetime.now().date()
                if not ((log_df["Student ID"] == student_id) &
                        (pd.to_datetime(log_df["Timestamp"]).dt.date == today)).any():
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_entry = pd.DataFrame([[student_id, student_name, timestamp]],
                                             columns=["Student ID", "Student Name", "Timestamp"])
                    log_df = pd.concat([log_df, new_entry], ignore_index=True)
                    log_df.to_csv(log_file, index=False)
                    st.success(f"✅ {student_name} logged at {timestamp}")
                else:
                    st.warning("⚠️ You have already logged in today.")
            else:
                st.error("❌ No matching student found.")
        else:
            st.warning("Please enter a valid number.")
else:
    st.info("⏳ Attendance is closed. Available from 8:00 PM to 9:30 PM.")

# Show total count
st.metric("Total Entries Today",
          len(log_df[pd.to_datetime(log_df["Timestamp"]).dt.date == datetime.now().date()]))
