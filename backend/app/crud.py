import os, datetime
from fastapi import UploadFile, HTTPException, Depends, status
from pydantic import ValidationError
from sqlalchemy import select, or_, join, distinct
from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from uuid import uuid4
from app import models, schemas



def create_task(item: schemas.TaskCreate, db: Session):
    #
    db_item = models.Task(**item.model_dump(), created_datetime=datetime.datetime.now())
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # logging_action(obj_type='batch', schema=schemas.Batch, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def update_task(item_uuid: str, item: schemas.TaskUpdate, db: Session, ):
    #
    item_from_db = db.query(models.Task).filter(models.Task.uuid == item_uuid).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    for field, value in item.model_dump(exclude_unset=True).items():
        setattr(item_from_db, field, value)
    db.commit()
    # logging_action(obj_type='batch', schema=schemas.Batch, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    return item_from_db


def get_user_tasks(user_uuid: str, db: Session, skip: int = 0, limit: int = 100):
    #
    return db.query(models.Task).filter(models.Task.user_uuid==user_uuid).\
        order_by(models.Task.created_datetime.desc()).all()


def create_user(db: Session, user: schemas.UserCreate, user_uuid: str):
    # creates user in database
    print('user passwird = ', user.password)
    password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password=password_context.hash(user.password)
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())
    
    db_item = models.User(
        **user.model_dump(exclude='password'),
        uuid=uuid,
        hashed_password=hashed_password, 
        created_datetime=created_datetime
        )
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # logging_action(obj_type='user', schema=schemas.User, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)
    return db_item


#########################################################    USER FUNCTIONS
def get_user_by_login(db: Session, login: str):
    #
    response = db.query(models.User).filter(models.User.login==login).first()
    if not response:
        return False
    return response


def get_user(db: Session, user_id: int):
    #
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_login_full(db: Session, login: str):
    #
    main_table = aliased(models.User)
    contact_1 = aliased(models.Contact)
    role_2 = aliased(models.Role)

    response = db.query(main_table, contact_1, role_2).\
            filter(main_table.login==login, main_table.is_active==True).\
            join(contact_1, contact_1.uuid==main_table.contact_uuid, isouter=True).\
            join(role_2, role_2.role_id==main_table.role_id, isouter=True).\
            order_by(main_table.created_datetime.desc()).first()

    contact_name=response[1].__dict__['name'] if response[1] else None
    role_name=response[2].__dict__['role_name'] if response[2] else None

    db_full_response = schemas.UserJoined(**response[0].__dict__, contact_name=contact_name, role_name=role_name)

    return db_full_response


def get_user_by_login_for_auth(db: Session, login: str):
    #
    main_table = aliased(models.User)

    response = db.query(main_table).\
            filter(main_table.login==login, main_table.is_active==True).\
            order_by(main_table.created_datetime.desc()).first()

    if not response:
        return False


    db_full_response = schemas.UserFull(**response[0].__dict__)

    return db_full_response





# def get_users(db: Session, skip: int = 0, limit: int = 100):
#     #
#     stmt = select(models.User, models.Contact).where(models.User.is_active==True,
#                                     models.Contact.uuid == models.User.contact_uuid)
#     response = db.execute(stmt).all()
#     db_full_response = [schemas.UserJoined(**row[0].__dict__, 
#                 contact_name=row[1].__dict__['name']) for row in response]
#     return db_full_response


def get_users(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.User)
    contact_1 = aliased(models.Contact)
    role_2 = aliased(models.Role)

    response = db.query(main_table, contact_1, role_2).\
            filter(main_table.is_active==True, main_table.login!='operator-1').\
            join(contact_1, contact_1.uuid==main_table.contact_uuid, isouter=True).\
            join(role_2, role_2.role_id==main_table.role_id, isouter=True).\
            order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        role_name=row[2].__dict__['role_name'] if row[2] else None
        db_full_response.append(schemas.UserJoined(**row[0].__dict__, contact_name=contact_name, role_name=role_name))

    return db_full_response












def create_uemail(textemail: str, doc_uuid: str, contact_uuid: str, user_uuid: str, db: Session):
    # create record in uemail table
    db_contact = get_contact_by_uuid(db=db, uuid=contact_uuid)
    if not db_contact:
        print(f'[ error ]  ошибка отправки email - в БД отсутствует контакт с uuid {contact_uuid}')
        return
    if not db_contact.email:
        print(f'[ error ]  ошибка отправки email - у контакта {db_contact.name} (ИНН {db_contact.inn}) отсутствует email')
        return 
    adrto = db_contact.email
    # adoptation for current mSender version where email addresses via ,
    adrto = adrto.replace(';', ',')
    
    db_doc = get_document_by_related_doc_uuid(db=db, related_doc_uuid=doc_uuid)
    attachmentfiles = db_doc.filepath.rpartition('\\')[2]

    uemail_rec = schemas.UemailCreate(
        id = str(uuid4()),
        adrto = adrto,
        subj = 'Сервис Управление терминалом - оповещение',
        textemail = textemail,
        attachmentfiles = attachmentfiles,
        datep = datetime.datetime.now(),
        user_id = user_uuid,
        client = contact_uuid,
    )
    
    uemail_rec = models.Uemail(**uemail_rec.model_dump())
    try:
        db.add(uemail_rec); db.commit(); db.refresh(uemail_rec)
    except Exception as err:
        print(err)
        #raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def logging_action(obj_type, schema, action, item_from_db, user_uuid: str, db: Session):
    # logging
    entity_title_name_dict = {
        'Партия товаров': 'batch',
        'Пропуск ТС на въезд': 'carpass',
        'Пропуск ТС на выезд': 'carpass_exit',
        'Заявка на въезд ТС': 'entry_request',
        'Клиент': 'contact',
        'Брокер': 'contact',
        'Пользователь': 'user',
        'Таможенное оформление': 'dtreg',
        'Заявки размещения партий на склад': 'requests_batch_to_sklad',
        'Тестовая сущность 1': 'testen1',
    }

    if obj_type == 'related_docs_record':
        obj_uuid = item_from_db.obj_uuid
        obj_type = entity_title_name_dict.get(item_from_db.obj_type)
    elif obj_type in ['tzone', 'tcell']:
        obj_uuid = '-'
    else:
        obj_uuid = item_from_db.uuid

    log_rec = schemas.LogRecordCreate(
        obj_uuid = obj_uuid,
        obj_type = obj_type,
        action = action,
        obj_after_action_state = str(schema.model_validate(item_from_db).model_dump()),
        user_uuid = user_uuid
    )
    created_date = datetime.date.today()
    created_time = datetime.datetime.now().strftime("%H:%M:%S")
    log_rec = models.LogRecord(**log_rec.model_dump(), created_date = created_date, created_time = created_time)
    try:
        db.add(log_rec); db.commit(); db.refresh(log_rec)
    except Exception as err:
        print(err)
        #raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def attach_doc_to_additional_entity(db: Session, doc_id: int, entity_uuid: str):
    #
    db_document = db.query(models.Document).filter(models.Document.id==doc_id).first()
    if db_document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    related_doc_uuid = db_document.related_doc_uuid
    new_related_doc_uuid = related_doc_uuid + ',' + entity_uuid

    setattr(db_document, 'related_doc_uuid', new_related_doc_uuid)
    db.commit()

    return db_document.id


def create_n_save_document(db: Session, file: UploadFile, document: schemas.DocumentCreate):
    # 
    # add filecontent as blob 
    document.filecontent = file.file.read()

    # save file on disk  !!! create folders system !!!
    if not os.path.exists('saved_files'):
        os.mkdir('saved_files')

    #file_location = f"saved_files/{file.filename}"

    with open(document.filepath, "wb+") as file_object:
        file_object.write(document.filecontent)

    # add record into database
    uuid=str(uuid4())
    created_datetime = datetime.datetime.now()
    db_document = models.Document(**document.model_dump(), uuid=uuid, created_datetime=created_datetime)
    db.add(db_document); db.commit(); db.refresh(db_document)
    
    return db_document.filename


def get_document_by_uuid(db: Session, uuid: str):
    # returns list with 1 item (for frontend compatibility)
    return [db.query(models.Document).filter(models.Document.uuid == uuid, models.Document.is_active==True).first()]


def get_document_by_related_doc_uuid(db: Session, related_doc_uuid: str):
    #
    return db.query(models.Document).filter(models.Document.related_doc_uuid == related_doc_uuid, models.Document.is_active==True).first()


# def get_documents(db: Session, skip: int = 0, limit: int = 100):
def get_document_records(db: Session, skip: int = 0, limit: int = 100):
    # retrives all document_records from database
    main_table = aliased(models.DocumentRecord)
    tbl_2 = aliased(models.Document)

    response = db.query(main_table, tbl_2).\
        filter(main_table.is_active==True).\
        join(tbl_2, tbl_2.related_doc_uuid == main_table.uuid, isouter=True).\
        order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        filename=row[1].__dict__['filename'] if row[1] else ''
        db_full_response.append(schemas.DocumentRecordJoined2(**row[0].__dict__, filename=filename))

    return db_full_response

    # return db.query(models.DocumentRecord).filter(models.DocumentRecord.is_active==True).\
    #     order_by(models.DocumentRecord.created_datetime.desc()).offset(skip).limit(limit).all()


def get_document_records_client(user_uuid: str, user_contact_uuid: str, db: Session, skip: int = 0, limit: int = 100):
    # retrives all document_records from database
    db_related_docs = db.query(models.RelatedDocs).\
           filter(models.RelatedDocs.contact_uuid==user_contact_uuid, models.RelatedDocs.is_active==True).\
           order_by(models.RelatedDocs.created_datetime.desc()).all()
    doc_uuid_list = []
    for rec in db_related_docs:
        doc_uuid_list.append(rec.doc_uuid)

    return db.query(models.DocumentRecord).\
        filter( or_(models.DocumentRecord.user_uuid_create==user_uuid, models.DocumentRecord.uuid.in_(doc_uuid_list)) ).\
        filter(models.DocumentRecord.is_active==True).\
        order_by(models.DocumentRecord.created_datetime.desc()).offset(skip).all()


def get_log_records(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.LogRecord)
    table_2 = aliased(models.User)

    response = db.query(main_table, table_2).\
        join(table_2, table_2.uuid == main_table.user_uuid, isouter=True).\
        order_by(main_table.created_date.desc(), main_table.created_time.desc()).all()

    db_full_response = []
    for row in response:
        user_login=row[1].__dict__['login'] if row[1] else row[0].__dict__['user_uuid']
        db_full_response.append(schemas.LogRecordJoined(**row[0].__dict__, user_login=user_login))

    return db_full_response


def get_batch_log_records(batch_uuid: str, db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.LogRecord)
    table_2 = aliased(models.User)

    response = db.query(main_table, table_2).\
        filter(main_table.obj_uuid==batch_uuid).\
        join(table_2, table_2.uuid == main_table.user_uuid, isouter=True).\
        order_by(main_table.created_date.desc(), main_table.created_time.desc()).all()

    db_full_response = []
    for row in response:
        user_login=row[1].__dict__['login'] if row[1] else row[0].__dict__['user_uuid']
        db_full_response.append(schemas.LogRecordJoined(**row[0].__dict__, user_login=user_login))

    return db_full_response



def get_tzone(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Tzone).order_by(models.Tzone.zone_id).all()


def get_tzone_zone_id(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Tzone.zone_id).order_by(models.Tzone.zone_id).all()


def get_tcell(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Tcell).order_by(models.Tcell.zone_id, models.Tcell.cell_id).all()


def get_tcell_by_zone_id(zone_id: str, db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Tcell).filter(models.Tcell.zone_id==zone_id).order_by(models.Tcell.cell_id).all()


def get_messages(user_login:str, db: Session, notifications:bool=False, new_notifications:bool=False, skip: int = 0, limit: int = 100):
    if new_notifications:
        return db.query(models.Message).filter(models.Message.receiver==user_login, 
                                               models.Message.is_notification==True, models.Message.status=='новое').\
            order_by(models.Message.created_datetime.desc()).all()
    if notifications:
        return db.query(models.Message).filter(models.Message.receiver==user_login, models.Message.is_notification==True).\
            order_by(models.Message.status, models.Message.created_datetime.desc()).all()
    return db.query(models.Message).filter(models.Message.receiver==user_login).\
        order_by(models.Message.created_datetime.desc()).all()


def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Contact).filter(models.Contact.type=='V', models.Contact.is_active==True).\
        order_by(models.Contact.created_datetime.desc()).all()


def get_contacts_posted(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Contact).filter(models.Contact.type=='V', models.Contact.is_active==True, models.Contact.posted==True).\
        order_by(models.Contact.created_datetime.desc()).all()


def get_partners(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Contact).filter(models.Contact.is_active==True).\
        order_by(models.Contact.created_datetime.desc()).all()


def get_partners_posted(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Contact).filter(models.Contact.is_active==True, models.Contact.posted==True).\
        order_by(models.Contact.created_datetime.desc()).all()


def get_roles(partner_type: str, db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Role).filter(models.Role.role_type==partner_type).\
        order_by(models.Role.role_id).all()


def get_brokers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Contact).filter(models.Contact.type=='B', models.Contact.is_active==True).\
        order_by(models.Contact.created_datetime.desc()).all()


def get_brokers_posted(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Contact).filter(models.Contact.type=='B', models.Contact.is_active==True, models.Contact.posted==True).\
        order_by(models.Contact.created_datetime.desc()).all()


def get_brokers_available(contact_uuid: str, db: Session, skip: int = 0, limit: int = 100):
    # get brokers which are not already in the list of related brokers of client
    db_related_contact_brokers = db.query(models.RelatedContactBroker).filter(models.RelatedContactBroker.contact_uuid==contact_uuid, 
                                                 models.RelatedContactBroker.is_active==True).all()

    existing_brokers_uuid_list = []
    for rec in db_related_contact_brokers:
        if rec.broker_uuid not in existing_brokers_uuid_list:
            existing_brokers_uuid_list.append(rec.broker_uuid)

    return db.query(models.Contact).filter(models.Contact.type=='B', models.Contact.is_active==True, models.Contact.posted==True,
                                           models.Contact.uuid.not_in(existing_brokers_uuid_list)).\
        order_by(models.Contact.created_datetime.desc()).all()


# def get_requests_batch_to_sklad(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.RequestBatchToSklad).filter(models.RequestBatchToSklad.is_active==True).\
#         order_by(models.RequestBatchToSklad.created_datetime.desc()).all()


def get_requests_batch_to_sklad(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.RequestBatchToSklad)
    batch = aliased(models.Batch)
    contact = aliased(models.Contact)
    carpass = aliased(models.Carpass)

    response = db.query(main_table, batch, contact, carpass).\
        join(batch, batch.uuid == main_table.batch_uuid, isouter=True).\
        join(contact, contact.uuid == batch.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        batch_id=row[1].__dict__['id'] if row[1] else ''
        batch_tn_id=row[1].__dict__['tn_id'] if row[1] else ''
        batch_client=row[2].__dict__['name'] if row[2] else ''
        batch_identity = f"{batch_tn_id} ({batch_client})"
        ncar=row[3].__dict__['ncar'] if row[3] else None
        db_full_response.append(schemas.RequestBatchToSkladJoined(**row[0].__dict__, batch_id=batch_id, batch_identity=batch_identity, 
                                                    ncar=ncar))

    return db_full_response


def get_requests_batch_to_sklad_for_cert(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.RequestBatchToSklad)
    batch = aliased(models.Batch)
    contact = aliased(models.Contact)

    response = db.query(main_table, batch, contact).\
        filter(main_table.posted==True, main_table.is_completed==False).\
        join(batch, batch.uuid == main_table.batch_uuid, isouter=True).\
        join(contact, contact.uuid == batch.contact_uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        batch_id=row[1].__dict__['id'] if row[1] else ''
        batch_tn_id=row[1].__dict__['tn_id'] if row[1] else ''
        batch_client=row[2].__dict__['name'] if row[2] else ''
        batch_identity = f"{batch_tn_id} ({batch_client})"
        goods=row[1].__dict__['goods'] if row[1] else ''
        places_cnt=row[1].__dict__['places_cnt'] if row[1] else ''
        weight=row[1].__dict__['weight'] if row[1] else ''
        db_full_response.append(schemas.RequestBatchToSkladJoinedForCert(**row[0].__dict__, tn_id=batch_tn_id, 
                    contact_name=batch_client, batch_id=batch_id, batch_identity=batch_identity,
                    goods=goods, places_cnt=places_cnt, weight=weight
                    ))

    return db_full_response


# def get_cert_goods_accept(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.CertGoodsAccept).filter(models.CertGoodsAccept.is_active==True).\
#         order_by(models.CertGoodsAccept.created_datetime.desc()).all()


def get_cert_goods_accept(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.CertGoodsAccept)
    batch = aliased(models.Batch)
    contact = aliased(models.Contact)
    request_goods_accept = aliased(models.RequestBatchToSklad)

    response = db.query(main_table, batch, contact, request_goods_accept).\
        join(batch, batch.uuid == main_table.batch_uuid, isouter=True).\
        join(contact, contact.uuid == batch.contact_uuid, isouter=True).\
        join(request_goods_accept, request_goods_accept.uuid == main_table.request_batch_to_sklad_uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        batch_id=row[1].__dict__['id'] if row[1] else None
        batch_tn_id=row[1].__dict__['tn_id'] if row[1] else ''
        # batch_client=row[1].__dict__['contact_uuid'] if row[1] else ''
        batch_client=row[2].__dict__['name'] if row[2] else ''
        batch_identity = f"{batch_tn_id} ({batch_client})"
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"
        request_batch_to_sklad_id = row[3].__dict__['id'] if row[3] else None
        db_full_response.append(schemas.CertGoodsAcceptJoined(**row[0].__dict__, batch_id=batch_id, batch_identity=batch_identity, 
                                                    place=place, request_batch_to_sklad_id=request_batch_to_sklad_id))

    return db_full_response


# def get_dtregs(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.Dtreg).filter(models.Dtreg.is_active==True).\
#         order_by(models.Dtreg.created_datetime.desc()).all()


def get_dtregs(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Dtreg)
    batch = aliased(models.Batch)
    contact = aliased(models.Contact)

    response = db.query(main_table, batch, contact).\
        join(batch, batch.uuid == main_table.batch_uuid, isouter=True).\
        join(contact, contact.uuid == batch.contact_uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        batch_id=row[1].__dict__['id'] if row[1] else ''
        batch_tn_id=row[1].__dict__['tn_id'] if row[1] else ''
        # batch_client=row[1].__dict__['contact_uuid'] if row[1] else ''
        batch_client=row[2].__dict__['name'] if row[2] else ''
        batch_identity = f"{batch_tn_id} ({batch_client})"
        db_full_response.append(schemas.DtregJoined(**row[0].__dict__, batch_id=batch_id, batch_identity=batch_identity, 
                                                    ))

    return db_full_response


# def get_testen1(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.TestEntity1).filter(models.TestEntity1.is_active==True).\
#         order_by(models.TestEntity1.created_datetime.desc()).all()



def get_testen1(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.TestEntity1)
    broker = aliased(models.Contact)
    contact = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)

    response = db.query(main_table, broker, contact, carpass, related_docs).\
        join(broker, broker.uuid == main_table.broker_uuid, isouter=True).\
        join(contact, contact.uuid == main_table.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        broker_name=row[1].__dict__['name'] if row[1] else None
        broker_inn=row[1].__dict__['inn'] if row[1] else None
        contact_name=row[2].__dict__['name'] if row[2] else None
        contact_inn=row[2].__dict__['inn'] if row[2] else None
        broker=f'{broker_name} ({broker_inn})' if row[1] else None
        contact=f'{contact_name} ({contact_inn})' if row[2] else None
        ncar=row[3].__dict__['ncar'] if row[3] else None
        docs_exist=1 if row[4] else 0
        db_full_response.append(schemas.TestEntity1Joined(**row[0].__dict__, contact=contact, broker=broker, 
                                                    ncar=ncar, docs_exist=docs_exist))

    return db_full_response


# def get_shipments(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.Shipment).filter(models.Shipment.is_active==True).\
#         order_by(models.Shipment.created_datetime.desc()).all()


def get_shipments(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Shipment)
    contact = aliased(models.Contact)
    related_docs = aliased(models.RelatedDocs)

    response = db.query(main_table, contact, related_docs).\
        join(contact, contact.uuid == main_table.contact_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()
    
    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        docs_exist=1 if row[2] else 0
        db_full_response.append(schemas.ShipmentJoined(**row[0].__dict__, contact_name=contact_name, docs_exist=docs_exist))

    return db_full_response


def get_batches(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Batch)
    contact_1 = aliased(models.Contact)
    contact_2 = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)

    response = db.query(main_table, contact_1, contact_2, carpass, related_docs).\
        join(contact_1, contact_1.uuid == main_table.broker_uuid, isouter=True).\
        join(contact_2, contact_2.uuid == main_table.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        broker_name=row[1].__dict__['name'] if row[1] else None
        contact_name=row[2].__dict__['name'] if row[2] else None
        ncar=row[3].__dict__['ncar'] if row[3] else None
        dateen=row[3].__dict__['dateen'] if row[3] else None
        docs_exist=1 if row[4] else 0
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"
        db_full_response.append(schemas.BatchJoined(**row[0].__dict__, contact_name=contact_name, broker_name=broker_name, 
                                                    ncar=ncar, dateen=dateen, docs_exist=docs_exist, place=place))

    return db_full_response


def get_batches_by_carpass_uuid(carpass_uuid: str, db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Batch)
    contact_1 = aliased(models.Contact)
    contact_2 = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)

    response = db.query(main_table, contact_1, contact_2, carpass, related_docs).\
        filter(main_table.carpass_uuid==carpass_uuid).\
        join(contact_1, contact_1.uuid == main_table.broker_uuid, isouter=True).\
        join(contact_2, contact_2.uuid == main_table.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        broker_name=row[1].__dict__['name'] if row[1] else None
        contact_name=row[2].__dict__['name'] if row[2] else None
        ncar=row[3].__dict__['ncar'] if row[3] else None
        dateen=row[3].__dict__['dateen'] if row[3] else None
        docs_exist=1 if row[4] else 0
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"        
        db_full_response.append(schemas.BatchJoined(**row[0].__dict__, contact_name=contact_name, broker_name=broker_name, 
                                                    ncar=ncar, dateen=dateen, docs_exist=docs_exist, place=place))

    return db_full_response


def get_batches_posted(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Batch)
    contact_1 = aliased(models.Contact)
    contact_2 = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)

    response = db.query(main_table, contact_1, contact_2, carpass, related_docs).\
        filter(main_table.posted==True).\
        join(contact_1, contact_1.uuid == main_table.broker_uuid, isouter=True).\
        join(contact_2, contact_2.uuid == main_table.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        broker_name=row[1].__dict__['name'] if row[1] else None
        contact_name=row[2].__dict__['name'] if row[2] else None
        ncar=row[3].__dict__['ncar'] if row[3] else None
        dateen=row[3].__dict__['dateen'] if row[3] else None
        docs_exist=1 if row[4] else 0
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"  
        db_full_response.append(schemas.BatchJoined(**row[0].__dict__, contact_name=contact_name, broker_name=broker_name, 
                                                    ncar=ncar, dateen=dateen, docs_exist=docs_exist, place=place))

    return db_full_response


def get_batches_for_request_goods_accept(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Batch)
    contact_1 = aliased(models.Contact)
    contact_2 = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)

    response = db.query(main_table, contact_1, contact_2, carpass, related_docs).\
        filter(main_table.posted==True, main_table.to_sklad==False, main_table.fwms==False).\
        join(contact_1, contact_1.uuid == main_table.broker_uuid, isouter=True).\
        join(contact_2, contact_2.uuid == main_table.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        broker_name=row[1].__dict__['name'] if row[1] else None
        contact_name=row[2].__dict__['name'] if row[2] else None
        ncar=row[3].__dict__['ncar'] if row[3] else None
        dateen=row[3].__dict__['dateen'] if row[3] else None
        docs_exist=1 if row[4] else 0
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"  
        db_full_response.append(schemas.BatchJoined(**row[0].__dict__, contact_name=contact_name, broker_name=broker_name, 
                                                    ncar=ncar, dateen=dateen, docs_exist=docs_exist, place=place))

    return db_full_response


def get_batches_client(type: str, contact_uuid: str, db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Batch)
    contact_1 = aliased(models.Contact)
    contact_2 = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)  # 19.02.2026

    if type == 'V':
        response = db.query(main_table, contact_1, contact_2, carpass, related_docs).\
            filter(main_table.contact_uuid==contact_uuid).\
            join(contact_1, contact_1.uuid == main_table.broker_uuid, isouter=True).\
            join(contact_2, contact_2.uuid == main_table.contact_uuid, isouter=True).\
            join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
            join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
            distinct(main_table.id).\
            order_by(main_table.id.desc()).all()
    elif type == 'B':
        response = db.query(main_table, contact_1, contact_2, carpass, related_docs).\
            filter(main_table.broker_uuid==contact_uuid).\
            join(contact_1, contact_1.uuid == main_table.broker_uuid, isouter=True).\
            join(contact_2, contact_2.uuid == main_table.contact_uuid, isouter=True).\
            join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
            join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
            distinct(main_table.id).\
            order_by(main_table.id.desc()).all()

    db_full_response = []
    for row in response:
        broker_name=row[1].__dict__['name'] if row[1] else None
        contact_name=row[2].__dict__['name'] if row[2] else None
        ncar=row[3].__dict__['ncar'] if row[3] else None
        dateen=row[3].__dict__['dateen'] if row[3] else None
        docs_exist=1 if row[4] else 0
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"  
        db_full_response.append(schemas.BatchJoined(**row[0].__dict__, contact_name=contact_name, broker_name=broker_name, 
                                                    ncar=ncar, dateen=dateen, docs_exist=docs_exist, place=place))

    return db_full_response


def get_entry_requests(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.EntryRequest)
    contact_1 = aliased(models.Contact)

    response = db.query(main_table, contact_1).\
        join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
        order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        db_full_response.append(schemas.EntryRequestJoined(**row[0].__dict__, contact_name=contact_name))

    return db_full_response


def get_entry_requests_posted(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.EntryRequest)
    contact_1 = aliased(models.Contact)

    response = db.query(main_table, contact_1).\
        filter(main_table.posted==True).\
        join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
        order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        db_full_response.append(schemas.EntryRequestJoined(**row[0].__dict__, contact_name=contact_name))

    return db_full_response


def get_entry_requests_client(type: str, contact_uuid: str, db: Session, skip: int = 0, limit: int = 100):
    #   
    main_table = aliased(models.EntryRequest)
    contact_1 = aliased(models.Contact)

    if type == 'V':
        response = db.query(main_table, contact_1).\
            filter(main_table.contact_uuid==contact_uuid).filter(main_table.is_active == True).\
            join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
            order_by(main_table.dateen, main_table.timeen).all()
    if type == 'B':
        response = db.query(main_table, contact_1).\
            filter(main_table.broker_uuid==contact_uuid).filter(main_table.is_active == True).\
            join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
            order_by(main_table.dateen, main_table.timeen).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        db_full_response.append(schemas.EntryRequestJoined(**row[0].__dict__, contact_name=contact_name))

    return db_full_response


def get_carpasses(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Carpass)
    contact_1 = aliased(models.Contact)

    response = db.query(main_table, contact_1).\
        join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
        order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"
        db_full_response.append(schemas.CarpassJoined(**row[0].__dict__, contact_name=contact_name, place=place))

    return db_full_response


def get_carpasses(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Carpass)
    contact_1 = aliased(models.Contact)

    response = db.query(main_table, contact_1).\
        join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
        order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"
        db_full_response.append(schemas.CarpassJoined(**row[0].__dict__, contact_name=contact_name, place=place))

    return db_full_response


def get_carpasses_posted(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Carpass)
    contact_1 = aliased(models.Contact)

    response = db.query(main_table, contact_1).\
        filter(main_table.posted==True, main_table.is_active==True).\
        join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
        order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"
        db_full_response.append(schemas.CarpassJoined(**row[0].__dict__, contact_name=contact_name, place=place))

    return db_full_response


# def get_carpasses_posted(db: Session, skip: int = 0, limit: int = 100):
#     #
#     return db.query(models.Carpass).filter(models.Carpass.posted==True, models.Carpass.is_active==True).\
#         order_by(models.Carpass.created_datetime.desc()).all()


def get_carpasses_client(type: str, contact_uuid: str, db: Session, skip: int = 0, limit: int = 100):
    #
    # + get client batches - get all batch.carpass_uuid - get add carpasses by carpass_uuid
    db_client_carpasses = db.query(models.Carpass).filter(models.Carpass.contact_uuid==contact_uuid, models.Carpass.is_active==True).all()
    if type == 'V':
        db_client_batches = db.query(models.Batch).filter(models.Batch.contact_uuid==contact_uuid, models.Batch.is_active==True).\
            order_by(models.Batch.created_datetime.desc()).all()
    elif type == 'B':
        db_client_batches = db.query(models.Batch).filter(models.Batch.broker_uuid==contact_uuid, models.Batch.is_active==True).\
            order_by(models.Batch.created_datetime.desc()).all()
    
    carpass_uuid_list = []
    for rec in db_client_carpasses:
        if rec.uuid not in carpass_uuid_list:
            carpass_uuid_list.append(rec.uuid)
    
    for rec in db_client_batches:
        if rec.carpass_uuid not in carpass_uuid_list:
            carpass_uuid_list.append(rec.carpass_uuid)
    
    main_table = aliased(models.Carpass)
    contact_1 = aliased(models.Contact)

    response = db.query(main_table, contact_1).\
        filter(main_table.uuid.in_(carpass_uuid_list)).\
        join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
        order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"
        db_full_response.append(schemas.CarpassJoined(**row[0].__dict__, contact_name=contact_name, place=place))

    return db_full_response


def get_carpasses_posted_not_archival(db: Session, skip: int = 0, limit: int = 100):
    #
    return db.query(models.Carpass).filter(models.Carpass.posted==True, models.Carpass.status!='archival', models.Carpass.is_active==True).\
        order_by(models.Carpass.created_datetime.desc()).all()


def get_cars_at_terminal(db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Carpass)
    contact_1 = aliased(models.Contact)

    response = db.query(main_table, contact_1).\
        filter(main_table.is_active==True, main_table.posted==True, main_table.dateex==None).\
        join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
        order_by(main_table.created_datetime.desc()).all()

    db_full_response = []
    for row in response:
        contact_name=row[1].__dict__['name'] if row[1] else None
        tzone = row[0].__dict__['place_tzone'] if row[0].__dict__['place_tzone'] else ''
        tcell = '/ ' + row[0].__dict__['place_tcell'] if row[0].__dict__['place_tcell'] else ''
        place = f"{tzone} {tcell}"
        db_full_response.append(schemas.CarpassJoined(**row[0].__dict__, contact_name=contact_name, place=place))

    return db_full_response

    # return db.query(models.Carpass).filter(models.Carpass.is_active==True, models.Carpass.posted==True, models.Carpass.dateex==None).\
    #     order_by(models.Carpass.created_datetime.desc()).offset(skip).limit(limit).all()


def get_cars_at_terminal_for_exit(db: Session, skip: int = 0, limit: int = 100):
    #
    return db.query(models.Carpass).filter(models.Carpass.is_active==True, models.Carpass.posted==True, models.Carpass.dateex==None, \
                                           models.Carpass.exitcarpass_created==False).\
        order_by(models.Carpass.created_datetime.desc()).all()


def get_exitcarpasses(db: Session, skip: int = 0, limit: int = 100):
    #
    return db.query(models.Exitcarpass).filter(models.Exitcarpass.is_active == True).\
        order_by(models.Exitcarpass.created_datetime.desc()).all()


def get_exitcarpasses_posted(db: Session, skip: int = 0, limit: int = 100):
    #
    return db.query(models.Exitcarpass).filter(models.Exitcarpass.is_active == True, models.Exitcarpass.posted==True).\
        order_by(models.Exitcarpass.created_datetime.desc()).all()


def get_entry_requests_for_new_carpass(db: Session, skip: int = 0, limit: int = 100):
    # заявки для выпадающего списка при создании нового пропуска на въезд (активные-проведенные-по которым нет пропуска)
    return db.query(models.EntryRequest).filter(models.EntryRequest.is_active==True, models.EntryRequest.posted==True, \
                                                models.EntryRequest.carpass_created==False).\
        order_by(models.EntryRequest.dateen, models.EntryRequest.timeen).all()


def get_ncars_exitcarpasses(db: Session, skip: int = 0, limit: int = 100):
    # get ncar fields from exitcarpasses
    return db.query(models.Exitcarpass.ncar).filter(models.Exitcarpass.is_active == True).order_by(models.Exitcarpass.created_datetime.desc()).all()


#########################################################    CREATE FUNCTIONS
def create_exitcarpass(db: Session, item: schemas.ExitcarpassCreate, user_uuid: str):
    #
    last_created_item_from_db =  db.query(models.Exitcarpass).order_by(models.Exitcarpass.id.desc()).first()
    id_exit = '1' if last_created_item_from_db is None else str(int(last_created_item_from_db.id_exit) + 1)
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.Exitcarpass(**item.model_dump(), uuid=uuid, id_exit=id_exit, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # update carpass set exitcarpass_created = true
    carpass_from_db =  db.query(models.Carpass).filter(models.Carpass.id_enter == item.id_enter).first()
    if carpass_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    setattr(carpass_from_db, 'exitcarpass_created', True)
    db.commit()
    
    logging_action(obj_type='carpass_exit', schema=schemas.Exitcarpass, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def create_testen1(db: Session, item: schemas.TestEntity1Create, user_uuid: str):
    #
    created_datetime = datetime.datetime.now()
    post_date = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.TestEntity1(**item.model_dump(), uuid=uuid, created_datetime=created_datetime, post_date=post_date)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    logging_action(obj_type='testen1', schema=schemas.TestEntity1, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    created_item = get_testen_by_uuid_joined(uuid=uuid, db=db)
    return created_item


def create_shipment(db: Session, item: schemas.ShipmentCreate, user_uuid: str):
    #
    created_datetime = datetime.datetime.now()
    post_date = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.Shipment(**item.model_dump(), uuid=uuid, created_datetime=created_datetime, post_date=post_date)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # set_shipment_status(db=db, shipment_uuid=db_item.uuid, status_name='приехала', user_uuid=user_uuid)
    
    logging_action(obj_type='shipment', schema=schemas.Shipment, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def create_batch(db: Session, item: schemas.BatchCreate, user_uuid: str):
    #
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.Batch(**item.model_dump(), uuid=uuid, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    logging_action(obj_type='batch', schema=schemas.Batch, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def create_dtreg(db: Session, item: schemas.DtregCreate, user_uuid: str):
    #
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.Dtreg(**item.model_dump(), uuid=uuid, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    logging_action(obj_type='dtreg', schema=schemas.Dtreg, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def create_cert_goods_accept(db: Session, item: schemas.CertGoodsAcceptCreate, user_uuid: str):
    #
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.CertGoodsAccept(**item.model_dump(), uuid=uuid, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    logging_action(obj_type='cert_goods_accept', schema=schemas.CertGoodsAccept, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def create_requests_batch_to_sklad(db: Session, item: schemas.RequestBatchToSkladCreate, user_uuid: str):
    #
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.RequestBatchToSklad(**item.model_dump(), uuid=uuid, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    logging_action(obj_type='requests_batch_to_sklad', schema=schemas.RequestBatchToSklad, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def create_message(db: Session, item: schemas.MessageCreate):
    #
    created_datetime = datetime.datetime.now()

    db_item = models.Message(**item.model_dump(), created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return db_item


def create_entry_request(db: Session, item: schemas.EntryRequestCreate, user_uuid: str):
    #
    last_created_item_from_db =  db.query(models.EntryRequest).order_by(models.EntryRequest.id.desc()).first()
    id_entry_request = '1' if last_created_item_from_db is None else str(int(last_created_item_from_db.id_entry_request) + 1)
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.EntryRequest(**item.model_dump(), uuid=uuid, id_entry_request=id_entry_request, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    logging_action(obj_type='entry_request', schema=schemas.EntryRequest, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def create_carpass(db: Session, item: schemas.CarpassCreate, user_uuid: str):
    # creates a enter carpass
    if db.query(models.Carpass).filter(models.Carpass.ncar==item.ncar, models.Carpass.status!='archival').first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Ошибка: пропуск для ТС {item.ncar} создан и активен.")

    last_created_carpass_from_db =  db.query(models.Carpass).order_by(models.Carpass.id.desc()).first()
    id_enter = '1' if last_created_carpass_from_db is None else str(int(last_created_carpass_from_db.id_enter) + 1)
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.Carpass(**item.model_dump(), uuid=uuid, id_enter=id_enter, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # update entry_request set carpass_created = true (if carpass is creating from entry_request)
    entry_request_from_db =  db.query(models.EntryRequest).filter(models.EntryRequest.ncar==item.ncar).first()
    if entry_request_from_db:
        setattr(entry_request_from_db, 'carpass_created', True)
        db.commit()

    logging_action(obj_type='carpass_enter', schema=schemas.Carpass, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)

    return db_item


def create_contact(db: Session, item: schemas.ContactCreate, user_uuid: str):
    # creates a contact in database
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.Contact(**item.model_dump(), uuid=uuid, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    logging_action(obj_type='contact', schema=schemas.Contact, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)
    return db_item


def create_tzone(db: Session, item: schemas.TzoneCreate, user_uuid: str):
    # creates a tzone in database
    created_datetime = datetime.datetime.now()

    db_item = models.Tzone(**item.model_dump(), created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    logging_action(obj_type='tzone', schema=schemas.Tzone, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)
    return db_item


def create_tcell(db: Session, item: schemas.TcellCreate, user_uuid: str):
    # creates a tcell in database
    created_datetime = datetime.datetime.now()

    db_item = models.Tcell(**item.model_dump(), created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print('ошибка =', err)
        print('детали =', str(err.orig))
        if "нарушает ограничение внешнего ключа" in str(err.orig):
            print(str(err.orig).partition('DETAIL:')[2].strip())
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                detail={ 'type': 'ForeignKeyViolation', 'content': str(err.orig).partition('DETAIL:')[2].strip()}
                                        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    logging_action(obj_type='tcell', schema=schemas.Tcell, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)
    return db_item





def create_document_record(db: Session, item: schemas.DocumentRecordCreate, user_uuid: str):
    # creates a record in documents table in database
    created_datetime = datetime.datetime.now()
    uuid=str(uuid4())

    db_item = models.DocumentRecord(**item.model_dump(), uuid=uuid, created_datetime=created_datetime)
    try:
        db.add(db_item); db.commit(); db.refresh(db_item)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    logging_action(obj_type='document_record', schema=schemas.DocumentRecord, action='create', item_from_db=db_item, user_uuid=user_uuid, db=db)
    return db_item


def create_related_docs_record(db: Session, data: schemas.RelatedDocsCreate):
    # creates record in related_docs table
    created_datetime = datetime.datetime.now()

    # add check if the same record exists already!

    record = models.RelatedDocs(obj_type=data.obj_type, obj_type_name=data.obj_type_name, contact_uuid=data.contact_uuid,
        obj_uuid=data.obj_uuid, doc_uuid=data.doc_uuid, user_uuid=data.user_uuid, created_datetime=created_datetime)
    try:
        db.add(record); db.commit(); db.refresh(record)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    logging_action(obj_type='related_docs_record', schema=schemas.RelatedDocs, action='attach_doc', item_from_db=record, user_uuid=data.user_uuid, db=db)
    
    # create uemail
    textemail = f"""
        тестовое сообщение:  
        к {data.obj_type} {data.obj_uuid} добавлен документ {data.doc_uuid}
        дата добавления: {created_datetime} 
        """
    create_uemail(textemail=textemail, doc_uuid=data.doc_uuid, contact_uuid=data.contact_uuid, user_uuid=data.user_uuid, db=db)


    return record


def create_related_contact_broker(db: Session, data: schemas.RelatedContactBrokerCreate):
    # creates record in related_docs table
    created_datetime = datetime.datetime.now()

    # add check if the same record exists already!

    record = models.RelatedContactBroker(contact_uuid=data.contact_uuid,
        broker_uuid=data.broker_uuid, user_uuid_create=data.user_uuid_create, created_datetime=created_datetime)
    try:
        db.add(record); db.commit(); db.refresh(record)
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return record

#########################################################    UPDATE FUNCTIONS




# def update_carpass(db: Session, item_uuid: str, item: schemas.CarpassUpdate, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Carpass).filter(models.Carpass.uuid == item_uuid).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")    
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='carpass_enter', schema=schemas.Carpass, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db

# def update_batch(db: Session, item_uuid: str, item: schemas.BatchUpdate, user_uuid: str):
#     #
#     item_from_db = db.query(models.Batch).filter(models.Batch.uuid == item_uuid).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='batch', schema=schemas.Batch, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db

# def update_entry_request(db: Session, item_uuid: str, item: schemas.EntryRequestUpdate, user_uuid: str):
#     #
#     item_from_db =  db.query(models.EntryRequest).filter(models.EntryRequest.id == item_uuid).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='entry_request', schema=schemas.EntryRequest, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db

# def update_exitcarpass(db: Session, item_id: int, item: schemas.ExitcarpassUpdate, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Exitcarpass).filter(models.Exitcarpass.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='carpass_exit', schema=schemas.Exitcarpass, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db

# def update_dtreg(db: Session, item_id: int, item: schemas.DtregUpdate, user_uuid: str):
#     #
#     item_from_db = db.query(models.Dtreg).filter(models.Dtreg.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='dtreg', schema=schemas.Dtreg, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db

# def update_cert_goods_accept(db: Session, item_id: int, item: schemas.CertGoodsAcceptUpdate, user_uuid: str):
#     #
#     item_from_db = db.query(models.CertGoodsAccept).filter(models.CertGoodsAccept.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='cert_goods_accept', schema=schemas.CertGoodsAccept, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db

# def update_requests_batch_to_sklad(db: Session, item_id: int, item: schemas.RequestBatchToSkladUpdate, user_uuid: str):
#     #
#     item_from_db = db.query(models.RequestBatchToSklad).filter(models.RequestBatchToSklad.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='requests_batch_to_sklad', schema=schemas.RequestBatchToSklad, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db

# def update_contact(db: Session, item_id: int, item: schemas.ContactUpdate, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Contact).filter(models.Contact.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='contact', schema=schemas.Contact, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db

# def update_document_record(db: Session, item_id: int, item: schemas.DocumentRecordUpdate, user_uuid: str):
#     #
#     item_from_db =  db.query(models.DocumentRecord).filter(models.DocumentRecord.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     for field, value in item.model_dump(exclude_unset=True).items():
#         setattr(item_from_db, field, value)
#     db.commit()
#     logging_action(obj_type='document_record', schema=schemas.DocumentRecord, action='update', 
#                    item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db


def update_tzone(db: Session, zone_id: int, item: schemas.TzoneUpdate, user_uuid: str):
    # specifia update function for tzone
    item_from_db =  db.query(models.Tzone).filter(models.Tzone.zone_id == zone_id).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    for field, value in item.model_dump(exclude_unset=True).items():
        setattr(item_from_db, field, value)
    db.commit()

    logging_action(obj_type='tzone', schema=schemas.Tzone, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    return item_from_db


def update_user(db: Session, item_uuid: str, item: schemas.UserUpdate, new_pwd: str, user_uuid: str):
    # specifia update function for user
    item_from_db =  db.query(models.User).filter(models.User.uuid == item_uuid).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    for field, value in item.model_dump(exclude_unset=True).items():
        setattr(item_from_db, field, value)
    db.commit()

    # password change
    if new_pwd:
        password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password=password_context.hash(new_pwd)
        setattr(item_from_db, 'hashed_password', hashed_password)
        db.commit()

    logging_action(obj_type='user', schema=schemas.User, action='update', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    return item_from_db


def car_exit(db: Session, exitcarpass_uuid: str, exit_data: schemas.CarExitData, user_uuid: str):
    #
    item_from_db =  db.query(models.Exitcarpass).filter(models.Exitcarpass.uuid == exitcarpass_uuid).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    dateex = datetime.date.today()
    timeex = datetime.datetime.now().strftime("%H:%M:%S")

    setattr(item_from_db, 'dateex', dateex)
    setattr(item_from_db, 'timeex', timeex)
    setattr(item_from_db, 'comment_checkpoint', exit_data.comment_checkpoint)
    setattr(item_from_db, 'status', 'archival')

    carpass_enter_from_db =  db.query(models.Carpass).filter(models.Carpass.id_enter == item_from_db.id_enter).first()
    setattr(carpass_enter_from_db, 'dateex', dateex)
    setattr(carpass_enter_from_db, 'timeex', timeex)
    setattr(carpass_enter_from_db, 'status', 'archival')
    
    db.commit()

    logging_action(obj_type='carpass_exit', schema=schemas.Exitcarpass, action='car_exit', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    return item_from_db

#########################################################    DELETE FUNCTIONS

def delete_item(model, schema, obj_type, db: Session, item_uuid: str, user_uuid: str):
    # generic delete item function
    item_from_db =  db.query(model).filter(model.uuid == item_uuid).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    try:
        db.delete(item_from_db)
        db.flush()
    except IntegrityError as err:
        db.rollback()
        table_name = err.args[0].partition('таблицы "')[2].partition('"\n')[0]
        msg_detail = f'Ошибка при удалении - есть связанные объекты в таблице {table_name}'
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg_detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can't delete item")
    db.commit()

    # SPECIFIC ACTIONS FOR DIFFERENT ENTITIES
    if obj_type == 'carpass_exit':
    # update carpass set exitcarpass_created = false
        carpass_from_db =  db.query(models.Carpass).filter(models.Carpass.id_enter == item_from_db.id_enter).first()
        if carpass_from_db:
            setattr(carpass_from_db, 'exitcarpass_created', False)
            db.commit()

    if obj_type == 'carpass_enter':
    # update entry_request set carpass_created = false
        entry_request_from_db =  db.query(models.EntryRequest).filter(models.EntryRequest.ncar==item_from_db.ncar).first()
        if entry_request_from_db:
            setattr(entry_request_from_db, 'carpass_created', False)
            db.commit()

    # LOGGING
    logging_action(obj_type=obj_type, schema=schema, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    return {"message": f"User uuid {item_uuid} deleted successfully"}


def delete_related_contact_broker(db: Session, item_id: int):
    # specific delete function for related contact broker
    item_from_db =  db.query(models.RelatedContactBroker).filter(models.RelatedContactBroker.id == item_id).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    try:
        db.delete(item_from_db)
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can't delete item")
    db.commit()
    return {"message": f"Item ID {item_id} deleted successfully"}


def delete_related_docs_record(db: Session, doc_uuid: str, obj_uuid: str, user_contact_uuid: str):
    # specific delete function for related docs
    item_from_db = db.query(models.RelatedDocs).filter(models.RelatedDocs.doc_uuid==doc_uuid,
                                                              models.RelatedDocs.obj_uuid==obj_uuid).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # checking if user has rights to deattach file from object (like in frontend)
    db_docrel_user_contact_uuid = db.query(models.User).filter(models.User.uuid == item_from_db.user_uuid).first().contact_uuid
    if db_docrel_user_contact_uuid != user_contact_uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к файлу")

    try:
        db.delete(item_from_db)
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can't delete item")
    db.commit()
    return {"message": f"Item ID {item_from_db.id} deleted successfully"}


def delete_tzone(db: Session, zone_id: str, user_uuid: str):
    # specific delete function for tzone
    item_from_db = db.query(models.Tzone).filter(models.Tzone.zone_id == zone_id).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    try:
        db.delete(item_from_db)
        db.flush()
    except IntegrityError as err:
        db.rollback()
        table_name = err.args[0].partition('таблицы "')[2].partition('"\n')[0]
        msg_detail = f'Ошибка при удалении - есть связанные объекты в таблице {table_name}'
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg_detail)
    db.commit()
    logging_action(obj_type='tzone', schema=schemas.Tzone, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    return {"message": f"Zone id {zone_id} deleted successfully"}


# def delete_contact(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Contact).filter(models.Contact.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
#     try:
#         db.delete(item_from_db)
#         db.flush()
#     except IntegrityError as err:
#         db.rollback()
#         table_name = err.args[0].partition('таблицы "')[2].partition('"\n')[0]
#         msg_detail = f'Ошибка при удалении - есть связанные объекты в таблице {table_name}'
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg_detail)
#     db.commit()

#     logging_action(obj_type='contact', schema=schemas.Contact, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

#     return {"message": f"Contact id {item_id} deleted successfully"}


# def delete_document_records(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.DocumentRecord).filter(models.DocumentRecord.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
#     try:
#         db.delete(item_from_db)
#         db.flush()
#     except IntegrityError as err:
#         db.rollback()
#         table_name = err.args[0].partition('таблицы "')[2].partition('"\n')[0]
#         msg_detail = f'Ошибка при удалении - есть связанные объекты в таблице {table_name}'
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg_detail)
#     db.commit()

#     logging_action(obj_type='document_record', schema=schemas.DocumentRecord, action='delete', 
#                    item_from_db=item_from_db, user_uuid=user_uuid, db=db)

#     return {"message": f"DocumentRecord id {item_id} deleted successfully"}


# def delete_user(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.User).filter(models.User.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
#     try:
#         db.delete(item_from_db)
#         db.flush()
#     except IntegrityError as err:
#         db.rollback()
#         table_name = err.args[0].partition('таблицы "')[2].partition('"\n')[0]
#         msg_detail = f'Ошибка при удалении - есть связанные объекты в таблице {table_name}'
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg_detail)
#     db.commit()

#     logging_action(obj_type='user', schema=schemas.User, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

#     return {"message": f"User id {item_id} deleted successfully"}


# def delete_batch(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Batch).filter(models.Batch.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     try:
#         db.delete(item_from_db)
#     except Exception as err:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can't delete item")
#     db.commit()
#     logging_action(obj_type='batch', schema=schemas.Batch, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return {"message": f"Item ID {item_id} deleted successfully"}


# def delete_carpass(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Carpass).filter(models.Carpass.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
#     db.delete(item_from_db)
#     db.commit()

#     # update entry_request set carpass_created = false
#     entry_request_from_db =  db.query(models.EntryRequest).filter(models.EntryRequest.ncar==item_from_db.ncar).first()
#     if entry_request_from_db:
#         setattr(entry_request_from_db, 'carpass_created', False)
#         db.commit()

#     logging_action(obj_type='carpass_enter', schema=schemas.Carpass, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return {"message": f"Carpass id {item_id} deleted successfully"}


# def delete_entry_request(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.EntryRequest).filter(models.EntryRequest.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
#     try:
#         db.delete(item_from_db)
#     except Exception as err:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can't delete item")

#     db.commit()

#     logging_action(obj_type='entry_request', schema=schemas.EntryRequest, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

#     return {"message": f"Item ID {item_id} deleted successfully"}


# def delete_dtreg(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Dtreg).filter(models.Dtreg.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     try:
#         db.delete(item_from_db)
#     except Exception as err:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can't delete item")
#     db.commit()
#     logging_action(obj_type='dtreg', schema=schemas.Dtreg, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return {"message": f"Item ID {item_id} deleted successfully"}


# def delete_cert_goods_accept(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.CertGoodsAccept).filter(models.CertGoodsAccept.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     try:
#         db.delete(item_from_db)
#     except Exception as err:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can't delete item")
#     db.commit()
#     logging_action(obj_type='cert_goods_accept', schema=schemas.CertGoodsAccept, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return {"message": f"Item ID {item_id} deleted successfully"}


# def delete_requests_batch_to_sklad(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.RequestBatchToSklad).filter(models.RequestBatchToSklad.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     try:
#         db.delete(item_from_db)
#     except Exception as err:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can't delete item")
#     db.commit()
#     logging_action(obj_type='requests_batch_to_sklad', schema=schemas.RequestBatchToSklad, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return {"message": f"Item ID {item_id} deleted successfully"}


# def delete_exitcarpass(db: Session, carpass_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Exitcarpass).filter(models.Exitcarpass.id == carpass_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     db.delete(item_from_db)
#     db.commit()

#     # update carpass set exitcarpass_created = false
#     carpass_from_db =  db.query(models.Carpass).filter(models.Carpass.id_enter == item_from_db.id_enter).first()
#     if carpass_from_db:
#         setattr(carpass_from_db, 'exitcarpass_created', False)
#         db.commit()

#     ### [ !!! DEVELOPMENT !!! ]  enrich this with saving deleted record into archive table
#     logging_action(obj_type='carpass_exit', schema=schemas.Exitcarpass, action='delete', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    
#     return {"message": f"Exitcarpass id {carpass_id} deleted successfully"}


#
# def deactivate_carpass(db: Session, carpass_id: int):
#     #
#     carpass_from_db =  db.query(models.Carpass).filter(models.Carpass.id == carpass_id).first()
#     if carpass_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
#     setattr(carpass_from_db, 'is_active', False)
#     db.commit()

#     return carpass_from_db.id


# def deactivate_exitcarpass(db: Session, carpass_id: int):
#     #
#     carpass_from_db =  db.query(models.Exitcarpass).filter(models.Exitcarpass.id == carpass_id).first()
#     if carpass_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
#     setattr(carpass_from_db, 'is_active', False)
#     db.commit()

#     # update carpass set exitcarpass_created = false
#     carpass_from_db =  db.query(models.Carpass).filter(models.Carpass.id_enter == carpass_from_db.id_enter).first()
#     if carpass_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     setattr(carpass_from_db, 'exitcarpass_created', False)
#     db.commit()

#     return carpass_from_db.id

#########################################################    POSTING FUNCTIONS
def common_posting_entity_item(db: Session, item_uuid: str, db_model, schema_obj, foo_fields_validation, foo_check_conditions):
# def common_posting_entity_item(db: Session, item_id: int, db_model, schema_obj, foo_fields_validation, foo_check_conditions):
    # COMMON FUNCTION FOR ALL ENTITIES - POSTING ITEMS
    # 01 - get item from db
    item_from_db = db.query(db_model).filter(db_model.uuid == item_uuid).first()
    # item_from_db = db.query(db_model).filter(db_model.id == item_id).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item_from_db.posted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was posted already")
    
    # 02 - check general conditions and data for posting posibility
    foo_check_conditions(item_from_db)

    # 03 - fields validation - check required fields are not empty
    validation_errs = []
    try:
        item_validated = schema_obj(**item_from_db.__dict__)
    except ValidationError as err:
        for e in err.errors():
            # print(e['loc'][0])
            validation_errs.append(e['loc'][0])

    # 04 - fields validation - check values are correct and not contradictory
    correct_fiel_value_errs = foo_fields_validation(item_from_db)
    validation_errs.extend(correct_fiel_value_errs)

    if validation_errs:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={'validation_errors': validation_errs})

    # 05 - save to database
    setattr(item_from_db, 'posted', True)
    setattr(item_from_db, 'was_posted', True)
    setattr(item_from_db, 'post_date', datetime.datetime.now())
    setattr(item_from_db, 'post_user_id', '1')
    db.commit()

    return item_from_db


def posting_carpass(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        #
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.Carpass, 
                               schema_obj=schemas.CarpassValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    # additional actions after posting item
    # write to EntryRequest - set status entered
    entry_request_from_db = db.query(models.EntryRequest).filter(models.EntryRequest.ncar==item_from_db.ncar).first()
    if entry_request_from_db:
        setattr(entry_request_from_db, 'status', 'entered')
        db.commit()

    logging_action(obj_type='carpass_enter', schema=schemas.Carpass, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    return item_from_db


def posting_contact(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.Contact, 
                               schema_obj=schemas.ContactValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='contact', schema=schemas.Contact, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    return item_from_db


def posting_document_record(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.DocumentRecord, 
                               schema_obj=schemas.DocumentRecordValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='document_record', schema=schemas.DocumentRecord, action='posting', 
                   item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    return item_from_db


def posting_user(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.User, 
                               schema_obj=schemas.UserValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='user', schema=schemas.User, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
    return item_from_db


def posting_entry_request(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        if (item_from_db.timeen and item_from_db.plan_timeen_to) and (item_from_db.timeen > item_from_db.plan_timeen_to):
            validation_errs.append('timeen')
            validation_errs.append('plan_timeen_to')
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.EntryRequest, 
                               schema_obj=schemas.EntryRequestValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='entry_request', schema=schemas.EntryRequest, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    return item_from_db


def posting_batch(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        ###
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.Batch, 
                               schema_obj=schemas.BatchValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='batch', schema=schemas.Batch, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    return item_from_db


def posting_testen1(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        ###
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.TestEntity1, 
                               schema_obj=schemas.TestEntity1Validation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='testen1', schema=schemas.TestEntity1, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    return item_from_db


def posting_dtreg(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        ###
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.Dtreg, 
                               schema_obj=schemas.DtregValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='dtreg', schema=schemas.Dtreg, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    new_batch_status = 'Ч.офор.' if item_from_db.is_partial else 'Там.офор.'
    set_batch_status(db=db, batch_uuid=item_from_db.batch_uuid, status=new_batch_status, user_uuid=user_uuid)

    # batch_from_db =  db.query(models.Batch).filter(models.Batch.uuid == item_from_db.batch_uuid).first()
    # setattr(batch_from_db, 'status', new_batch_status)
    # logging_action(obj_type='batch', schema=schemas.Batch, action='set_status', item_from_db=batch_from_db, user_uuid=user_uuid, db=db)

    return item_from_db


def posting_cert_goods_accept(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        ###
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.CertGoodsAccept, 
                               schema_obj=schemas.CertGoodsAcceptValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='cert_goods_accept', schema=schemas.CertGoodsAccept, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    batch_from_db = db.query(models.Batch).filter(models.Batch.uuid == item_from_db.batch_uuid).first()
    setattr(batch_from_db, 'to_sklad', False)
    setattr(batch_from_db, 'fwms', True)
    setattr(batch_from_db, 'place_tzone', item_from_db.place_tzone)
    setattr(batch_from_db, 'place_tcell', item_from_db.place_tcell)
    db.commit()
    logging_action(obj_type='batch', schema=schemas.Batch, action='sklad_accept', item_from_db=batch_from_db, user_uuid=user_uuid, db=db)

    request_batch_to_sklad_from_db = db.query(models.RequestBatchToSklad).\
        filter(models.RequestBatchToSklad.uuid == item_from_db.request_batch_to_sklad_uuid).first()
    setattr(request_batch_to_sklad_from_db, 'is_completed', True)
    db.commit()
    logging_action(obj_type='request_batch_to_sklad', schema=schemas.RequestBatchToSklad, action='completed', item_from_db=request_batch_to_sklad_from_db, user_uuid=user_uuid, db=db)


    return item_from_db


def posting_requests_batch_to_sklad(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        ###
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        pass 

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.RequestBatchToSklad, 
                               schema_obj=schemas.RequestBatchToSkladValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)

    logging_action(obj_type='requests_batch_to_sklad', schema=schemas.RequestBatchToSklad, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    batch_from_db = db.query(models.Batch).filter(models.Batch.uuid == item_from_db.batch_uuid).first()
    setattr(batch_from_db, 'to_sklad', True)
    db.commit()
    logging_action(obj_type='batch', schema=schemas.Batch, action='to_sklad', item_from_db=batch_from_db, user_uuid=user_uuid, db=db)

    return item_from_db


def posting_exitcarpass(db: Session, item_uuid: str, user_uuid: str):
    #
    def foo_fields_validation(item_from_db):
        # fields validation - check values are correct and not contradictory
        validation_errs = []
        ###
        return validation_errs

    def foo_check_conditions(item_from_db):
        # check general conditions and data for posting posibility
        carpass_enter_from_db =  db.query(models.Carpass).filter(models.Carpass.id_enter == item_from_db.id_enter).first()
        if item_from_db is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        if carpass_enter_from_db.status != 'exit_permitted':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Отсутствует разрешение на выезд')

    item_from_db = common_posting_entity_item(db=db, item_uuid=item_uuid, 
                               db_model=models.Exitcarpass, 
                               schema_obj=schemas.ExitcarpassValidation,
                               foo_fields_validation=foo_fields_validation,
                               foo_check_conditions=foo_check_conditions)
    
    # additional actions after posting item
    # write to Carpass - set dateex & timeex for related carpass 
    # dateex = item_from_db.dateex
    # timeex = item_from_db.timeex 
    carpass_enter_from_db =  db.query(models.Carpass).filter(models.Carpass.id_enter == item_from_db.id_enter).first()
    # setattr(carpass_enter_from_db, 'dateex', dateex)
    # setattr(carpass_enter_from_db, 'timeex', timeex)
    # setattr(carpass_enter_from_db, 'status', 'archival')
    setattr(carpass_enter_from_db, 'status', 'for_exit')
    db.commit()

    logging_action(obj_type='carpass_exit', schema=schemas.Exitcarpass, action='posting', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    return item_from_db


#########################################################    ROLLBACK FUNCTIONS
def rollback_item(model, schema, obj_type, db: Session, item_uuid: str, user_uuid: str):
    # generic rollback item function

    item_from_db =  db.query(model).filter(model.uuid == item_uuid).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if not item_from_db.posted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
    
    setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
    db.commit()

    logging_action(obj_type=obj_type, schema=schema, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)

    return item_from_db.id

# def rollback_carpass(db: Session, carpass_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Carpass).filter(models.Carpass.id == carpass_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='carpass_enter', schema=schemas.Carpass, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

# def rollback_exitcarpass(db: Session, carpass_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Exitcarpass).filter(models.Exitcarpass.id == carpass_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='carpass_exit', schema=schemas.Exitcarpass, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

# def rollback_entry_requests(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.EntryRequest).filter(models.EntryRequest.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='entry_request', schema=schemas.EntryRequest, action='rollback', 
#                    item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

# def rollback_batches(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Batch).filter(models.Batch.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='batch', schema=schemas.Batch, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

# def rollback_dtreg(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Dtreg).filter(models.Dtreg.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='dtreg', schema=schemas.Dtreg, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

# def rollback_cert_goods_accept(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.CertGoodsAccept).filter(models.CertGoodsAccept.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='cert_goods_accept', schema=schemas.CertGoodsAccept, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

# def rollback_requests_batch_to_sklad(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.RequestBatchToSklad).filter(models.RequestBatchToSklad.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='requests_batch_to_sklad', schema=schemas.RequestBatchToSklad, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

# def rollback_contact(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.Contact).filter(models.Contact.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='contact', schema=schemas.Contact, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

# def rollback_document_record(db: Session, item_id: int):
#     #
#     item_from_db =  db.query(models.DocumentRecord).filter(models.DocumentRecord.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     return item_from_db.id

# def rollback_user(db: Session, item_id: int, user_uuid: str):
#     #
#     item_from_db =  db.query(models.User).filter(models.User.id == item_id).first()
#     if item_from_db is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
#     if not item_from_db.posted:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
#     setattr(item_from_db, 'posted', False); setattr(item_from_db, 'post_date', None); setattr(item_from_db, 'post_user_id', None)
#     db.commit()
#     logging_action(obj_type='user', schema=schemas.User, action='rollback', item_from_db=item_from_db, user_uuid=user_uuid, db=db)
#     return item_from_db.id

#########################################################    STATUS MANAGING FUNCTIONS
def car_exit_permit(db: Session, carpass_id: int):
    #
    carpass_from_db =  db.query(models.Carpass).filter(models.Carpass.id == carpass_id).first()
    if carpass_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if not carpass_from_db.posted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
    
    if carpass_from_db.status != 'exit_prohibited':
        setattr(carpass_from_db, 'status', 'exit_permitted')
    db.commit()

    return carpass_from_db.id_enter


def set_default_car_status(db: Session, carpass_id: int):
    #
    carpass_from_db =  db.query(models.Carpass).filter(models.Carpass.id == carpass_id).first()
    if carpass_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if not carpass_from_db.posted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
    if carpass_from_db.status != 'archival':
        setattr(carpass_from_db, 'status', 'parking')
        db.commit()

    return carpass_from_db.id


def exit_prohibited(db: Session, carpass_id: int):
    #
    carpass_from_db =  db.query(models.Carpass).filter(models.Carpass.id == carpass_id).first()
    if carpass_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if not carpass_from_db.posted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
    if carpass_from_db.status != 'archival':
        setattr(carpass_from_db, 'status', 'exit_prohibited')
        db.commit()

    return carpass_from_db.id


def set_batch_status(db: Session, batch_uuid: str, status_name: str, user_uuid: str):
    #
    item_from_db = db.query(models.Batch).filter(models.Batch.uuid == batch_uuid).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if not item_from_db.posted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
    setattr(item_from_db, 'status', status_name)
    db.commit()

    logging_action(obj_type='batch', schema=schemas.Batch, action='set_status', item_from_db=item_from_db, 
                   user_uuid=user_uuid, db=db)

    return item_from_db


def set_shipment_status(db: Session, shipment_uuid: str, data: schemas.ShipmentSetStatus, user_uuid: str):
    #
    status_list = ['приехала', 'на стоянке', 'на СВХ', 'на ДО', 'подано', 'выпущено', 'уехала']

    item_from_db = db.query(models.Shipment).filter(models.Shipment.uuid == shipment_uuid).first()
    if item_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    # if not item_from_db.posted:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Item was not posted")
    if data.status not in status_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="wrong status")

    status_time_field = {
        'приехала': 'arrival_datetime',
        'подано': 'doc_submit_datetime',
        'выпущено': 'doc_issue_datetime',
        'уехала': 'departure_datetime',
    }
    # current_time = datetime.datetime.now()
    current_time = data.status_time

    setattr(item_from_db, 'status', data.status)
    if data.status in ['приехала', 'подано', 'выпущено', 'уехала']:
        setattr(item_from_db, status_time_field[data.status], current_time)
    db.commit()

    logging_action(obj_type='shipment', schema=schemas.Shipment, action='set_status', item_from_db=item_from_db, 
                   user_uuid=user_uuid, db=db)

    return item_from_db


def get_carpass_by_id(db: Session, carpass_id: int):
    #
    main_table = aliased(models.Carpass)
    contact_1 = aliased(models.Contact)

    response = db.query(main_table, contact_1).\
        filter(main_table.id == carpass_id).\
        join(contact_1, contact_1.uuid == main_table.contact_uuid, isouter=True).\
        first()

    contact_name=response[1].__dict__['name'] if response[1] else None

    db_full_response = schemas.CarpassJoined(**response[0].__dict__, contact_name=contact_name, place='-')
    
    return db_full_response


def get_batch_by_sys_id(db: Session, item_sys_id: int):
    #
    main_table = aliased(models.Batch)
    contact_1 = aliased(models.Contact)
    contact_2 = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)  # 19.02.2026

    response = db.query(main_table, contact_1, contact_2, carpass, related_docs).\
        filter(main_table.id == item_sys_id).\
        join(contact_1, contact_1.uuid == main_table.broker_uuid, isouter=True).\
        join(contact_2, contact_2.uuid == main_table.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        first()

    broker_name=response[1].__dict__['name'] if response[1] else None
    contact_name=response[2].__dict__['name'] if response[2] else None
    ncar=response[3].__dict__['ncar'] if response[3] else None
    dateen=response[3].__dict__['dateen'] if response[3] else None
    docs_exist=1 if response[4] else 0
    
    db_full_response = schemas.BatchJoined(**response[0].__dict__, contact_name=contact_name, broker_name=broker_name, 
                                           ncar=ncar, dateen=dateen, docs_exist=docs_exist, place='-')
    
    return db_full_response


def get_carpass(db: Session, carpass_id_enter: str):
    # get single carpass from db
    return db.query(models.Carpass).filter(models.Carpass.id_enter == carpass_id_enter).first()


def get_entry_request_by_uuid(db: Session, uuid: str):
    # get single entry_request from db
    return db.query(models.EntryRequest).filter(models.EntryRequest.uuid == uuid).first()


def get_carpass_by_uuid(db: Session, uuid: str):
    # get single entry_request from db
    return db.query(models.Carpass).filter(models.Carpass.uuid == uuid).first()


def get_exitcarpass_by_uuid(db: Session, uuid: str):
    # get single exit carpass from db
    return db.query(models.Exitcarpass).filter(models.Exitcarpass.uuid == uuid).first()


def get_shipment_by_uuid(db: Session, uuid: str):
    # get single shipment from db
    return db.query(models.Shipment).filter(models.Shipment.uuid == uuid).first()


def get_testen1_by_uuid(db: Session, uuid: str):
    # get single testen1 from db
    return db.query(models.TestEntity1).filter(models.TestEntity1.uuid == uuid).first()


def get_testen_by_uuid_joined(uuid: str, db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.TestEntity1)
    contact = aliased(models.Contact)
    broker = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)

    response = db.query(main_table, contact, broker, carpass, related_docs).\
        filter(main_table.uuid==uuid).\
        join(contact, contact.uuid == main_table.broker_uuid, isouter=True).\
        join(broker, broker.uuid == main_table.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).first()

    broker_name=response[1].__dict__['name'] if response[1] else None
    broker_inn=response[1].__dict__['inn'] if response[1] else None
    contact_name=response[2].__dict__['name'] if response[2] else None
    contact_inn=response[2].__dict__['inn'] if response[2] else None
    broker=f'{broker_name} ({broker_inn})' if response[1] else None
    contact=f'{contact_name} ({contact_inn})' if response[2] else None
    ncar=response[3].__dict__['ncar'] if response[3] else None
    docs_exist=1 if response[4] else 0
    db_full_response = schemas.TestEntity1Joined(**response[0].__dict__, contact=contact, broker=broker, 
                                                    ncar=ncar, docs_exist=docs_exist)

    return db_full_response


def get_batch_by_uuid(db: Session, uuid: str):
    # get single entry_request from db
    return db.query(models.Batch).filter(models.Batch.uuid == uuid).first()


def get_batch_by_uuid_joined(uuid: str, db: Session, skip: int = 0, limit: int = 100):
    #
    main_table = aliased(models.Batch)
    contact_1 = aliased(models.Contact)
    contact_2 = aliased(models.Contact)
    carpass = aliased(models.Carpass)
    related_docs = aliased(models.RelatedDocs)

    response = db.query(main_table, contact_1, contact_2, carpass, related_docs).\
        filter(main_table.uuid==uuid).\
        join(contact_1, contact_1.uuid == main_table.broker_uuid, isouter=True).\
        join(contact_2, contact_2.uuid == main_table.contact_uuid, isouter=True).\
        join(carpass, carpass.uuid == main_table.carpass_uuid, isouter=True).\
        join(related_docs, related_docs.obj_uuid == main_table.uuid, isouter=True).\
        distinct(main_table.id).\
        order_by(main_table.id.desc()).first()

    broker_name=response[1].__dict__['name'] if response[1] else None
    contact_name=response[2].__dict__['name'] if response[2] else None
    ncar=response[3].__dict__['ncar'] if response[3] else None
    dateen=response[3].__dict__['dateen'] if response[3] else None
    docs_exist=1 if response[4] else 0
    tzone = response[0].__dict__['place_tzone'] if response[0].__dict__['place_tzone'] else ''
    tcell = '/ ' + response[0].__dict__['place_tcell'] if response[0].__dict__['place_tcell'] else ''
    place = f"{tzone} {tcell}"        
    db_full_response = schemas.BatchJoined(**response[0].__dict__, contact_name=contact_name, broker_name=broker_name, 
                                                    ncar=ncar, dateen=dateen, docs_exist=docs_exist, place=place)

    return db_full_response


def get_dtreg_by_uuid(db: Session, uuid: str):
    # get single dtreg from db
    return db.query(models.Dtreg).filter(models.Dtreg.uuid == uuid).first()


def get_cert_goods_accept_by_uuid(db: Session, uuid: str):
    # get single cert_goods_accept from db
    return db.query(models.CertGoodsAccept).filter(models.CertGoodsAccept.uuid == uuid).first()


def get_requests_batch_to_sklad_by_uuid(db: Session, uuid: str):
    # get single requests_batch_to_sklad from db
    return db.query(models.RequestBatchToSklad).filter(models.RequestBatchToSklad.uuid == uuid).first()


def get_user_by_uuid(db: Session, uuid: str):
    # get single user from db
    return db.query(models.User).filter(models.User.uuid == uuid).first()




#########################################################    CONTACT FUNCTIONS
def get_contact(db: Session, contact_id: int):
    return db.query(models.Contact).filter(models.Contact.id == contact_id).first()


def get_contact_by_uuid(db: Session, uuid: str):
    return db.query(models.Contact).filter(models.Contact.uuid == uuid).first()


def get_broker_by_inn(db: Session, inn: str):
    return db.query(models.Contact).filter(models.Contact.type=='B', models.Contact.inn==inn, models.Contact.posted==True).first()

#########################################################    ROLE FUNCTIONS
def get_role(db: Session, role_id: int):
    return db.query(models.Role).filter(models.Role.role_id == role_id).first()


