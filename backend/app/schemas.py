from datetime import date, datetime, time, timedelta
from typing import Annotated
from enum import Enum
from pydantic import BaseModel, Field, StringConstraints, EmailStr, AfterValidator
from fastapi import UploadFile


class IncomeDocReceived(BaseModel):
    max_cnt_elems: int = Field(default=..., ge=1)
    user_uuid: str

class IncomeDoc(IncomeDocReceived):
    filename: str
    filecontent: bytes

class FileData(BaseModel):
    file_path: str
    file_name: str

class FileDBData(BaseModel):
    file_type: str
    task_uuid: str



################
class Status(str, Enum):
    done = "готово"
    processing = "в обработке"
    error = "ошибка"
    notdecoded = "нераспознано"

###############
class TaskBase(BaseModel):
    uuid: str
    filename: str
    size: int
    max_cnt_elems: int = Field(default=..., ge=1)
    user_uuid: str
    status: Status
    processing_path: str
    error_text: str | None = None
    start_time: time
    finish_time: time | None = None

class TaskCreate(TaskBase):
    source_pdf_file: bytes

# class TaskCreate(BaseModel):
#     uuid: str
#     filename: str
#     source_pdf_file: bytes
#     size: int
#     max_cnt_elems: int = Field(default=..., ge=1)
#     user_uuid: str
#     status: Status
#     processing_path: str
#     error_text: str | None = None
#     start_time: time
#     finish_time: time | None = None
    
class TaskUpdate(BaseModel):
    status: Status
    processing_path: str | None = None
    error_text: str | None = None
    finish_time: time
    res_csv_file: bytes | None = None
    report_file: bytes | None = None
    undecoded_pages_zip: bytes | None = None

class Task(TaskBase):
    id: int
    created_datetime: datetime

    class Config:
        from_attributes = True


####################
class UserBase(BaseModel):
    login: str
    email: str | None = None
    company: str | None = None
    role_id: int

class UserCreate(UserBase):
    password: str | None = None

class UserUpdate(UserBase):
    updated_datetime: datetime

class User(UserBase):
    id: int
    is_active: bool
    uuid: str
    created_datetime: datetime
    updated_datetime: datetime | None

    class Config:
        from_attributes = True




#######################
class CarpassCreate(BaseModel):
    ncar: str
    contact_uuid: str
    dateen: date | str | None = None
    timeen: time | str | None = None
    ntir: str | None = None
    ntir_date: date | str | None = None
    customs_doc: str | None = None
    customs_doc_date: date | str | None = None
    nseal: str | None = None
    nkont: str | None = None
    driver: str | None = None
    driver_fio: str | None = None
    driver_phone: str | None = None
    driver_licence: str | None = None
    car_model: str | None = None
    entry_type: str | None = None
    # place_n: str | None = None  # deprecated

    place_tzone: str | None = None
    place_tcell: str | None = None

    nav_seal: bool
    radiation: bool
    brokenAwning: bool
    brokenSeal: bool
    comment: str | None = None
    dateex: date | str | None = None
    timeex: time | str | None = None
    status: str = 'parking'
    exitcarpass_created: bool = False

class CarpassValidation(BaseModel):
    ncar: str
    dateen: date
    timeen: time
    ntir: str
    ntir_date: date
    # customs_doc: str
    # customs_doc_date: date
    nseal: str
    # nkont: str
    # driver: str
    driver_fio: str
    driver_phone: str
    driver_licence: str
    car_model: str
    entry_type: str
    contact_uuid: str
    # place_n: str

    place_tzone: str
    place_tcell: str

class CarpassUpdate(CarpassCreate):
    updated_datetime: datetime
    
class Carpass(CarpassCreate):
    id: int
    uuid: str
    id_enter: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True

class CarpassJoined(Carpass):
    contact_name: str | None
    place: str | None
    

##############
class ExitcarpassCreate(BaseModel):
    id_enter: str
    contact_uuid: str
    ncar: str
    driver_fio: str
    driver_phone: str
    driver_licence: str
    ndexit: int | str | None = None
    comment: str | None = None
    dateex: date | str | None = None
    timeex: time | str | None = None
    comment_checkpoint: str | None = None
    status: str = 'default'

class ExitcarpassValidation(BaseModel):
    id_enter: str
    ncar: str
    driver_fio: str
    driver_phone: str
    driver_licence: str
    ndexit: str
    # dateex: date
    # timeex: time

class ExitcarpassUpdate(ExitcarpassCreate):
    updated_datetime: datetime
    
class Exitcarpass(ExitcarpassCreate):
    id: int
    uuid: str
    id_exit: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True


class CarExitData(BaseModel):
    comment_checkpoint: str | None = None

# class CarExitDataUpdate(CarExitData):
#     dateex: date
#     timeex: time


#############
class EntryRequestCreate(BaseModel):
    ncar: str
    contact_uuid: str
    dateen: date | str | None = None    # plan_dateen
    timeen: time | str | None = None   # plan_timeen_from
    plan_timeen_to: time | str | None = None
    driver_fio: str | None = None
    driver_licence: str | None = None
    car_model: str | None = None
    entry_type: str | None = None
    # contact: int | str | None = None
    # contact_name: str | None = None
    broker_uuid: str | None = None
    ntir: str | None = None
    ntir_date: date | str | None = None
    customs_doc: str | None = None
    customs_doc_date: date | str | None = None
    warehouse_upload: bool
    comment: str | None = None
    status: str = 'open'
    carpass_created: bool = False

class EntryRequestValidation(BaseModel):
    ncar: str
    contact_uuid: str
    dateen: date
    timeen: time
    plan_timeen_to: time
    driver_fio: str
    driver_licence: str
    car_model: str
    entry_type: str
    # contact: int
    # contact_name: str
    # ntir: str
    # ntir_date: date
    # customs_doc: str
    # customs_doc_date: date

class EntryRequestUpdate(EntryRequestCreate):
    updated_datetime: datetime

class EntryRequest(EntryRequestCreate):
    id: int
    uuid: str
    id_entry_request: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True

class EntryRequestJoined(EntryRequest):
    contact_name: str | None


#####################
class DocumentBase(BaseModel):
    doc_name: str
    related_doc_uuid: str
    customer_name: str
    contact_uuid: str
    post_user_id: str
    filename: str
    filepath: str


class DocumentCreate(DocumentBase):
    filecontent: bytes | None = None


class Document(DocumentBase):
    id: int
    uuid: str
    created_datetime: datetime
    updated_datetime: datetime | None

    class Config:
        from_attributes = True

##############################
class DocumentRecordCreate(BaseModel):
    doc_name: str
    doc_id: str
    doc_date: date
    #contact_uuid: str
    #related_objects_uuid: str | None = None
    user_uuid_create: str
    comment: str | None = None


class DocumentRecordValidation(BaseModel):
    doc_name: str
    doc_id: str
    doc_date: date
    contact_uuid: str

class DocumentRecordUpdate(DocumentRecordCreate):
    updated_datetime: datetime


class DocumentRecord(DocumentRecordCreate):
    id: int
    uuid: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True


class DocumentRecordJoined(DocumentRecord):
    user_uuid: str
    file_name: str
    login: str
    contact: str | None
    contact_uuid: str | None
    attachment_datetime: str

class DocumentRecordJoined2(DocumentRecord):
    filename: str | None

################
class Role(BaseModel):
    role_id: int
    role_name: str
    role_type: str

################


class UserJoined(User):
    contact_name: str | None
    role_name: str | None

class UserFull(UserJoined):
    hashed_password: str | None
    
        
#####
class ContactCreate(BaseModel):
    name: str
    inn: str | None = None
    type: str
    fio: str | None = None
    contract: str | None = None
    phone: str | None = None
    email: str | None = None
    idtelegram: str | None = None
    #linked_broker_uuid: str | None = None   # deprecated
    comment: str | None = None

def is_emails_list(value: str) -> str:
    # email list validator
    class EmailCheck(BaseModel): email: EmailStr
    try:
        for i in value.split(';'):
            email = EmailCheck(email=i.strip())
    except Exception as e:
        raise ValueError(f'{value} is not an list of emails')
    return value

def is_contains_letters(value: str) -> str:
    # check if string contains letters
    try:
        c = int(value)
    except Exception as e:
        raise ValueError(f'{value} contains unacceptable symbols')
    return value
    

class ContactValidation(BaseModel):
    name: str
    inn: Annotated[str, StringConstraints(min_length=10, max_length=12), AfterValidator(is_contains_letters)]
    type: str
    email: Annotated[str, AfterValidator(is_emails_list)] | None = None
    #email: EmailStr | None = None


class ContactUpdate(ContactCreate):
    updated_datetime: datetime

class Contact(ContactCreate):
    id: int
    uuid: str
    #related_obj_uuid: str | None
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True	

###########
class RelatedDocsCreate(BaseModel):
    obj_type: str
    obj_type_name: str
    contact_uuid: str
    obj_uuid: str
    user_uuid: str
    doc_uuid: str

class RelatedDocs(RelatedDocsCreate):
    id: int
    created_datetime: datetime

    class Config:
        from_attributes = True	

###########
class RelatedContactBrokerCreate(BaseModel):
    contact_uuid: str
    broker_uuid: str
    user_uuid_create: str

class RelatedContactBrokerWithJoins(BaseModel):
    id: int
    contact_uuid: str
    broker_uuid: str
    user_uuid_create: str
    broker_name: str
    broker_inn: str

class RelatedBrokerContactWithJoins(BaseModel):
    id: int
    contact_uuid: str
    broker_uuid: str
    user_uuid_create: str
    client_name: str
    client_inn: str

#############
class BatchCreate(BaseModel):
    carpass_uuid: str
    
    # delivery_close_date: date | str | None = None   # 04.03.26
    # delivery_close_time: time | str | None = None   # 04.03.26
    # dt_submission_date: date | str | None = None    # 04.03.26
    # dt_submission_time: time | str | None = None    # 04.03.26

    delivery_close_datetime: datetime | str | None = None   # 04.03.26
    dt_submission_datetime: datetime | str | None = None   # 04.03.26

    status: str = 'на СВХ'
    tn_id: str
    contact_uuid: str
    broker_uuid: str | None = None
    goods: str | None = None
    places_cnt: int | str | None = None
    weight: float | str | None = None
    tnved: str | None = None
    place_tzone: str | None = None
    place_tcell: str | None = None    
    fito_control: bool
    vet_control: bool
    comment: str | None = None


class BatchValidation(BaseModel):
    carpass_uuid: str
    status: str
    tn_id: str
    contact_uuid: str
    goods: str
    places_cnt: int
    weight: float
    place_tzone: str
    place_tcell: str


class BatchUpdate(BatchCreate):
    updated_datetime: datetime


class Batch(BatchCreate):
    id: int
    uuid: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True


class BatchJoined(Batch):
    fwms: bool
    ncar: str | None
    dateen: date | None     
    contact_name: str | None  
    broker_name: str | None   
    docs_exist: int | None
    place: str | None

#########
class LogRecordCreate(BaseModel):
    obj_uuid: str
    obj_type: str
    action: str
    obj_after_action_state: str
    user_uuid: str

class LogRecord(LogRecordCreate):
    id: int
    created_date: date
    created_time: time

class LogRecordJoined(LogRecord):
    user_login: str

###############
class UemailCreate(BaseModel):
    id: str
    adrto: str
    subj: str
    textemail: str
    attachmentfiles: str
    datep: datetime
    user_id: str
    client: str

class Uemail(UemailCreate):
    uniqueindexfield: int

#########
class MessageCreate(BaseModel):
    sender: str
    receiver: str
    msg_text: str
    data: str
    status: str = 'новое'
    is_notification: bool

class Message(MessageCreate):
    id: int
    created_datetime: datetime

#########
class TzoneCreate(BaseModel):
    zone_id: str
    ftk: str
    name_zone: str

class TzoneUpdate(TzoneCreate):
    updated_datetime: datetime

class Tzone(TzoneCreate):
    id: int
    created_datetime: datetime
    updated_datetime: datetime | None

    class Config:
        from_attributes = True

#########
class TcellCreate(BaseModel):
    zone_id: str
    cell_id: str
    note: str | None = None

class Tcell(TcellCreate):
    id: int
    created_datetime: datetime
    updated_datetime: datetime | None

    class Config:
        from_attributes = True

##########
class DtregCreate(BaseModel):
    batch_uuid: str
    declar_id: str | None = None
    is_partial: bool
    comment: str | None = None

class DtregValidation(BaseModel):
    batch_uuid: str
    declar_id: str

class DtregUpdate(DtregCreate):
    updated_datetime: datetime

class Dtreg(DtregCreate):
    id: int
    uuid: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True

class DtregJoined(Dtreg):
    batch_id: int | None
    batch_identity: str | None     


##########
class RequestBatchToSkladCreate(BaseModel):
    batch_uuid: str
    carpass_uuid: str
    comment: str | None = None

class RequestBatchToSkladValidation(BaseModel):
    batch_uuid: str
    carpass_uuid: str

class RequestBatchToSkladUpdate(RequestBatchToSkladCreate):
    updated_datetime: datetime

class RequestBatchToSklad(RequestBatchToSkladCreate):
    id: int
    uuid: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True

class RequestBatchToSkladJoined(RequestBatchToSklad):
    is_completed: bool
    batch_id: int | None
    batch_identity: str | None
    ncar: str | None

class RequestBatchToSkladJoinedForCert(RequestBatchToSklad):
    batch_id: int | None
    batch_identity: str | None
    tn_id: str | None
    contact_name: str | None
    goods: str | None = None
    places_cnt: int | str | None = None
    weight: float | str | None = None


##########
class CertGoodsAcceptCreate(BaseModel):
    request_batch_to_sklad_uuid: str
    batch_uuid: str
    place_tzone: str | None = None
    place_tcell: str | None = None
    goods: str | None = None
    places_cnt: int | str | None = None
    weight: float | str | None = None
    comment: str | None = None

class CertGoodsAcceptValidation(BaseModel):
    request_batch_to_sklad_uuid: str
    batch_uuid: str
    place_tzone: str
    place_tcell: str
    goods: str
    places_cnt: int
    weight: float

class CertGoodsAcceptUpdate(CertGoodsAcceptCreate):
    updated_datetime: datetime

class CertGoodsAccept(CertGoodsAcceptCreate):
    id: int
    uuid: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True

class CertGoodsAcceptJoined(CertGoodsAccept):
    batch_id: int | None
    batch_identity: str | None
    place: str | None
    request_batch_to_sklad_id: int | None



#############
class ShipmentCreate(BaseModel):
    shipment_id: int
    ncar: str
    tir: str
    cmr: str
    status: str
    location: str
    places_cnt: int
    arrival_datetime: datetime | str | None = datetime.now()
    # departure_datetime: datetime | str | None = None
    # doc_submit_datetime: datetime | str | None = None
    # doc_issue_datetime: datetime | str | None = None
    # owner: str
    contact_uuid: str
    goods: str
    comment: str | None = None

class ShipmentUpdate(ShipmentCreate):
    updated_datetime: datetime

class Shipment(ShipmentCreate):
    id: int
    uuid: str

    # status: str
    # arrival_datetime: datetime | str | None = datetime.now()
    departure_datetime: datetime | str | None
    doc_submit_datetime: datetime | str | None
    doc_issue_datetime: datetime | str | None

    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True

class ShipmentJoined(Shipment):   
    contact_name: str | None
    docs_exist: int | None

class ShipmentSetStatus(BaseModel):
    status: str
    status_time: datetime


#########
class TestEntity1Create(BaseModel):
    str_field: str | None = None
    int_field: int | str | None = None
    float_field: float | str | None = None
    dt_field: datetime | str | None = None
    date_field: date | str | None = None
    time_field: time | str | None = None
    comment: str | None = None
    bool_field: bool = False
    contact_uuid: str | None = None
    broker_uuid: str | None = None
    carpass_uuid: str | None = None

class TestEntity1Validation(BaseModel):
    str_field: str
    int_field: int

class TestEntity1Update(TestEntity1Create):
    updated_datetime: datetime
    
class TestEntity1(TestEntity1Create):
    id: int
    uuid: str
    created_datetime: datetime
    updated_datetime: datetime | None
    post_date: datetime | None
    post_user_id: str | None
    posted: bool
    was_posted: bool

    class Config:
        from_attributes = True

class TestEntity1Joined(TestEntity1):
    contact: str | None = None
    broker: str | None = None
    ncar: str | None = None
    docs_exist: int | None
    