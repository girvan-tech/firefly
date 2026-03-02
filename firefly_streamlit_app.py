
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import List
from rapidfuzz import fuzz

# ----------------------------------
# CONFIG
# ----------------------------------
DATA_FILE_DEFAULT = "all firefly.xlsx"
REQUIRED_COLS = [
    "Artist(s)", "Title", "Submitter",
    "Round Order", "Round Name",
    "Total Votes", "League"
]

st.set_page_config(page_title="Firefly Search (fuzzy)", layout="wide")

# ----------------------------------
# LOAD DATA (CACHED)
# ----------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    missing = set(REQUIRED_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    # Lowercase helpers for exact search
    df["artist_lc"] = df["Artist(s)"].astype(str).str.lower()
    df["title_lc"]  = df["Title"].astype(str).str.lower()
    # Convenience: string versions of a few cols
    df["Round Order"] = pd.to_numeric(df["Round Order"], errors="coerce")
    df["Total Votes"] = pd.to_numeric(df["Total Votes"], errors="coerce")
    return df


# ----------------------------------
# EXACT (non-fuzzy) SEARCH
# ----------------------------------
def exact_search(df: pd.DataFrame, query: str, field: str) -> pd.DataFrame:
    q = (query or "").strip().lower()
    if not q:
        return df.iloc[0:0]

    if field == "Artist":
        mask = df["artist_lc"].str.contains(q, na=False)
    elif field == "Title":
        mask = df["title_lc"].str.contains(q, na=False)
    else:  # Artist + Title
        mask = df["artist_lc"].str.contains(q, na=False) | df["title_lc"].str.contains(q, na=False)

    results = df.loc[mask, REQUIRED_COLS].copy()

    # Prioritise starts-with matches, then highest votes
    starts = (
        df["artist_lc"].str.startswith(q, na=False) |
        df["title_lc"].str.startswith(q, na=False)
    )
    results["__starts"] = starts[mask].astype(int)
    results = results.sort_values(["__starts", "Total Votes"], ascending=[False, False]).drop(columns="__starts")
    return results


# ----------------------------------
# FUZZY SEARCH (rapidfuzz)
# ----------------------------------
def fuzzy_search(df: pd.DataFrame, query: str, field: str, threshold: int) -> pd.DataFrame:
    q = (query or "").strip().lower()
    if not q:
        return df.iloc[0:0]

    if field == "Artist":
        series = df["Artist(s)"].astype(str)
    elif field == "Title":
        series = df["Title"].astype(str)
    else:  # Artist + Title
        series = (df["Artist(s)"].astype(str) + " " + df["Title"].astype(str))

    # Compute fuzzy partial ratio per row
    scores = series.apply(lambda x: fuzz.partial_ratio(q, x.lower()))

    # Keep only matches above threshold
    matched = df.loc[scores >= threshold].copy()
    matched["fuzzy_score"] = scores[scores >= threshold]

    # Nice stable ordering: best score → votes → round order asc
    matched = matched.sort_values(
        by=["fuzzy_score", "Total Votes", "Round Order"],
        ascending=[False, False, True]
    )

    return matched[REQUIRED_COLS + ["fuzzy_score"]]


# ----------------------------------
# SIDEBAR – DATA SOURCE & FILTERS
# ----------------------------------
st.sidebar.header("⚙️ Settings")

# Let the user point to a different combined file if they want
data_file = st.sidebar.text_input("Combined Excel path", DATA_FILE_DEFAULT)

# Try to load
data_path = Path(data_file)
if not data_path.exists():
    st.sidebar.error(f"File not found: {data_path}")
    st.stop()

df = load_data(str(data_path))

# Optional filters (apply to the full dataset before search)
with st.sidebar.expander("🔎 Filters (optional)"):
    source_pick = st.multiselect("League", sorted(df["League"].dropna().unique().tolist()))
    round_pick  = st.multiselect("Round Name", sorted(df["Round Name"].dropna().unique().tolist()))
    submitter_pick = st.multiselect("Submitter", sorted(df["Submitter"].dropna().unique().tolist()))
    min_votes = st.number_input("Min Total Votes", min_value=0, value=0, step=1)

filtered = df.copy()
if source_pick:
    filtered = filtered[filtered["League"].isin(source_pick)]
if round_pick:
    filtered = filtered[filtered["Round Name"].isin(round_pick)]
if submitter_pick:
    filtered = filtered[filtered["Submitter"].isin(submitter_pick)]
if min_votes:
    filtered = filtered[filtered["Total Votes"].fillna(0) >= min_votes]


# ----------------------------------
# MAIN UI
# ----------------------------------
st.title("🔎 Firefly Music League — Search (with fuzzy matching)")

st.caption(
    f"Loaded **{len(df):,}** rows from **{data_path.name}** · "
    f"Active filters reduce to **{len(filtered):,}** rows"
)

col_q, col_field = st.columns([3, 1])
with col_q:
    query = st.text_input("Search by Artist or Song Title", "", placeholder="Try: 'Shuggie', 'Radiohed', 'Banana', 'Blue Monday'…")
with col_field:
    field = st.selectbox("Field", ["Artist + Title", "Artist", "Title"])

# Fuzzy controls
row1_col1, row1_col2, row1_col3 = st.columns([1.4, 2, 2])
with row1_col1:
    use_fuzzy = st.checkbox("Enable fuzzy matching", value=True)
with row1_col2:
    threshold = st.slider("Fuzzy threshold", min_value=40, max_value=95, value=80, step=1, help="Lower = more forgiving; Higher = stricter")
with row1_col3:
    limit = st.number_input("Max rows to display", min_value=10, max_value=5000, value=500, step=10)

st.markdown("---")

# ----------------------------------
# EXECUTE SEARCH
# ----------------------------------
if query:
    if use_fuzzy:
        results = fuzzy_search(filtered, query, {"Artist + Title": "Both", "Artist": "Artist", "Title": "Title"}[field], threshold)
        # If fuzzy returns the extra column, show it; otherwise fallback
        display_cols = REQUIRED_COLS + (["fuzzy_score"] if "fuzzy_score" in results.columns else [])
    else:
        results = exact_search(filtered, query, field if field != "Artist + Title" else "Both")
        display_cols = REQUIRED_COLS

    # Trim to limit
    results = results.head(limit)

    if results.empty:
        st.warning("No matches found.")
    else:
        st.success(f"Found **{len(results):,}** matches.")
        st.dataframe(results[display_cols], use_container_width=True)

        # CSV export
        csv = results[display_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download these results (CSV)",
            data=csv,
            file_name="firefly_search_results.csv",
            mime="text/csv"
        )
else:
    st.info("Enter a search term to begin. Tip: toggle **fuzzy** and adjust the **threshold** if spelling is uncertain.")
