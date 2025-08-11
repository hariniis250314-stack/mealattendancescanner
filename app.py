import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Meal Attendance Scanner", page_icon="🍽️")
st.title("🍽️ Meal Attendance Logger")

# ---------- Helpers ----------
def normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "").replace("_", "")

def auto_find_columns(df: pd.DataFrame):
    # drop stray index columns like "Unnamed: 0"
    clean_df = df.loc[:, ~df.columns.str.contains(r"^unnamed", case=False)]
    # build map: normalized -> original
    norm_map = {normalize(c): c for c in clean_df.columns}

    # try common variants
    id_candidates = ["studentid", "id", "rollno", "rollnumber"]
    name_candidates = ["name", "studentname", "fullname"]

    id_col = next((norm_map[n] for n in id_candidates if n in norm_map), None)
    name_col = next((norm_map[n] for n in name_candidates if n in norm_map), None)
    return clean_df, id_col, name_col

# ---------- Load master list ----------
try:
    students_raw = pd.read_csv("students.csv", dtype=str)
except FileNotFoundError:
    st.error("❌ `students.csv` not found. Place it next to `app.py` and redeploy.")
    st.stop()
except Exception as e:
    st.error(f"❌ Failed to read `students.csv`: {e}")
    st.stop()

students_df, id_col, name_col = auto_find_columns(students_raw)

if id_col is None or name_col is None:
    st.error(
        "❌ Could not find required columns in `students.csv`.\n\n"
        "Expected headers similar to:\n"
        "- ID column: StudentID / ID / RollNo / RollNumber\n"
        "- Name column: Name / StudentName / FullName\n\n"
        f"Detected columns: {list(students_raw.columns)}"
    )
    st.stop()

# ---------- Load or create log file ----------
log_file = "meal_log.xlsx"
if os.path.exists(log_file):
    try:
        df = pd.read_excel(log_file, dtype=str)
    except Exception:
        df = pd.DataFrame(columns=["Student ID", "Name", "Date", "Time"])
else:
    df = pd.DataFrame(columns=["Student ID", "Name", "Date", "Time"])

# ---------- Input ----------
student_id = st.text_input("Enter your Student ID")

if st.button("Submit"):
    sid = (student_id or "").strip()
    if not sid:
        st.warning("Please enter a valid Student ID.")
    else:
        # case-insensitive match after stripping
        match = students_df[
            students_df[id_col].astype(str).str.strip().str.upper() == sid.upper()
        ]
        if not match.empty:
            student_name = match[name_col].iloc[0]
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            new_row = pd.DataFrame(
                [[sid, student_name, date_str, time_str]],
                columns=["Student ID", "Name", "Date", "Time"]
            )
            df = pd.concat([df, new_row], ignore_index=True)
            # write Excel
            try:
                df.to_excel(log_file, index=False)
            except Exception as e:
                st.error(f"❌ Failed to write log file: {e}")
            else:
                st.success(f"✅ {student_name} ({sid}) logged at {time_str} on {date_str}")
        else:
            st.error("❌ Student ID not found in master list.")

# ---------- Summary ----------
st.metric("Total Entries", len(df))
# --- Admin Access Section ---
st.markdown("---")
with st.expander("🔐 Admin Login"):
    admin_pass = st.text_input("Enter admin password", type="password", key="admin_password")

    if admin_pass == "admin123":  # ← change to a secure password / use secrets in prod
        st.success("Welcome, Admin ✅")

        # Admin-only refresh button
        if st.button("🔁 Refresh entries", key="admin_refresh"):
            st.rerun()

        # Admin-only download
        if not df.empty and os.path.exists(log_file):
            with open(log_file, "rb") as file:
                st.download_button(
                    label="📥 Download Meal Log (Excel)",
                    data=file,
                    file_name="meal_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_log_xlsx"
                )
        else:
            st.warning("No entries found yet.")
    elif admin_pass:
        st.error("Incorrect password ❌")
