
import streamlit as st
import pandas as pd
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
DATA_FILE = "submission_summary_all_firefly_4_5_6.xlsx"

REQUIRED_COLS = [
    "Artist(s)", "Title", "Submitter", "Round Order",
    "Round Name", "Round ID", "Total Votes", "Source File"
]

# -----------------------------
# LOAD DATA (CACHED)
# -----------------------------
@st.cache_data
def load_data(path: str):
    df = pd.read_excel(path, engine="openpyxl")
    missing = set(REQUIRED_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Precompute lowercase for fast search
    df["artist_lc"] = df["Artist(s)"].astype(str).str.lower()
    df["title_lc"] = df["Title"].astype(str).str.lower()
    return df


# -----------------------------
# SEARCH FUNCTION
# -----------------------------
def search(df: pd.DataFrame, query: str, field: str):
    if not query:
        return df.iloc[0:0]  # empty

    q = query.lower().strip()

    if field == "Artist":
        mask = df["artist_lc"].str.contains(q, na=False)
    elif field == "Title":
        mask = df["title_lc"].str.contains(q, na=False)
    else:
        mask = df["artist_lc"].str.contains(q, na=False) | df["title_lc"].str.contains(q, na=False)

    results = df.loc[mask, REQUIRED_COLS].copy()

    # Prioritize matches that *start with* the query
    starts = (
        df["artist_lc"].str.startswith(q, na=False) |
        df["title_lc"].str.startswith(q, na=False)
    )
    results["starts"] = starts[mask].astype(int)

    results = results.sort_values(["starts", "Total Votes"], ascending=[False, False])
    results = results.drop(columns=["starts"])
    return results


# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="Firefly Music Search", layout="wide")
st.title("🔎 Firefly Music League – Search Tool")

data_path = Path(DATA_FILE)

if not data_path.exists():
    st.error(f"Data file not found: {DATA_FILE}")
    st.stop()

df = load_data(DATA_FILE)

st.write(f"Loaded **{len(df):,}** submissions from **{DATA_FILE}**")

# Search inputs
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input("Search by Artist or Song Title", "", placeholder="e.g. Beatles, Autechre, Sunshine...")
with col2:
    field = st.selectbox("Field", ["Artist + Title", "Artist", "Title"])

# Run search
field_map = {"Artist + Title": "Both", "Artist": "Artist", "Title": "Title"}
search_field = field_map[field]

results = search(df, query, search_field)

# Display results
if query and results.empty:
    st.warning("No matches found.")
elif query:
    st.success(f"Found {len(results)} matching submissions.")
    st.dataframe(results, use_container_width=True)

    # CSV download
    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download results as CSV",
        data=csv,
        file_name=f"firefly_search_results.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("Firefly Search Tool – Streamlit version")
