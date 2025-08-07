import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- Page Config ---
st.set_page_config(page_title="Meal Attendance Scanner", page_icon="🍽️")
st.title("🍽️ Meal Attendance Logger")

# --- Reset Daily Log After 11PM ---
reset_time = time(23, 0)
now = datetime.now()
log_file = "meal_log.xlsx"

if now.time() >= reset_time and os.path.exists(log_file):
    os.remove(log_file)

# --- Load Master Student List ---
students_df = pd.read_csv("students.csv")  # Must exist in the same folder

# --- Load or Create Log File ---
if os.path.exists(log_file):
    df = pd.read_excel(log_file)
else:
    df = pd.DataFrame(columns=["Student ID", "Name", "Date", "Time"])

# --- Input Section ---
student_id = st.text_input("Enter your Student ID")

if st.button("Submit"):
    student_id = student_id.strip()
    if student_id != "":
        # Match ID
        match = students_df[students_df["Student ID"] == student_id]
        if not match.empty:
            student_name = match["Name"].values[0]
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M:%S")

            new_entry = pd.DataFrame([[student_id, student_name, current_date, current_time]],
                                     columns=["Student ID", "Name", "Date", "Time"])
            df = pd.concat([df, new_entry], ignore_index=True)
            df.to_excel(log_file, index=False)

            st.success(f"✅ {student_name} ({student_id}) logged at {current_time} on {current_date}")
        else:
            st.error("❌ Student ID not found in master list.")
    else:
        st.warning("Please enter a valid Student ID.")

# --- Display Total Entries ---
st.metric("Total Entries", len(df))

# --- Admin Access Section ---
st.markdown("---")
with st.expander("🔐 Admin Login"):
    admin_pass = st.text_input("Enter admin password", type="password")
    if admin_pass == "admin123":  # Change this to a secure password
        st.success("Welcome, Admin ✅")

        if not df.empty:
            with open(log_file, "rb") as file:
                st.download_button(
                    label="📥 Download Meal Log (Excel)",
                    data=file,
                    file_name="meal_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No entries found in the log.")
    elif admin_pass != "":
        st.error("Incorrect password ❌")






