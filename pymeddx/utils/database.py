import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from pathlib import Path


project_dir = Path(__file__).resolve().parent.parent
database_path = os.path.join(project_dir, 'database/survey.db?charset=utf8')
# DATABASE_PATH = str(Path('database/survey.db?charset=utf8').resolve())

SQLALCHEMY_CONN_STRING = 'sqlite:///' + database_path

# SQLAlchemy root class for ORM mapping, all classess that should be mapped must inherit this class
Base = declarative_base()

# SQLAlchemy engine for database manipulations
engine = create_engine(SQLALCHEMY_CONN_STRING)

# this session should be used through all application to issue database commands
session = Session(bind=engine)