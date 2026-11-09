import datetime
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Float, String, Date, Time, DateTime, LargeBinary
from app.database import Base


class User(Base):
    __tablename__ = "users"
    login = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String)
    company = Column(String)
    role_id = Column(Integer)

    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True)
    comment = Column(String)
    created_datetime = Column(DateTime)
    updated_datetime = Column(DateTime, nullable=True, default=None)
    is_active = Column(Boolean, default=True)


class Task(Base):
    __tablename__ = 'tasks'

    uuid = Column(String, unique=True)
    filename = Column(String)
    max_cnt_elems = Column(Integer)
    user_uuid = Column(String)
    status = Column(String)
    processing_path = Column(String, nullable=True, default=None)
    error_text = Column(String, nullable=True, default=None)
    start_time = Column(Time)
    finish_time = Column(Time, nullable=True, default=None)

    # source_pdf_file
    # res_csv_file
    # report_file
    # undecoded_pages_zip

    id = Column(Integer, primary_key=True)
    created_datetime = Column(DateTime)
