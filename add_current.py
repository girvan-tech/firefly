
import pandas as pd
import zipfile
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---- Unzip export.zip ----
zip_path = "export.zip"
extract_dir = "."

with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(extract_dir)

print("Unzipped export.zip")

# ---- Load source data ----
df_sub = pd.read_csv('submissions.csv')
df_comp = pd.read_csv('competitors.csv')
df_rounds = pd.read_csv('rounds.csv')
df_votes = pd.read_csv('votes.csv')

# ---- Build submission summary ----

merged = df_sub.merge(df_comp, left_on='Submitter ID', right_on='ID', how='left')
merged = merged.rename(columns={'Name': 'Submitter'})

df_rounds['Round Order'] = df_rounds.reset_index().index + 1
merged = merged.merge(
    df_rounds[['ID', 'Round Order', 'Name']],
    left_on='Round ID', right_on='ID', how='left'
)
merged = merged.rename(columns={'Name': 'Round Name'})

vote_sum = df_votes.groupby('Spotify URI')['Points Assigned'].sum().reset_index()
vote_sum = vote_sum.rename(columns={'Points Assigned': 'Total Votes'})
merged = merged.merge(vote_sum, on='Spotify URI', how='left')

merged['League'] = "Firefly 7"

submission_summary = merged[
    ['Artist(s)', 'Title', 'Submitter', 'Round Order',
     'Round Name', 'Total Votes', 'League']
]

submission_summary.to_excel('submission_summary.xlsx', index=False, engine='openpyxl')

# ---- Update combined file ----
df_all = pd.read_excel('previous leagues.xlsx')
df_combined = pd.concat([df_all, submission_summary], ignore_index=True)

df_combined = df_combined.sort_values(by="Artist(s)", ascending=True)

df_combined.to_excel('all firefly.xlsx', index=False, engine='openpyxl')

print("Created all firefly.xlsx")

# ---- Upload to Google Sheets ----
creds_json = os.getenv("GOOGLE_CREDS_JSON")
creds_dict = json.loads(creds_json)

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1YOlQCaBlcjiE_x2-hL7gMeo-7eQ_p5a2rECw3vg3U4c"   # <-- add your real ID here
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# Convert DataFrame to list-of-lists
values = [df_combined.columns.tolist()] + df_combined.values.tolist()

sheet.clear()
sheet.update("A1", values)

print("Google Sheet updated successfully!")
