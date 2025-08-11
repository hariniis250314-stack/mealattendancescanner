import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ---------------- Page config ----------------
st.set_page_config(page_title="Meal Attendance Scanner", page_icon="🍽️")
st.title("🍽️ Meal Attendance Logger")

LOG_FILE = "meal_log.xlsx"
ADMIN_PASSWORD = "admin123"  # ⚠️ Change this (or use Streamlit Secrets in production)

# ---------------- Helpers ----------------
def _normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "").replace("_", "")

def _auto_find_columns(df: pd.DataFrame):
    """Find likely ID and Name columns (handles StudentID/ID and Name/FullName variants)."""
    # drop stray "Unnamed" index columns if any
    df = df.loc[:, ~df.columns.str.contains(r"^unnamed", case=False)]
    norm_map = {_normalize(c): c for c in df.columns}
    id_candidates = ["studentid", "id", "rollno", "rollnumber"]
    name_candidates = ["name", "studentname", "fullname"]
    id_col = next((norm_map[n] for n in id_candidates if n in norm_map), None)
    name_col = next((norm_map[n] for n in name_candidates if n in norm_map), None)
    return df, id_col, name_col

def file_mtime(path: str) -> float:
    return os.path.getmtime(path) if os.path.exists(path) else 0.0

# ---------------- Cached loaders keyed by file mtime ----------------
@st.cache_data(show_spinner=False)
def load_students_cached(mtime: float):
    raw = pd.read_csv("students.csv", dtype=str)
    df, id_col, name_col = _auto_find_columns(raw)
    return df, id_col, name_col

@st.cache_data(show_spinner=False)
def load_log_cached(path: str, mtime: float) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_excel(path, dtype=str)
    return pd.DataFrame(columns=["Student ID", "Name", "Date", "Time"])

# invisible bump to force cache re-key after writes (no refresh button)
if "cache_bump" not in st.session_state:
    st.session_state.cache_bump = 0

# ---------------- Load data ----------------
try:
    students_df, ID_COL, NAME_COL = load_students_cached(
        file_mtime("students.csv") + st.session_state.cache_bump
    )
except FileNotFoundError:
    st.error("❌ `students.csv` not found. Place it next to `app.py` and redeploy.")
    st.stop()
except Exception as e:
    st.error(f"❌ Failed to read `students.csv`: {e}")
    st.stop()

if ID_COL is None or NAME_COL is None:
    st.error(
        "❌ Could not detect required columns in `students.csv`.\n\n"
        "Expected headers like: StudentID / ID / RollNo  and  Name / StudentName / FullName.\n\n"
        f"Detected columns: {list(students_df.columns)}"
    )
    st.stop()

df = load_log_cached(LOG_FILE, file_mtime(LOG_FILE) + st.session_state.cache_bump)

# ---------------- Input ----------------
student_id = st.text_input("Enter your Student ID", key="student_input")

if st.button("Submit", key="submit_btn"):
    sid = (student_id or "").strip()
    if not sid:
        st.warning("Please enter a valid Student ID.")
    else:
        match = students_df[
            students_df[ID_COL].astype(str).str.strip().str.upper() == sid.upper()
        ]
        if not match.empty:
            student_name = match[NAME_COL].iloc[0]
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            new_row = pd.DataFrame(
                [[sid, student_name, date_str, time_str]],
                columns=["Student ID", "Name", "Date", "Time"]
            )
            df = pd.concat([df, new_row], ignore_index=True)

            try:
                df.to_excel(LOG_FILE, index=False)
            except Exception as e:
                st.error(f"❌ Failed to write log file: {e}")
            else:
                # bump cache key & rerun so UI reflects the latest file immediately
                st.session_state.cache_bump += 1
                st.success(f"✅ {student_name} ({sid}) logged at {time_str} on {date_str}")
                st.rerun()
        else:
            st.error("❌ Student ID not found in master list.")

# ---------------- Summary ----------------
df = load_log_cached(LOG_FILE, file_mtime(LOG_FILE) + st.session_state.cache_bump)
st.metric("Total Entries", len(df))

# ---------------- Admin Section (download only) ----------------
st.markdown("---")
with st.expander("🔐 Admin Login"):
    admin_pass = st.text_input("Enter admin password", type="password", key="admin_password")
    if admin_pass == ADMIN_PASSWORD:
        st.success("Welcome, Admin ✅")

        if not df.empty and os.path.exists(LOG_FILE):
            with open(LOG_FILE, "rb") as f:
                st.download_button(
                    label="📥 Download Meal Log (Excel)",
                    data=f,
                    file_name="meal_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_log_xlsx"
                )
        else:
            st.warning("No entries found yet.")
    elif admin_pass:
        st.error("Incorrect password ❌")



