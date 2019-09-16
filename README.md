# Nano Stats Recorder
Python scripts to record Nanocurrency node stats - used by https://nano-faucet.org/beta/chart/
- Confirmation History
- Block Count
- Unchecked Count
- Cemented Count
- Active Confirmation Count
- Confirmation Height Processor Count
- Active Difficulty Multiplier
- Several other stats ...

# Install
These scripts use the requests library as well as a few others. Install any missing libraries 

`pip install requests`

# Config
`config.py.sample` can be renamed to config.py and provides several options for customizing automatic uploads to https://nano-faucet.org/beta/chart and other settings primarily for vote_analysis.py.

## Warning - Use Ctrl-C only once to quit.  It may take a few seconds to end the loops and write to disk before closing.

# Usage - Node Stats
Node Stats will collect other statistical measures to help with plotting the node performance.  The script by default checks every 15 seconds and saves to a file every 60 seconds.  The file save amount should be in multiples of the RPC delay.  The process will save to a file with the date in the filename (eg. stats_2019-06-29.json).

It will read the contents of any file that matches the filename and combine the results for that day.

After quiting the execution (eg. Ctrl-C) it will save the current run to stats.json.  When the script is started again it will automatically rename confirmation_history.json to include the timestamp at the end to preserve prior attempts.

`python node_stats.py`

# Usage - Confirmation History
Confirmation History is pulled from the confirmation_history RPC.  The script by default runs every 10 seconds and saves to a file every 60 seconds.  The file save amount should be in multiples of the RPC delay.  The process will save to a file with the date in the filename (eg. confirmation_history_2019-06-29.json).

It will read the contents of any file that matches the filename and combine the results for that day.

After quiting the execution (eg. Ctrl-C) it will save the current run to confirmation_history.json.  When the script is started again it will automatically rename confirmation_history.json to include the timestamp at the end to preserve prior attempts.

`python confirmation_history.py`

# Usage - Vote Analysis
Vote Analysis will connect to the nodes websocket to record votes and confirmations for designated accounts.  This is used to analyze timing of votes, number of votes per rep and how many votes a particular block received.  It will generate 4 files when closed.

vote_batching.csv - shows how many vote hashes and count of votes per representative that voted during the test
vote_counts.csv - shows the number of votes per representative per test block sent during the test
vote_data.json - saves the vote data related to blocks sent during the test for the monitored account
vote_hashes.json - saves the confirmation history for blocks sent during the test for the monitored account

`python vote_analysis.py` without any arguments will monitor votes only.  -send true will send/receive every 5 seconds if an account and wallet is configured in config.py and if the account is setup with at least 1 raw.

# Usage - Upload
Use automatically by node_stats and record_confirmations but can be used manually to upload a file outside of the normal interval.  The automatic upload happens at 12:00am UTC when the filename rolls over, but a manual upload can be done by specifying the filename to upload.  It must end in json or csv extensions.
