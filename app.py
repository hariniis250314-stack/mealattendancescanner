import streamlit as st
import pandas as pd
from datetime import datetime, time
import pytz
import os
import re

# ---------- Config ----------
st.set_page_config(page_title="Meal Attendance Scanner", page_icon="🍽️")
st.title("🍽️ Meal Attendance Logger")

MASTER_FILE = "GMS Trainees list.xlsx"
LOG_FILE = "meal_log.xlsx"
ADMIN_PASSWORD = "cteagms25"

# Timezone
IST = pytz.timezone("Asia/Kolkata")

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

def save_log(df: pd.DataFrame):
    df.to_excel(LOG_FILE, index=False)

def filter_old_entries(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only today's entries after 7 PM, and entries after midnight until 10 AM next day."""
    if df.empty:
        return df

    now = datetime.now(IST)
    today_str = now.strftime("%Y-%m-%d")

    # Convert Date + Time to datetime in IST
    df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
    df["DateTime"] = df["DateTime"].dt.tz_localize("UTC").dt.tz_convert(IST) if df["DateTime"].dt.tz is None else df["DateTime"]

    filtered_df = pd.DataFrame()

    # If current time is after 7 PM
    if now.time() >= time(19, 0):
        # Show only today's entries after 7 PM
        mask = (df["DateTime"].dt.strftime("%Y-%m-%d") == today_str) & (df["DateTime"].dt.time >= time(19, 0))
        filtered_df = df[mask]

    # If between midnight and 10 AM
    elif now.time() <= time(10, 0):
        yesterday_str = (now - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        mask_yesterday = (df["DateTime"].dt.strftime("%Y-%m-%d") == yesterday_str) & (df["DateTime"].dt.time >= time(19, 0))
        mask_today = (df["DateTime"].dt.strftime("%Y-%m-%d") == today_str) & (df["DateTime"].dt.time <= time(10, 0))
        filtered_df = df[mask_yesterday | mask_today]

    # Drop helper column
    filtered_df = filtered_df.drop(columns=["DateTime"], errors="ignore")
    return filtered_df

# ---------- Load master ----------
if not os.path.exists(MASTER_FILE):
    st.error(f"❌ Master file not found: `{MASTER_FILE}`. Upload it next to `app.py` and redeploy.")
    st.stop()

master_raw = load_master(MASTER_FILE, file_mtime(MASTER_FILE) + st.session_state.get("cache_bump", 0))
master_df, NAME_COL, PHONE_COL = _auto_find_columns(master_raw)

if NAME_COL is None or PHONE_COL is None:
    st.error(
        "❌ Could not detect required columns in the master file.\n"
        "Expected a *name* and a *phone* column."
    )
    st.stop()

# Prepare last4
master_df["__digits__"] = master_df[PHONE_COL].map(_digits_only)
master_df["__last4__"]  = master_df["__digits__"].apply(lambda x: x[-4:] if len(x) >= 4 else "")

# ---------- Load log ----------
df = load_log(LOG_FILE, file_mtime(LOG_FILE) + st.session_state.get("cache_bump", 0))

# ---------- Input ----------
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
            now = datetime.now(IST)
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            dup = df[(df["Name"].str.strip().str.lower() == trainee_name.lower()) & (df["Date"] == date_str)]
            if not dup.empty:
                st.error("⚠️ You have already been logged for today.")
            else:
                new_row = pd.DataFrame([[code, trainee_name, date_str, time_str]], columns=["Last4", "Name", "Date", "Time"])
                df = pd.concat([df, new_row], ignore_index=True)
                save_log(df)
                st.session_state["cache_bump"] = st.session_state.get("cache_bump", 0) + 1
                st.success(f"✅ {trainee_name} logged at {time_str} on {date_str}")
                st.rerun()

        else:
            st.warning("Multiple trainees share these last 4 digits. Please confirm your name.")
            options = matches[NAME_COL].astype(str).dropna().unique().tolist()
            chosen = st.selectbox("Select your name", options)
            if st.button("Confirm", key="confirm_btn"):
                trainee_name = chosen.strip()
                now = datetime.now(IST)
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")

                dup = df[(df["Name"].str.strip().str.lower() == trainee_name.lower()) & (df["Date"] == date_str)]
                if not dup.empty:
                    st.error("⚠️ You have already been logged for today.")
                else:
                    new_row = pd.DataFrame([[code, trainee_name, date_str, time_str]], columns=["Last4", "Name", "Date", "Time"])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_log(df)
                    st.session_state["cache_bump"] = st.session_state.get("cache_bump", 0) + 1
                    st.success(f"✅ {trainee_name} logged at {time_str} on {date_str}")
                    st.rerun()

# ---------- Summary ----------
df = load_log(LOG_FILE, file_mtime(LOG_FILE) + st.session_state.get("cache_bump", 0))
st.metric("Total Entries Today", len(df[df["Date"] == datetime.now(IST).strftime("%Y-%m-%d")]))

# ---------- Admin ----------
st.markdown("---")
with st.expander("🔐 Admin Login"):
    admin_pass = st.text_input("Enter admin password", type="password")
    if admin_pass == ADMIN_PASSWORD:
        st.success("Welcome, Admin ✅")
        filtered_log = filter_old_entries(df)
        if not filtered_log.empty:
            st.dataframe(filtered_log)
            with open(LOG_FILE, "rb") as f:
                st.download_button(
                    label="📥 Download Meal Log (Excel)",
                    data=f,
                    file_name="meal_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No entries found in allowed time range.")
    elif admin_pass:
        st.error("Incorrect password ❌")

