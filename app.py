from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
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
    name_candidates = ["name", "studentname", "fullname", "traineename"]
    phone_candidates = ["phone", "phonenumber", "mobile", "mobilenumber", "contact", "contactnumber", "number"]
    name_col = next((norm_map[n] for n in name_candidates if n in norm_map), None)
    phone_col = next((norm_map[n] for n in phone_candidates if n in norm_map), None)
    return df, name_col, phone_col

@st.cache_data(show_spinner=False)
def load_master(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)

def load_log(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_excel(path, dtype=str)
    return pd.DataFrame(columns=["Last4", "Name", "Date", "Time"])

def save_log(df: pd.DataFrame, path: str):
    df.to_excel(path, index=False)

# ---------- Load master ----------
if not os.path.exists(MASTER_FILE):
    st.error(f"❌ Master file not found: `{MASTER_FILE}`.")
    st.stop()

master_raw = load_master(MASTER_FILE)
master_df, NAME_COL, PHONE_COL = _auto_find_columns(master_raw)

if NAME_COL is None or PHONE_COL is None:
    st.error("❌ Could not detect Name or Phone column in master file.")
    st.stop()

master_df["__digits__"] = master_df[PHONE_COL].map(_digits_only)
master_df["__last4__"] = master_df["__digits__"].apply(lambda x: x[-4:] if len(x) >= 4 else "")

# ---------- Time-based clearing ----------
now = datetime.now()
log_df = load_log(LOG_FILE)

# Define time windows
today_7pm = now.replace(hour=19, minute=0, second=0, microsecond=0)
today_10am = now.replace(hour=10, minute=0, second=0, microsecond=0)
yesterday_7pm = (today_7pm - timedelta(days=1))

# Clear old entries if after 10AM and log contains older than yesterday 7PM
if now > today_10am:
    log_df = log_df[~pd.to_datetime(log_df["Date"] + " " + log_df["Time"]).lt(today_7pm)]
    save_log(log_df, LOG_FILE)

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
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            dup = log_df[(log_df["Name"].str.lower() == trainee_name.lower()) & (log_df["Date"] == date_str)]
            if not dup.empty:
                st.error("⚠️ You have already been logged for today.")
            else:
                new_row = pd.DataFrame([[code, trainee_name, date_str, time_str]],
                                       columns=["Last4", "Name", "Date", "Time"])
                log_df = pd.concat([log_df, new_row], ignore_index=True)
                save_log(log_df, LOG_FILE)
                st.success(f"✅ {trainee_name} logged at {time_str} on {date_str}")
                st.rerun()
        else:
            st.warning("Multiple trainees share these last 4 digits.")
            options = matches[NAME_COL].unique().tolist()
            chosen = st.selectbox("Select your name", options, key="name_select")
            if st.button("Confirm", key="confirm_btn"):
                trainee_name = chosen.strip()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")
                dup = log_df[(log_df["Name"].str.lower() == trainee_name.lower()) & (log_df["Date"] == date_str)]
                if not dup.empty:
                    st.error("⚠️ You have already been logged for today.")
                else:
                    new_row = pd.DataFrame([[code, trainee_name, date_str, time_str]],
                                           columns=["Last4", "Name", "Date", "Time"])
                    log_df = pd.concat([log_df, new_row], ignore_index=True)
                    save_log(log_df, LOG_FILE)
                    st.success(f"✅ {trainee_name} logged at {time_str} on {date_str}")
                    st.rerun()

# ---------- Summary ----------
st.metric("Total Entries", len(log_df))

# ---------- Admin ----------
st.markdown("---")
with st.expander("🔐 Admin Login"):
    admin_pass = st.text_input("Enter admin password", type="password", key="admin_password")
    if admin_pass == ADMIN_PASSWORD:
        st.success("Welcome, Admin ✅")
        # Filter admin log view based on time
        if now < today_10am:
            admin_view = log_df[pd.to_datetime(log_df["Date"] + " " + log_df["Time"]) >= yesterday_7pm]
        else:
            admin_view = log_df[pd.to_datetime(log_df["Date"] + " " + log_df["Time"]) >= today_7pm]
        
        if not admin_view.empty:
            with open(LOG_FILE, "rb") as f:
                st.download_button(
                    label="📥 Download Meal Log (Excel)",
                    data=f,
                    file_name="meal_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No entries in this time window.")
    elif admin_pass:
        st.error("Incorrect password ❌")

