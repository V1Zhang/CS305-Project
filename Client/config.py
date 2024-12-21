HELP = 'Create         : create an conference\n' \
       'Join [conf_id ]: join a conference with conference ID\n' \
       'Quit           : quit an on-going conference\n' \
       'Cancel         : cancel your on-going conference (only the manager)\n\n'

SERVER_IP = '10.32.98.215'
MAIN_SERVER_PORT = 7000
TIMEOUT_SERVER = 5
# DGRAM_SIZE = 1500  # UDP
LOG_INTERVAL = 2

CHUNK = 1024
CHANNELS = 1  # Channels for audio capture
RATE = 44100  # Sampling rate for audio capture

CAMERA_WIDTH, CAMERA_HEIGHT = 320, 240  # resolution for camera capture

# Broadcast Information
BROADCAST_JOIN = 0
BROADCAST_CANCEL_CONFERENCE = 1
