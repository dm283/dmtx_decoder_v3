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


# class Message(Base):
#     __tablename__ = 'messages'
#     sender = Column(String)  # username
#     receiver = Column(String)  # username
#     msg_text = Column(String)
#     data = Column(String)   # json
#     status = Column(String)
    
#     id = Column(Integer, primary_key=True)
#     uuid = Column(String, unique=True)
#     created_datetime = Column(DateTime)
