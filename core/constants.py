# Network
# HTTP status code for a successful request
import os

STATUS_SUCCESS = 200

# Main
API_ENDPOINT = '/api/v2/servers/'
GUILD_ID:int = int(os.getenv('GUILD_ID'), 0)
AUTO_STOP_SLEEP_TIME:int = int(os.getenv('AUTO_STOP_SLEEP_TIME', 1800))
