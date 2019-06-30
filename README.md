# Nano Stats Recorder
Python scripts to record Nanocurrency node stats - used by https://nano-faucet.org/beta/chart/
- Confirmation History
- Block Count
- Unchecked Count
- Cemented Count
- Active Confirmation Count
- Confirmation Height Processor Count
- Active Difficulty Multiplier

# Install
These scripts use the requests library as well as a few others. Install any missing libraries 

`pip install requests`

# Usage
Confirmation History is pulled from the confirmation_history RPC.  The script by default runs every 10 seconds and saves to a file every 60 seconds.  The file save amount should be in multiples of the RPC delay.  The process will save to a file with the date in the filename (eg. confirmation_history_2019-06-29.json).

It will read the contents of any file that matches the filename and combine the results for that day.

After quiting the execution (eg. Ctrl-C) it will save the current run to confirmation_history.json.  When the script is started again it will automatically rename confirmation_history.json to include the timestamp at the end to preserve prior attempts.

`confirmation_history.py`

Node Stats will collect other statistical measures to help with plotting the node performance.  The script by default checks every 15 seconds and saves to a file every 60 seconds.  The file save amount should be in multiples of the RPC delay.  The process will save to a file with the date in the filename (eg. stats_2019-06-29.json).

It will read the contents of any file that matches the filename and combine the results for that day.

After quiting the execution (eg. Ctrl-C) it will save the current run to stats.json.  When the script is started again it will automatically rename confirmation_history.json to include the timestamp at the end to preserve prior attempts.

`node_stats.py`

