import json
import logging
import re

from datetime import datetime
from collections import defaultdict
from pathlib import Path

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, SmallInteger, DateTime, Boolean
from sqlalchemy.orm import relationship

from utils.database import Base, session
from model.question import Questions
from model.observer import Observers
from model.survey import Surveys


class Response(Base):
    """
    Class modeling response to a single question in a questionnaire.
    """

    id           = Column(Integer, primary_key=True, autoincrement=True)
    type         = Column(SmallInteger, nullable=False)
    created      = Column(DateTime, nullable=True)
    is_redundant = Column(Boolean, nullable=False)

    survey_id   = Column(Integer, ForeignKey("survey.id"), nullable=False)
    survey      = relationship("Survey", back_populates="responses")
    observer_id = Column(Integer, ForeignKey("observer.id"), nullable=False)
    observer    = relationship("Observer", back_populates="responses")

    __tablename__ = "response"
    __mapper_args__ = {
        'polymorphic_identity': 0,
        'polymorphic_on': type,
    }

    def __init__(self, survey_id, observer_id, is_redundant=False, created=None):
        self.survey = Surveys.get_by_id(survey_id)
        self.observer = Observers.get_observer_by_id(observer_id)
        self.created = created
        self.is_redundant = is_redundant

    def __repr__(self):
        return "<Response (question_id: '{}', given by observer: '{}' in survey: {})>".format(
            self.question.id,
            self.observer.id,
            self.survey.id
        )


class ResponseType1(Response):
    """
    TODO
    """
    __tablename__ = "rtype1"
    __mapper_args__ = {
        'polymorphic_identity': 1
    }

    id          = Column(Integer, ForeignKey("response.id"), primary_key=True)
    response    = Column(SmallInteger, nullable=True)
    certainty   = Column(SmallInteger, nullable=False)

    question_id      = Column(Integer, ForeignKey("qtype1.id"), nullable=False)
    question         = relationship("QuestionType1", back_populates="responses")

    # diagnostic_score_id = Column(Integer, ForeignKey("diagnostic_score.id"), nullable=True)
    diagnostic_score = relationship("DiagnosticScore", back_populates="response")

    def __init__(self, survey_id, question_id, observer_id, response, is_redundant, certainty, created=None):
        super(ResponseType1, self).__init__(
            survey_id=survey_id,
            observer_id=observer_id,
            created=created,
            is_redundant=is_redundant
        )
        self.response = response
        self.certainty = certainty
        self.question = Questions.get_by_id(question_id, qtype=1)
        with session.no_autoflush:  # FIXME autoflush warning
            self.diagnoses = self.question.image.diagnoses

    def __repr__(self):
        return "<Response (question_id: '{}', given by observer: '{}' in survey '{}', type: '{}', " \
               "answer: '{}', certainty: '{}')>".format(
                self.question_id,
                self.observer.name,
                self.survey_id,
                self.type,
                self.response,
                self.certainty
        )


class ResponseType2(Response):
    """
    TODO
    """
    __tablename__ = "rtype2"
    __mapper_args__ = {
        'polymorphic_identity': 2
    }

    id = Column(Integer, ForeignKey("response.id"), primary_key=True)
    choice = Column(SmallInteger, nullable=True)

    question_id = Column(Integer, ForeignKey("qtype2.id"), nullable=False)
    question = relationship("QuestionType2", back_populates="responses")

    img1_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    img2_id = Column(Integer, ForeignKey('image.id'), nullable=False)

    def __init__(self, survey_id, question_id, observer_id, choice, is_redundant, img1_id, img2_id, created=None):
        super(ResponseType2, self).__init__(
            survey_id=survey_id,
            observer_id=observer_id,
            created=created,
            is_redundant=is_redundant
        )
        self.choice = choice

        self.question_id = int(question_id)
        self.question = Questions.get_by_id(self.question_id, qtype=2)

        self.img1_id = int(img1_id)
        self.img2_id = int(img2_id)

        qim_im1 = self.question.im1
        qim_im2 = self.question.im2

        assert self.img1_id == qim_im1.id
        self.img1 = qim_im1
        assert self.img2_id == qim_im2.id
        self.img2 = qim_im2.id

    def __repr__(self):
        return "<Response (question_id: '{}', given by observer: '{}' in survey '{}', type: '{}', " \
               "choice: '{}'). Associated with images '{}' and '{}'>".format(
                self.question_id,
                self.observer.name,
                self.survey_id,
                self.type,
                self.choice,
                self.img1_id,
                self.img2_id
        )


class Responses:

    @staticmethod
    def insert(response):
        try:
            session.add(response)
        except:
            session.rollback()
            raise
        finally:
            session.commit()

    @staticmethod
    def get_all_responses(type):
        if type == 1:
            responses = session.query(ResponseType1).all()
        else:
            responses = session.query(ResponseType2).all()
        return responses


    @staticmethod
    def get_reponses_for_question(question):
        raise NotImplementedError

    @staticmethod
    def get_responses_for_observer(observer):
        raise NotImplementedError

    @staticmethod
    def get_responses_for_image(image):
        raise NotImplementedError

    @staticmethod
    def get_responses(observer, question):
        raise NotImplementedError

    @staticmethod
    def load_from_file(file, observer_id, qtype):
        # Create a Path object
        file_path = Path(file)

        # Check if the file exists
        if not file_path.exists():
            raise FileNotFoundError(f"The file '{file}' does not exist.")

        # Attempt to open and load the JSON data
        try:
            with file_path.open('r') as f:
                response_content = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON from '{file}': {e}")

        # Extract fields from the JSON data
        happened_at = int(response_content.get("HappenedAt"))
        happened_at = datetime.fromtimestamp(happened_at / 1000) # js Date.now() exports number of milliseconds, should be converted to number of seconds

        result_count = response_content.get("ResultCount")

        responses = response_content.get("Data", [])
        assert len(responses) == result_count, logging.error(f"There are responses for {len(responses)} surveys in "
                                                             f"file '{file}'. Expecting {result_count} responses."
                                                             f"Seems like someone has messed up with a file's content.")
        responses = responses[0]
        # FIXME vec ovde treba da krene uslovni deo qtype == 1
        if qtype == 1:
            # dictionary is in the following format
            # {
            #   's1-q1-choice': 'c1',
            #   's1-q1-certainty': 1,
            #   's1-q2-choice': 'c2',
            #   's1-q2-certainty': 2,
            # }
            # creates a nested dict with the following format
            # {
            #   's1-q1': {choice: 'c1', certainty: 1},
            #   's1-q2': {choice: 'c2', certainty: 2},
            # }
            complete_responses = defaultdict(dict)
            for key, response in responses.items():
                key, response_t = key.rsplit('-', 1)
                complete_responses[key][response_t] = response
            complete_responses = dict(complete_responses)

            # extract fields for Response object
            for key, c_response in complete_responses.items():
                survey_id, question_id = key.split('-')
                survey_id = int(survey_id[1:])
                question_id = int(question_id[1:])
                is_redundant = True if 'control' in file_path.stem else False
                choice = c_response['choice']
                certainty = int(c_response['certainty'])

                response = ResponseType1(
                    created=happened_at,
                    survey_id=survey_id,
                    question_id=question_id,
                    observer_id=observer_id,
                    is_redundant=is_redundant,
                    response=choice,
                    certainty=certainty
                )
                Responses.insert(response)
        else:
            # Regular expression pattern to match the required components
            pattern = r"s(?P<survey_id>\d+)-q(?P<question_id>\d+)-im(?P<image1_id>\d+)-im(?P<image2_id>\d+)-.*"

            # A set with identifiers of already inserted responses
            response_lookup = set()

            for key, value in responses.items():
                match = re.match(pattern, key)

                # Extract response components from response key
                survey_id = match.group('survey_id')
                question_id = match.group('question_id')
                image1_id = match.group('image1_id')
                image2_id = match.group('image2_id')

                # Check if there is already a response for the same question.
                # If yes, mark response as redundant.
                lookup_key, reversed_lookup_key = f"{image1_id}-{image2_id}", f"{image2_id}-{image1_id}"
                if lookup_key in response_lookup or reversed_lookup_key in response_lookup:
                    is_redundant = True
                else:
                    is_redundant = False
                    response_lookup.add(lookup_key)

                # Create and insert response
                response = ResponseType2(
                    survey_id=survey_id,
                    question_id=question_id,
                    observer_id=observer_id,
                    choice=value.replace('im', ''),
                    is_redundant=is_redundant,
                    img1_id=image1_id,
                    img2_id=image2_id,
                    created=happened_at
                )
                Responses.insert(response)


