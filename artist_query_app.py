# artist_query_app.py
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Artist Finder for allfirefly.xlsx", page_icon="🎵", layout="wide")

@st.cache_data(show_spinner=False)
def load_data(xlsx_path: str):
    # Read first sheet by default
    df = pd.read_excel(xlsx_path, engine="openpyxl")
    # Normalize column names
    df.columns = [c.strip() for c in df.columns]
    return df

# --- Load data ---
XLSX_FILE = "allfirefly.xlsx"
df = load_data(XLSX_FILE)

st.title("🎵 Artist Finder")
st.caption("Search the spreadsheet for matching artists and browse the results.")

# --- Sidebar form ---
with st.sidebar.form("search_form"):
    st.subheader("Search Options")
    query = st.text_input("Artist name contains…", placeholder="e.g., Nico, R.E.M., Billie")
    exact = st.checkbox("Exact match (whole field)", value=False)
    case_sensitive = st.checkbox("Case sensitive", value=False)
    dedupe = st.checkbox("Show unique artists only", value=True)
    limit = st.number_input("Max rows to show", min_value=1, max_value=10000, value=200, step=50)
    submitted = st.form_submit_button("Search")

# --- Ensure required columns ---
required_cols = ["Artist", "Title", "Rank", "Points", "Voters", "Average", "Submitter", "league", "Position"]
for col in required_cols:
    if col not in df.columns:
        # Soft-fail: just continue; columns vary sometimes
        pass

# --- Filtering logic ---
filtered = df.copy()
if submitted:
    if query:
        series = filtered["Artist"].astype(str)
        if exact:
            if case_sensitive:
                mask = series == query
            else:
                mask = series.str.casefold() == query.casefold()
        else:
            if case_sensitive:
                mask = series.str.contains(query, regex=False)
            else:
                mask = series.str.contains(query, case=False, regex=False)
        filtered = filtered[mask]
    else:
        st.info("Type something in the search box and click **Search** to filter by artist.")
else:
    # On first load, show nothing until user searches
    filtered = filtered.iloc[0:0]

# --- Dedupe option ---
if not filtered.empty and dedupe:
    # Keep first occurrence of each artist
    filtered = (filtered.sort_values(by=[c for c in ["Rank", "Points"] if c in filtered.columns], ascending=[True, False])
                        .drop_duplicates(subset=["Artist"]))

# --- Limit rows ---
if not filtered.empty:
    filtered = filtered.head(int(limit))

# --- Output ---
if filtered.empty:
    st.write("No results yet. Use the form to search by artist.")
else:
    # Select a nice subset of columns if available
    preferred = [c for c in ["Rank", "Artist", "Title", "Submitter", "league", "Position", "Voters", "Points", "Average"] if c in filtered.columns]
    display_df = filtered[preferred] if preferred else filtered
    st.success(f"Found {len(filtered):,} matching row(s)")
    st.dataframe(display_df, use_container_width=True)

    # Download button
    csv = filtered.to_csv(index=False)
    st.download_button(
        label="Download results as CSV",
        data=csv,
        file_name="artist_search_results.csv",
        mime="text/csv",
    )

# --- Extra: quick unique list of artists ---
st.divider()
st.subheader("Quick: Unique Artists in File")
unique_artists = df["Artist"].astype(str).dropna().unique().tolist() if "Artist" in df.columns else []
st.write(f"Total artists: {len(unique_artists):,}")
search_hint = st.text_input("Filter this list (client-side)", value="", placeholder="start typing…")
if search_hint:
    ua = [a for a in unique_artists if (a if case_sensitive else a.lower()).find(search_hint if case_sensitive else search_hint.lower()) != -1]
else:
    ua = unique_artists[:250]
st.write(ua)
