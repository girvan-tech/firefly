
import pandas as pd

# Load the CSV files
df_sub = pd.read_csv('submissions.csv')
df_comp = pd.read_csv('competitors.csv')
df_rounds = pd.read_csv('rounds.csv')
df_votes = pd.read_csv('votes.csv')

# 1–2. Merge submissions with competitors to get submitter name
merged = df_sub.merge(df_comp, left_on='Submitter ID', right_on='ID', how='left')
merged = merged.rename(columns={'Name': 'Submitter'})

# 3. Add round order and round name
df_rounds['Round Order'] = df_rounds.reset_index().index + 1
merged = merged.merge(
    df_rounds[['ID', 'Round Order', 'Name']],
    left_on='Round ID', right_on='ID', how='left'
)
merged = merged.rename(columns={'Name': 'Round Name'})

# 4. Total votes per track
vote_sum = df_votes.groupby('Spotify URI')['Points Assigned'].sum().reset_index()
vote_sum = vote_sum.rename(columns={'Points Assigned': 'Total Votes'})
merged = merged.merge(vote_sum, on='Spotify URI', how='left')

# 5. Add League column
merged['League'] = "Firefly 7"

# Final output columns
output = merged[['Artist(s)', 'Title', 'Submitter', 'Round Order', 'Round Name', 'Total Votes', 'League']]

# Save to Excel
output.to_excel('submission_summary.xlsx', index=False, engine='openpyxl')

output.head()
