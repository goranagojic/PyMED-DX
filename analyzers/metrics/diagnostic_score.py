from utils.database import Base, session

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship


class DiagnosticScore(Base):
    __tablename__ = "diagnostic_score"

    id     = Column(Integer, primary_key=True, autoincrement=True)
    value  = Column(Integer, nullable=False)

    response_id = Column(Integer, ForeignKey("rtype1.id"), nullable=False)
    response = relationship("ResponseType1", back_populates='diagnostic_score')

    def __init__(self, response):
        self.response = response
        self._calculate()

    def __repr__(self):
        return "<Diagnostic score: {}".format(self.value)

    def _calculate(self):
        answer, certainty = self.response.response, self.response.certainty
        with session.no_autoflush:  # FIXME autoflush warning
            diagnoses = self.response.question.image.diagnoses

        if answer == 'not_applicable':
            self.value = 0
        else:
            diagnoses = list(diagnoses)
            diagnoses.append('none')
            if answer in diagnoses:
                self.value = 1
            else:
                self.value = -1
        self.value *= certainty


class DiagnosticScores:

    @staticmethod
    def insert(diagnostic_score):
        try:
            session.add(diagnostic_score)
        except:
            session.rollback()
            raise
        finally:
            session.commit()
