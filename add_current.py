
import pandas as pd

# ---- Load source data ----
df_sub = pd.read_csv('submissions.csv')
df_comp = pd.read_csv('competitors.csv')
df_rounds = pd.read_csv('rounds.csv')
df_votes = pd.read_csv('votes.csv')

# ---- Build submission summary ----

# Merge to get submitter name
merged = df_sub.merge(df_comp, left_on='Submitter ID', right_on='ID', how='left')
merged = merged.rename(columns={'Name': 'Submitter'})

# Round order + round name
df_rounds['Round Order'] = df_rounds.reset_index().index + 1
merged = merged.merge(
    df_rounds[['ID', 'Round Order', 'Name']],
    left_on='Round ID', right_on='ID', how='left'
)
merged = merged.rename(columns={'Name': 'Round Name'})

# Total votes
vote_sum = df_votes.groupby('Spotify URI')['Points Assigned'].sum().reset_index()
vote_sum = vote_sum.rename(columns={'Points Assigned': 'Total Votes'})
merged = merged.merge(vote_sum, on='Spotify URI', how='left')

# Add League column
merged['League'] = "Firefly 7"

# Final output DataFrame
submission_summary = merged[
    ['Artist(s)', 'Title', 'Submitter', 'Round Order',
     'Round Name', 'Total Votes', 'League']
]

# ---- Save submission summary as its own file ----
submission_summary.to_excel('submission_summary.xlsx', index=False, engine='openpyxl')

# ---- Append to existing all firefly workbook ----
# Load existing
df_all = pd.read_excel('previous leagues.xlsx')

# Append new rows
df_combined = pd.concat([df_all, submission_summary], ignore_index=True)

# Save back to all firefly
df_combined.to_excel('all firefly.xlsx', index=False, engine='openpyxl')
