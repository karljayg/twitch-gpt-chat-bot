"""Simulate what the bot sees from spawningtool"""
# Based on replay_summary.txt, spawningtool returns time as "0:01" string format
# But comments.json stores time as integer seconds

# Example from replay_summary.txt:
# Time: 1:37, Name: Reaper, Supply: 19

# The bot gets this from replay_data:
live_step_example = {
    'time': '1:37',  # STRING format
    'name': 'Reaper',
    'supply': 19
}

# But comments.json stores:
stored_step_example = {
    'supply': 19,
    'name': 'Reaper',
    'time': 97  # INTEGER seconds
}

print("ISSUE FOUND!")
print(f"Live build order from spawningtool: time = '{live_step_example['time']}' (type: {type(live_step_example['time']).__name__})")
print(f"Stored build order in comments.json: time = {stored_step_example['time']} (type: {type(stored_step_example['time']).__name__})")
print()
print("When comparing timings, '1:37' != 97, causing timing penalties!")



