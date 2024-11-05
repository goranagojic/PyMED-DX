from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from secrets import token_urlsafe

from utils.database import Base, session
from utils.logger import logger


class Observer(Base):
    __tablename__ = "observer"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    created_at   = Column(DateTime, nullable=False)

    responses = relationship("Response", back_populates="observer")

    def __init__(self, name, access_token=None):
        self.name = name
        self.access_token = access_token
        if access_token is None:
            self.access_token = token_urlsafe(nbytes=16)
        self.created_at = datetime.now()


class Observers:
    observers = list()

    @staticmethod
    def insert(name, access_token=None):
        """
        Inserts new observer to the database if the observer with a same access token does not already exist. If the observer
        already exists in a database, the entry from the database is returned and new observer is not created.

        :param name: Observer name.
        :param access_token: Observer access token. Must be different from
        :return:
        """
        if access_token is None:
            result = None
        else:
            result = Observers.get_observer_by_access_token(access_token=access_token)

        if result is None:
            new_observer = Observer(name=name, access_token=access_token)
            try:
                session.add(new_observer)
            except:
                session.rollback()
            finally:
                session.commit()
                return new_observer
        else:
            logger.warning(f"A observer with with access_token '{access_token}' already exists in a database. "
                           f"A duplicate will not be inserted.")
            return result

    @staticmethod
    def update(observer):
        raise NotImplementedError

    @staticmethod
    def delete(observer):
        raise NotImplementedError

    @staticmethod
    def get_observers():
        """
        Returns all observers.

        :return:
        """
        return session.query(Observer).all()

    @staticmethod
    def get_observer_by_access_token(access_token):
        with session.no_autoflush:
            return session.query(Observer).where(Observer.access_token == access_token).first()

    @staticmethod
    def get_observer_by_id(uid):
        with session.no_autoflush: # FIXME autoflush warning
            observer = session.query(Observer).where(Observer.id == uid).first()
        return observer
