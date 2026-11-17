import sys, os, json, configparser
from pathlib import Path
from websockets.sync.client import connect

BASE_DIR = Path(__file__).resolve().parent.parent

config = configparser.ConfigParser()
config_file = BASE_DIR / 'config.ini'
if os.path.exists(config_file): config.read(config_file, encoding='utf-8')
else: print("error! config file doesn't exist"); sys.exit()

WS_IP = config['main']['backend_ip_address']
WS_PORT = config['main']['websocket_port']

uri = f"ws://{WS_IP}:{WS_PORT}/ws/backend"
# uri = f"ws://localhost:8000/ws/backend"

def send_websocket_msg(msg_date):
    #
    with connect(uri) as websocket:
        data = msg_date
        websocket.send(json.dumps(data))        
        message = websocket.recv()
        print(f"Received: {message}")


# def send_file():
#     with connect(uri) as ws:
#         with open("dmtx-1per4.pdf", "rb") as f:  # Open the file in binary mode
#             file_bytes = f.read()  # Read the entire file
#         ws.send(file_bytes)  # Send the file bytes
        
#         response = ws.recv()  # Wait for a confirmation response
#         print("Server response:", response)
