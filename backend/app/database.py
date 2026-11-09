import sys, os, configparser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

config = configparser.ConfigParser()
config_file = BASE_DIR / 'config.ini'
if os.path.exists(config_file): config.read(config_file, encoding='utf-8')
else: print("error! config file doesn't exist"); sys.exit()


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

DEV = config['main']['dev']

DB_USER = config['db']['user']
DB_PWD = quote_plus(config['db']['pwd'])
DB_SERVER = config['db']['server']
DB_NAME = config['db']['db_name']

SQLALCHEMY_DATABASE_URL = f'postgresql://{DB_USER}:{DB_PWD}@{DB_SERVER}/{DB_NAME}'

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
