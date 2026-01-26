"""Check if database has full build orders"""
import sys
sys.path.insert(0, '.')
import json

from models.mathison_db import Database
from adapters.database.database_client_factory import create_database_client

db = create_database_client()

# Get one replay to check structure
query = "SELECT Replay_Summary FROM Replays WHERE opponent = 'ГОСТ' ORDER BY date_played DESC LIMIT 1"
result = db.execute(query)

if result:
    summary_str = result[0]['Replay_Summary']
    if summary_str:
        summary = json.loads(summary_str) if isinstance(summary_str, str) else summary_str
        
        for p_key, p_data in summary.get('players', {}).items():
            name = p_data.get('name', 'Unknown')
            bo = p_data.get('buildOrder', [])
            print(f"Player: {name}, Build order steps: {len(bo)}")

