import os, json
from datetime import datetime
from fastapi import FastAPI, UploadFile, Depends, Form, WebSocket, WebSocketDisconnect, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException
from typing import Annotated
from uuid import uuid4
from urllib.parse import quote
from sqlalchemy.orm import Session
from sqlalchemy import select

from app import crud, models, schemas, auth, common_functions
from .auth import UserAuth, get_current_active_user
from app.database import SessionLocal, engine
from app.database import DEV
from .dmtx_pdf_reco_ver_3 import run_reco_script


if DEV == 'false':
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
else:
    app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix='/auth', tags=['auth'])

models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"backend_status": "working"}


# upload file (document)
@app.post("/upload_file/")
async def upload_file(current_user: Annotated[UserAuth, Depends(get_current_active_user)],
    data: Annotated[schemas.IncomeDocReceived, Form()], file: UploadFile, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    
    income_doc = schemas.IncomeDoc(filename = file.filename, filecontent = file.file.read(), 
                                   max_cnt_elems = data.max_cnt_elems, user_uuid=data.user_uuid)
    file_uuid = str(uuid4())
    start_time = datetime.now().time().strftime('%H:%M:%S')

    background_tasks.add_task(run_reco_script, file_uuid=file_uuid,
            filename=income_doc.filename, filesize=file.size, income_pdf_file=income_doc.filecontent, 
            dmtx_cnt_per_page=income_doc.max_cnt_elems, user_uuid=income_doc.user_uuid, start_time=start_time, db=db)

    return {'uuid': file_uuid, 'filename': file.filename, 'size': file.size, 'max_cnt_elems': data.max_cnt_elems, 
            'start_time': start_time, 'status': 'в обработке'}


# download file from server
@app.post('/download_file/')
def file_download(current_user: Annotated[UserAuth, Depends(get_current_active_user)], file_data: Annotated[schemas.FileData, Form()]):

    filepath = file_data.file_path
    filename = file_data.file_name
    response = FileResponse(path=filepath,
                            headers={"Access-Control-Expose-Headers": "Content-Disposition, File-Name",
                                "File-Name": quote(os.path.basename(filename), encoding='utf-8'),
                                "Content-Disposition": f"attachment; filename*=utf-8''{quote(os.path.basename(filename))}"})
    return response


# download file from db
@app.post('/download_file_db/')
def file_download_db(current_user: Annotated[UserAuth, Depends(get_current_active_user)], 
                     data: Annotated[schemas.FileDBData, Form()], db: Session = Depends(get_db)):

    task_uuid = data.task_uuid  # 822a349e-f54b-478d-969e-11b10d983da0
    file_type = data.file_type
    filename_dict = {
        'res_csv_file': 'res_decoded_dmtx.csv',
        'report_file': 'bot_report.txt',
        'undecoded_pages_zip': 'undecoded_pages.zip'
    }
    filename = filename_dict[file_type]
    db_item = db.query(models.Task).filter(models.Task.uuid == task_uuid).first()
    if db_item is None: raise HTTPException(status_code=404, detail="Item not found")
    filecontent = db_item.__getattribute__(file_type)
    response = Response(content=filecontent,
                        headers={"Access-Control-Expose-Headers": "Content-Disposition, File-Name",
                            "File-Name": quote(os.path.basename(filename), encoding='utf-8'),
                            "Content-Disposition": f"attachment; filename*=utf-8''{quote(os.path.basename(filename))}"})
    return response


### websocket section
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.active_connections_mapping: dict = {}

        self.reversedict: dict = {}
        self.active_conn_dict: dict = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()

        # 2 feature only 1 connection for 1 login
        if client_id in self.active_connections_mapping:
            msg_text = {"message": "already logged in"}
            msg_text = json.dumps(msg_text)
            print(111, msg_text, websocket)
            await self.send_personal_message(msg_text, websocket)
            return

        self.active_connections.append(websocket)
        self.active_connections_mapping[client_id] = websocket

        # try new feature
        self.reversedict[websocket] = client_id
        # if client_id not in self.active_conn_dict:
        #     self.active_conn_dict[client_id] = []
        # self.active_conn_dict[client_id].append(websocket)
        # print('active_conn_dict after new conn=', self.active_conn_dict)
        # print('active_connections_mapping after new conn=', self.active_connections_mapping)
        # print('reversedict =', self.reversedict)
        print(f'websocket  -  пользователь {client_id} подключился {websocket}')

    def disconnect(self, websocket: WebSocket):
        print('вебсокет отключился', websocket)
        #print(f'websocket  -  user {client_id} отключился {websocket}')
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # try new feature
        # del self.active_connections_mapping[ self.reversedict[websocket] ]
        # if websocket in self.active_conn_dict[ self.reversedict[websocket] ]:
        #     self.active_conn_dict[ self.reversedict[websocket] ].remove(websocket)
        if websocket in self.reversedict:
            del self.active_connections_mapping[ self.reversedict[websocket] ]
            del self.reversedict[websocket]
        

        # for i in self.active_connections_mapping:
        #     if self.active_connections_mapping[i] == websocket:
        #         del self.active_connections_mapping[i]
        # print('active_connections after disconnet =', self.active_connections_mapping)

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
                receiver = data['user_uuid']
                msg_text = {"message": "recognition done", "finish_time": datetime.now().time().strftime('%H:%M:%S'), "uuid": data['uuid'], "processing_path": data['processing_path']}
                msg_text = json.dumps(msg_text)
                await manager.send_personal_message(msg_text, manager.active_connections_mapping[receiver])

                # try new
                # for w in manager.active_conn_dict[receiver]:
                #     print('w =', w)
                #     await manager.send_personal_message(msg_text, w)

            elif data['message'] == 'error':
                receiver = data['user_uuid']
                msg_text = {"message": "error", "finish_time": datetime.now().time().strftime('%H:%M:%S'), "uuid": data['uuid']}
                msg_text = json.dumps(msg_text)
                await manager.send_personal_message(msg_text, manager.active_connections_mapping[receiver])      

            # zero elements have recognized (including pdf file has no any datamatrix)
            elif data['message'] == 'zero':
                receiver = data['user_uuid']
                msg_text = {"message": "zero", "finish_time": datetime.now().time().strftime('%H:%M:%S'), "uuid": data['uuid']}
                msg_text = json.dumps(msg_text)
                await manager.send_personal_message(msg_text, manager.active_connections_mapping[receiver])           

            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            # await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # await manager.broadcast(f"Client #{client_id} left the chat")



#########################################################    SERVICE FUNCTIONS
# def redefine_schema_values_to_none(data, schema_obj):
#     # get data received from frontend and redefine values if value is any kind of none to None
#     data_dict = data.dict()
#     for k in data_dict:
#         if data_dict[k] in ['null', 'undefined', '']:
#             data_dict[k] = None
#     return schema_obj(**data_dict)


# def check_endpoint_role_access(url, type, current_role_id):
#     #
#     if 'ALL' in endpoint_allowed_roles_dict[type+url]:
#         return

#     if current_role_id not in endpoint_allowed_roles_dict[type+url]:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Отсутствует доступ')


@app.get('/user_tasks/', response_model=list[schemas.Task])
def read_tasks(current_user: Annotated[UserAuth, Depends(get_current_active_user)],
                   skip: int = 0, limit: int = 5, db: Session = Depends(get_db)):
    common_functions.check_endpoint_role_access(url='user_tasks', type='get', current_role_id=current_user.role_id)
    items = crud.get_user_tasks(user_uuid=current_user.uuid, db=db, skip=skip, limit=limit)
    return items


@app.post("/users/", response_model=schemas.User)
def create_user(current_user: Annotated[UserAuth, Depends(get_current_active_user)],
                data: Annotated[schemas.UserCreate, Form()], db: Session = Depends(get_db)):
    common_functions.check_endpoint_role_access(url='users', type='post', current_role_id=current_user.role_id)
    data_none_values_redefined = common_functions.redefine_schema_values_to_none(data, schemas.UserCreate)
    db_user = crud.get_user_by_login(db, login=data_none_values_redefined.login)
    if db_user:
        raise HTTPException(status_code=400, detail="Login already registered")
    return crud.create_user(db=db, user=data_none_values_redefined, 
                            user_uuid=current_user.uuid
                            )


@app.get('/user/', response_model=schemas.User)
def read_user(current_user: Annotated[UserAuth, Depends(get_current_active_user)], db: Session = Depends(get_db)):
    #
    common_functions.check_endpoint_role_access(url='user', type='get', current_role_id=current_user.role_id)
    item = crud.get_user_by_uuid(db, uuid=current_user.uuid)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
