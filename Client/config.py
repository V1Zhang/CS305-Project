HELP = 'Create         : create an conference\n' \
       'Join [conf_id ]: join a conference with conference ID\n' \
       'Quit           : quit an on-going conference\n' \
       'Cancel         : cancel your on-going conference (only the manager)\n\n'

SERVER_IP = '127.0.0.1'
MAIN_SERVER_PORT = 7777
# yhj
SERVER_IP_LOGIC = '10.32.98.215'
MAIN_SERVER_PORT_LOGIC = 7000

MAIN_SERVER_PORT_UDP = 8000
SELF_IP = '10.32.98.215'

TIMEOUT_SERVER = 5
# DGRAM_SIZE = 1500  # UDP
LOG_INTERVAL = 2

CHUNK = 1024
CHANNELS = 1  # Channels for audio capture
RATE = 44100  # Sampling rate for audio capture

CAMERA_WIDTH, CAMERA_HEIGHT = 474, 474  # resolution for camera capture
SCREEN_WIDTH, SCREEN_HEIGHT = 550, 450

# Broadcast Information
BROADCAST_JOIN = 0
BROADCAST_CANCEL_CONFERENCE = 1
