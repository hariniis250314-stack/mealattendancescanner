import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import os
import re

# ---------- Config ----------
st.set_page_config(page_title="Meal Attendance Scanner", page_icon="🍽️")
st.title("🍽️ Meal Attendance Logger")

MASTER_FILE = "GMS Trainees list.xlsx"
LOG_FILE = "meal_log.xlsx"
ADMIN_PASSWORD = "cteagms25"

# ---------- Helpers ----------
def _norm(s: str) -> str:
    return s.strip().lower().replace(" ", "").replace("_", "")

def _digits_only(s) -> str:
    return re.sub(r"\D", "", str(s)) if pd.notna(s) else ""

def _auto_find_columns(df: pd.DataFrame):
    df = df.loc[:, ~df.columns.str.contains(r"^unnamed", case=False)]
    norm_map = {_norm(c): c for c in df.columns}
    name_candidates  = ["name", "studentname", "fullname", "traineename"]
    phone_candidates = ["phone", "phonenumber", "mobile", "mobilenumber", "contact", "contactnumber", "number"]

    name_col  = next((norm_map[n] for n in name_candidates  if n in norm_map), None)
    phone_col = next((norm_map[n] for n in phone_candidates if n in norm_map), None)
    return df, name_col, phone_col

@st.cache_data(show_spinner=False)
def load_master(path: str, mtime: float) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)

def file_mtime(path: str) -> float:
    return os.path.getmtime(path) if os.path.exists(path) else 0.0

@st.cache_data(show_spinner=False)
def load_log(path: str, mtime: float) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_excel(path, dtype=str)
    return pd.DataFrame(columns=["Last4", "Name", "Date", "Time"])

if "cache_bump" not in st.session_state:
    st.session_state.cache_bump = 0

# ---------- Load Master ----------
if not os.path.exists(MASTER_FILE):
    st.error(f"❌ Master file not found: `{MASTER_FILE}`. Upload it next to `app.py` and redeploy.")
    st.stop()

try:
    master_raw = load_master(MASTER_FILE, file_mtime(MASTER_FILE) + st.session_state.cache_bump)
except Exception as e:
    st.error(f"❌ Failed to read `{MASTER_FILE}`: {e}")
    st.stop()

master_df, NAME_COL, PHONE_COL = _auto_find_columns(master_raw)

if NAME_COL is None or PHONE_COL is None:
    st.error("❌ Could not detect required columns in the master file.")
    st.stop()

master_df = master_df.copy()
master_df["__digits__"] = master_df[PHONE_COL].map(_digits_only)
master_df["__last4__"]  = master_df["__digits__"].apply(lambda x: x[-4:] if len(x) >= 4 else "")

# ---------- Load Log ----------
df = load_log(LOG_FILE, file_mtime(LOG_FILE) + st.session_state.cache_bump)

# ---------- Input (NO time restriction) ----------
now = datetime.now()
last4 = st.text_input("Enter LAST 4 digits of your phone number", max_chars=4)

if st.button("Submit"):
    code = (last4 or "").strip()
    if not (len(code) == 4 and code.isdigit()):
        st.warning("Please enter exactly 4 digits.")
    else:
        matches = master_df[master_df["__last4__"] == code]

        if matches.empty:
            st.error("❌ No trainee found with those last 4 digits.")
        elif len(matches) == 1:
            trainee_name = str(matches[NAME_COL].iloc[0]).strip()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            dup = df[(df["Name"].astype(str).str.strip().str.lower() == trainee_name.lower()) &
                     (df["Date"] == date_str)]
            if not dup.empty:
                st.error("⚠️ You have already been logged for today.")
            else:
                new_row = pd.DataFrame([[code, trainee_name, date_str, time_str]],
                                       columns=["Last4", "Name", "Date", "Time"])
                df = pd.concat([df, new_row], ignore_index=True)

                try:
                    df.to_excel(LOG_FILE, index=False)
                except Exception as e:
                    st.error(f"❌ Failed to write log file: {e}")
                else:
                    st.session_state.cache_bump += 1
                    st.success(f"✅ {trainee_name} logged at {time_str} on {date_str}")
                    st.rerun()
        else:
            st.warning("Multiple trainees share these digits. Please confirm your name.")
            chosen = st.selectbox("Select your name", matches[NAME_COL].astype(str).unique().tolist())
            if st.button("Confirm"):
                trainee_name = chosen.strip()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")

                dup = df[(df["Name"].astype(str).str.strip().str.lower() == trainee_name.lower()) &
                         (df["Date"] == date_str)]
                if not dup.empty:
                    st.error("⚠️ You have already been logged for today.")
                else:
                    new_row = pd.DataFrame([[code, trainee_name, date_str, time_str]],
                                           columns=["Last4", "Name", "Date", "Time"])
                    df = pd.concat([df, new_row], ignore_index=True)

                    try:
                        df.to_excel(LOG_FILE, index=False)
                    except Exception as e:
                        st.error(f"❌ Failed to write log file: {e}")
                    else:
                        st.session_state.cache_bump += 1
                        st.success(f"✅ {trainee_name} logged at {time_str} on {date_str}")
                        st.rerun()

# ---------- Admin (NO time window, NO cleanup) ----------
df = load_log(LOG_FILE, file_mtime(LOG_FILE) + st.session_state.cache_bump)

st.markdown("---")
with st.expander("🔐 Admin Login"):
    admin_pass = st.text_input("Enter admin password", type="password", key="admin_password")
    if admin_pass == ADMIN_PASSWORD:
        st.success("Welcome, Admin ✅")
        st.dataframe(df)  # show everything
        if not df.empty and os.path.exists(LOG_FILE):
            with open(LOG_FILE, "rb") as f:
                st.download_button(
                    label="📥 Download Meal Log (Excel)",
                    data=f,
                    file_name="meal_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No entries found yet.")
    elif admin_pass:
        st.error("Incorrect password ❌")

