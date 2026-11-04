import json
from websockets.sync.client import connect

uri = "ws://localhost:8000/ws/12"  

def send_websocket_msg(msg_date):
    #
    with connect(uri) as websocket:
        data = msg_date
        websocket.send(json.dumps(data))
        # websocket.send('hello!')
        # websocket.send_data()
        
        message = websocket.recv()
        print(f"Received: {message}")


def send_file():
    with connect(uri) as ws:
        with open("dmtx-1per4.pdf", "rb") as f:  # Open the file in binary mode
            file_bytes = f.read()  # Read the entire file
        ws.send(file_bytes)  # Send the file bytes
        
        response = ws.recv()  # Wait for a confirmation response
        print("Server response:", response)
