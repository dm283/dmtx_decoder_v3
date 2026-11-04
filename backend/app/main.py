import os, json
from datetime import datetime
from fastapi import FastAPI, UploadFile, Depends, Form, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Annotated
from pydantic import BaseModel, Field
from uuid import uuid4
from urllib.parse import quote

from app import schemas
from .dmtx_pdf_reco_ver_3 import run_reco_script


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ "*", ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"backend_status": "working"}


# upload file (document)
@app.post("/upload_file/")
async def upload_file(data: Annotated[schemas.IncomeDocReceived, Form()], file: UploadFile, background_tasks: BackgroundTasks):    
    income_doc = schemas.IncomeDoc(filename = file.filename, filecontent = file.file.read(), max_cnt_elems = data.max_cnt_elems)
    file_uuid = str(uuid4())
    background_tasks.add_task(run_reco_script, file_uuid=file_uuid,
            filename=income_doc.filename, income_pdf_file=income_doc.filecontent, dmtx_cnt_per_page=income_doc.max_cnt_elems)
    return {'file_data': {'file': file, 'max_cnt_elems': data.max_cnt_elems, 
                          'sent_dt': datetime.now().time().strftime('%H:%M:%S'), 'status': 'в обработке'},
            'uuid': file_uuid}



# download file from server
@app.post('/download_file/')
def file_download(file_data: Annotated[schemas.FileData, Form()]):
    filepath = file_data.file_path
    filename = file_data.file_name
    response = FileResponse(path=filepath,
                            headers={"Access-Control-Expose-Headers": "Content-Disposition, File-Name",
                                "File-Name": quote(os.path.basename(filename), encoding='utf-8'),
                                "Content-Disposition": f"attachment; filename*=utf-8''{quote(os.path.basename(filename))}"})
    return response



### websocket section
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.active_connections_mapping: dict = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.active_connections_mapping[client_id] = websocket

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # data = await websocket.receive_text()
            # data = await websocket.receive_bytes()
            data = await websocket.receive_json()
            print('received data =', data)
            await manager.send_personal_message(f"server received file", websocket)
            
            # send message to frontend
            if data['message'] == 'recognition done':
                receiver = '10'
                msg_text = {"message": "recognition done", "finish_time": datetime.now().time().strftime('%H:%M:%S'), "uuid": data['uuid'], "processing_path": data['processing_path']}
                msg_text = json.dumps(msg_text)
                await manager.send_personal_message(msg_text, manager.active_connections_mapping[receiver])

            elif data['message'] == 'error':
                receiver = '10'
                msg_text = {"message": "error", "finish_time": datetime.now().time().strftime('%H:%M:%S'), "uuid": data['uuid']}
                msg_text = json.dumps(msg_text)
                await manager.send_personal_message(msg_text, manager.active_connections_mapping[receiver])               

            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            # await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # await manager.broadcast(f"Client #{client_id} left the chat")
