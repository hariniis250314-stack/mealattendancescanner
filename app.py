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
        mask = (

