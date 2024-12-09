import base64
import random
import itertools
import json
from PIL import Image as PillowImage

from datetime import datetime
from pathlib import Path
from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy import and_
from string import Template

from utils.database import Base, session
from utils.logger import logger
from utils.tools import minify_json, fisher_yates_shuffle
from model.image import Images
from model.diagnosis import Diagnoses

from localization.locale import *


class Question(Base):
    __tablename__ = "question"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    type        = Column(Integer)
    json        = Column(Text)
    created_at  = Column(DateTime, nullable=False)

    valid_types = [1, 2, 3]

    __mapper_args__ = {
        'polymorphic_identity': 0,
        'polymorphic_on': type,
    }

    regular_survey_id = Column(Integer, ForeignKey("regular_survey.id"))
    control_survey_id = Column(Integer, ForeignKey("control_survey.id"))

    regular_survey = relationship("RegularSurvey", back_populates="questions")
    control_survey = relationship("ControlSurvey", back_populates="questions")

    def __init__(self):
        self.created_at = datetime.now()

    def __repr__(self):
        return "<Question (id: '{}', type: '{}', created at: '{}', in regular survey {}, in control survey {})>".format(
            str(self.id),
            str(self.type),
            str(self.created_at),
            "no" if self.regular_survey is None else "yes",
            "no" if self.control_survey is None else "yes"
        )


class QuestionType1(Question):
    __tablename__   = "qtype1"
    __mapper_args__ = {'polymorphic_identity': 1}

    id       = Column(Integer, ForeignKey("question.id"), primary_key=True)
    image_id = Column(Integer, ForeignKey("image.id"))

    image = relationship("Image", back_populates="questions")
    responses = relationship("ResponseType1", back_populates="question")

    def __repr__(self):
        return super().__repr__() + \
            "\n<QuestionType1 (image id: '{}', image name: '{}')>".format(
            "None" if self.image is None else str(self.image.id),
            "None" if self.image is None else self.image.filename
        )

    def generate(self):
        if self.image is not None:
            question_json = QuestionType1._get_question_template().substitute({
                "quid": self.id,
                "imid": self.image.id,
                "imname": self.image.name,
                "imfname": self.image.filename,
                "questions": QuestionType1._get_questions()
            })
            self.json = minify_json(question_json)
        else:
            logger.error(f"Cannot generate question {self.id} because it does not have associated image.")
            raise ValueError(f"Cannot generate question {self.id} because it does not have associated image.")

    @staticmethod
    def _get_questions():
        diagnoses = Diagnoses.get_all()
        questions_json = ""
        for i, diagnosis in enumerate(diagnoses):
            template = Template(f"""
            {{
                value: "$token",
                text: "{type1_locale_data["positive_answer"]} $name."
            }},
            """).substitute({"token": diagnosis.token, "name": diagnosis.name})
            questions_json += template
        questions_json += Template(f"""
            
            {{
                value: "none",
                text: "{type1_locale_data["negative_answer"]}"
            }}, {{
                value: "not_applicable",
                text: "{type1_locale_data["unclear_image_answer"]}" 
            }}
            """).substitute({})
        return questions_json

    @staticmethod
    def _get_question_template():
        # $quid - id pitanja
        # $imid - id slike vezane za pitanje
        # $imname - ime slike koja se prikazuje, mora da se nalazi u images direktorijumu
        # $imfname - puno ime slike sa ekstenzijom
        # $questions - izgenerisani json za bolesti na slici
        template = Template(f"""
        elements: [
            {{
                type: "html",
                name: "s^_^-q$quid-img",
                html: "<div class='img-zoom-container'><div style='width: 500px; float: left'><img onload=\\"imageZoom('$imname', '$imname-zoom')\\" id='$imname' src='images/$imfname' style='width: 100%'/></div>
                       <div id='$imname-zoom' class='img-zoom-result'></div></div>"
            }},
            {{
                type: "radiogroup",
                name: "s^_^-q$quid-choice",
                isRequired: true,
                state: "expanded",
                title: "{type1_locale_data["question_explanation"]}",
                requiredErrorText: "{type1_locale_data["error_text"]}",
                choices: [
                    $questions
                ]
            }},
            {{
                type: "rating",
                name: "s^_^-q$quid-certainty",
                state: "expanded",
                title: "{type1_locale_data["certainty_question"]}",
                requiredErrorText: "{type1_locale_data["error_text"]}",
                isRequired: true,
                rateMin: 1,
                rateMax: 5,
                minRateDescription: "{type1_locale_data["min_certain"]}",
                maxRateDescription: "{type1_locale_data["max_certain"]}"
            }}
        ]
        """)
        return template


class QuestionType2(Question):
    __tablename__ = "qtype2"
    __mapper_args__ = {'polymorphic_identity': 2}

    id           = Column(Integer, ForeignKey("question.id"), primary_key=True)
    group        = Column(Integer)
    is_redundant = Column(Boolean, nullable=False, default=False)

    ref_question_id = Column(Integer, ForeignKey("qtype2.id"), nullable=True)

    im1_id = Column(Integer, ForeignKey("image.id"))    # comparison image id 1
    im2_id = Column(Integer, ForeignKey("image.id"))    # comparison image id 2
    im0_id = Column(Integer, ForeignKey("image.id"))    # refernce image id

    im1 = relationship("Image", foreign_keys=[im1_id])  # comparison image
    im2 = relationship("Image", foreign_keys=[im2_id])  # comparison image
    im0 = relationship("Image", foreign_keys=[im0_id])  # reference image

    responses = relationship("ResponseType2", back_populates="question")

    def __init__(self, gid, ref_im0, comp_im1, comp_im2, is_redundant=False, ref_question_id=None):
        super(QuestionType2, self).__init__()
        self.group = gid
        self.is_redundant = is_redundant
        self.ref_question_id = ref_question_id
        self.im0 = ref_im0
        self.im0_id = self.im0.id
        self.im1 = comp_im1
        self.im1_id = self.im1.id
        self.im2 = comp_im2
        self.im2_id = self.im2.id

    def __repr__(self):
        return super().__repr__() + \
            "\n<QuestionType2 (reference_image: '{}', image1_id: '{}', image2_id: '{}')>".format(
                "None" if self.im0 is None else str(self.im0_id),
                "None" if self.im1 is None else str(self.im1_id),
                "None" if self.im2 is None else str(self.im2_id)
            )

    def generate(self):
        """
        Generate JSON for a single survey question.
        :return:
        """
        if self.im0 is not None and self.im1 is not None and self.im2 is not None:
            im1path = str(Path(self.im1.root) / self.im1.filename)
            im2path = str(Path(self.im2.root) / self.im2.filename)
            im0path = str(Path(self.im0.root) / self.im0.filename)
            with open(im1path, "rb") as im1f:
                im1hash = "data:image/png;base64," + base64.b64encode(im1f.read()).decode('utf-8')
            with open(im2path, "rb") as im2f:
                im2hash = "data:image/png;base64," + base64.b64encode(im2f.read()).decode('utf-8')
            with open(im0path, "rb") as im0f:
                im0hash = "data:image/png;base64," + base64.b64encode(im0f.read()).decode('utf-8')
            image_width, image_height = PillowImage.open(im1path).size
            question_json = QuestionType2._get_question_template().substitute({
                "quid": self.id,
                "im1id": self.im1.id,
                "im2id": self.im2.id,
                "im0hash": im0hash,
                "im1hash": im1hash,
                "im2hash": im2hash,
                "imwidth": image_width,
                "imheight": image_height
            })
            self.json = minify_json(question_json)
        else:
            if self.im1 is None or self.im2 is None:
                logger.error(f"Cannot generate the question because one of comparison images is None.")
            if self.im0 is None:
                logger.error(f"Cannot generate the question because reference image is None.")
            raise ValueError(f"Cannot generate the question because some of the images has None value. Image triplet "
                             f"({self.im0_id}, {self.im1_id}, {self.im2_id}) (ref_im_id, comp_im_id1, comp_im_id2)" )

    @staticmethod
    def _get_questions():
        raise NotImplementedError

    @staticmethod
    def _get_question_template():
        # $quid         - id pitanja
        # $im1id        - id prve slike
        # $im2id        - id druge slike
        # $im0hash      - base64 hash originalne slike (slike 0)
        # $im1hash      - base64 hash prve segmentacione mape (slike 1)
        # $im2hash      - base64 hash druge segmentacione mape (slike 2)
        # $imwidth      - sirina slike koja se prikazuje
        # $imheight     - visina slike koja se prikazuje
        template = Template(f"""
            elements: [
                {{
                    type: "imagepicker",
                    name: "s^_^-q$quid-im$im1id-im$im2id-img",
                    title: "{type2_locale_data["original_title"]}",
                    hideNumber: true,
                    choices: [
                    {{
                        value: "original",
                        imageLink: "$im0hash"
                    }}
                 ],
                 startWithNewLine: true,
                 readOnly: true,
                 imageTag: "original"
                }},
                {{
                    type: "imagepicker",
                    name: "s^_^-q$quid-im$im1id-im$im2id-impicker",
                    title: "{type2_locale_data["answer_choice_title"]}",
                    hideNumber: true,
                    choices: [
                    {{
                        value: "im$im1id",
                        imageLink: "$im1hash"
                    }},
                    {{
                        value: "im$im2id",
                        imageLink: "$im2hash"
                    }}
                    ],
                    isRequired: true,
                    requiredErrorText: "{type2_locale_data["error_text"]}",
                    startWithNewLine: false,
                    imageTag: "segmaps"
                }}
            ]
        """)
        return template


class Questions:

    @staticmethod
    def insert(question):
        raise NotImplementedError

    @staticmethod
    def bulk_insert(questions):
        try:
            [session.add(q) for q in questions]
        except:
            session.rollback()
            raise
        else:
            session.commit()

    @staticmethod
    def update(question):
        raise NotImplementedError

    @staticmethod
    def delete(question):
        raise NotImplementedError

    @staticmethod
    def get_all():
        return session.query(Question).all()

    @staticmethod
    def get_by_type(type):
        """
        Query a database for all questions of specific type.

        :param type: An integer in interval [0-3].
        :return: A list of Question objects.
        """
        if type not in [0, 1, 2, 3]:
            raise ValueError("Question type must be one of [0, 1, 2, 3]. Given type is {0}".format(type))
        return session.query(Question).where(Question.type == type).all()

    @staticmethod
    def get_by_id(qid, qtype):
        if qtype == 1:
            with session.no_autoflush:
                return session.query(QuestionType1).get(qid)
        else:
            with session.no_autoflush:
                return session.query(QuestionType2).get(qid)

    @staticmethod
    def get_by_image(image):
        raise NotImplementedError

    @staticmethod
    def get_by_network(network):
        raise NotImplementedError

    @staticmethod
    def get_unassigned(types=None):
        """
        Returns all questions of specific types that are not assigned to any regular or control survey.

        :param types: Valid question types.
        :return: List of questions not assigned to any survey
        """
        if types is not None:
            filters = [Question.type == type for type in types]
        else:
            filters = []
        return session.query(Question)\
                      .where(and_(Question.regular_survey == None, Question.control_survey == None))\
                      .filter(*filters)\
                      .all()

    @staticmethod
    def get_in_regular_survey(types=None):
        """
        Returns all questions of specific types that are assigned to any of regular surveys and are not assigned to any of control surveys.

        :param types: Valid question types.
        :return: List of questions assigned only to regular surveys.
        """
        if types is not None:
            filters = [Question.type == type for type in types]
        else:
            filters = []
        return session.query(Question)\
                      .where(and_(Question.regular_survey != None, Question.control_survey == None))\
                      .filter(*filters)\
                      .all()

    @staticmethod
    def get_by_image_group(gid, unassigned=True):
        if unassigned:
            # return all questions of the same group that are not already attached to some of the surveys
            questions = session.query(QuestionType2).where(QuestionType2.group == gid).all()
            return [q for q in questions if q.regular_survey is None]
        else:
            # return all questions of the same group
            return session.query(QuestionType2).where(QuestionType2.group == gid).all()

    @staticmethod
    def get_by_survey(sid):
        questions_r = session.query(Question).where(Question.regular_survey_id == sid).all()
        questions_c = session.query(Question).where(Question.control_survey_id == sid).all()

        if questions_c is None or len(questions_c) == 0:
            assert (questions_r is not None and len(questions_r) != 0)
            return questions_r
        if questions_r is None or len(questions_r) == 0:
            assert (questions_c is not None and len(questions_c) != 0)
            return questions_c

    # @staticmethod
    # def get_associated_images(qid, qtype):
    #     session.query()


    @staticmethod
    def generate_questions_t2(gid, image_group, n_repeat, redundancy=50, n_redundancy=1, flip_images=True):
        """

        :param gid:
        :param image_group:
        :param n_repeat:
        :param redundancy: Should be in percentages. How many questions will be repeated to create redundancy. It should
            be between 0 and 100.
        :return:
        """

        # generate all combinations of images in a group
        # it will be total of 28 image pairs for a group of 8 images
        image_group = [i for i in itertools.combinations(iterable=image_group, r=2)]

        # repeat some pairs to create redundancy, number of pairs is determined according to the redundancy parameter
        # which represents a percent of pairs to be repeated
        assert 0 <= redundancy <= 100
        dupes = list()

        # sample different question indices to duplicate them
        iindices = random.sample(range(0, len(image_group)), (redundancy * len(image_group)) // 100)
        for idx in iindices:
            dupes.append(image_group[idx])
            print(f"Added duplicate image pair ({image_group[idx][0].id}, {image_group[idx][1].id}).")

        # replicate duplicates n_redundancy times
        dupes = dupes * n_redundancy
        # image_group.extend(dupes)

        # shuffle images before creating the questions
        # TODO shuffle later
        # image_group = fisher_yates_shuffle(image_group)

        # get original image for a segmentation mask group
        # the original should be the last image in an array
        original = Images.get_original_for_segmap(image_group[0][0])

        # GENERATE REGULAR QUESTIONS
        # create questions and assign them to the images
        questions = list()
        for i, (im1, im2) in enumerate(image_group):
            q = QuestionType2(
                gid=gid,
                is_redundant=False,
                ref_im0=original,
                comp_im1=im1,
                comp_im2=im2
            )
            questions.append(q)
            print(f"Question {i} is associated with images {im1.id} and {im2.id} (non-redundant).")
        # Shuffle questions to mitigate memory effect
        # In distribution question shuffle
        # questions = fisher_yates_shuffle(questions)
        Questions.bulk_insert(questions)
        logger.debug(f"Inserted {len(questions)} questions to the database.")

        # how many questions are generated, this is for regular measurements
        # n_questions = len(questions)

        # GENERATE REPEATED QUESTIONS
        duplicates = list()
        for idx, (im1, im2) in zip(iindices, dupes):
            q = QuestionType2(
                gid=gid,
                is_redundant=True,
                ref_question_id=questions[idx].id,
                ref_im0=original,
                comp_im1=im1,
                comp_im2=im2
            )
            duplicates.append(q)
            print(f"Question {idx} is associated with images {im1.id} and {im2.id} (redundant).")

        # Shuffle duplicate questions to mitigate memory effect
        # In distribution duplicate shuffle
        duplicates = fisher_yates_shuffle(duplicates)
        Questions.bulk_insert(duplicates)
        logger.debug(f"Inserted {len(duplicates)} duplicates to the database.")
        questions.extend(duplicates)

        # Shuffle both non-duplicate and duplicate questions to mitigate memory effect
        # The final shuffle
        questions = fisher_yates_shuffle(questions)

        return questions

    @staticmethod
    def generate(question_types, n_repeat, image_names=None):
        """
        Generate questions of a given type for a given set of images. If set of images
        is specified, it must be provided as a list of image filenames. If not specified
        the method will generate questions for all images present in a database.

        :param question_types: An integer list of question types. Currently supported type
            values are:
                1 - question type for an experiment 1
                2 - question type for an experiment 2
        :param n_repeat: An integer that specifies how many times will each image from the image group be
            repeated when generating questions.
        :param image_names: A list of string representing image filenames with extension. Filenames
            are case sensitive.
        :return: A list of generated questions.
        """
        logger.info(f"Generating questions of types {question_types}.")
        for qtype in question_types:
            qtype = int(qtype)
            if qtype not in [1, 2]:
                logger.error(f"Cannot generate question of type {qtype}. Valid question types are 1, 2, 3.")
                raise ValueError(f"Cannot generate question of type {qtype}. Valid question types are 1, 2, 3.")

        questions = list()
        for qtype in question_types:
            qtype = int(qtype)
            if qtype == 1:
                if image_names is None:
                    images = Images.get_all()
                else:
                    images = Images.get_by_name(image_names)
                logger.info(f"Loaded {len(images)} images for question generation.")

                for image in images:
                    qt = QuestionType1()
                    qt.image = image
                    questions.append(qt)
                Questions.bulk_insert(questions=questions)
            elif qtype == 2:
                min_group_id = Images.get_min_image_group()
                if min_group_id is None:
                    logger.error(f"Skipping question generation because there are no groups associated with the "
                                 f"images.")
                    raise ValueError(logger.error(f"Skipping question generation because there are no groups associated"
                                                  f" with the images."))

                max_group_id = Images.get_max_image_group()
                for gid in range(min_group_id, max_group_id+1):
                    image_group = Images.get_whole_group(gid)
                    if image_group is None:
                        logger.error(f"There are no images associated with a group {gid}. Aborting.")
                        raise ValueError(f"There are no images associated with a group {gid}. Aborting.")
                    qt = Questions.generate_questions_t2(gid, image_group, n_repeat)
                    questions.extend(qt)

                n_model = len(Images.get_whole_group(min_group_id))
                n_images = max_group_id - min_group_id + 1
                ssize_inter = n_images * (n_model * (n_model - 1)) // 2

                logger.info("")
                logger.info("*" * 100)
                logger.info(f"Expected sample size for inter-observer agreement methods is {ssize_inter} (per observer).")
                ssize_intra = ssize_inter // 2
                logger.info(f"Expected sample size for intra-observer agreement methods is {ssize_intra} (per observer).")
                logger.info(f"Use the reported sample sizes if you want to check if the sample size is large enough to produce "
                            f"reliable results for inter- and intra-observer agreement methods and desired significance "
                            f"level, effect size, and statistical power. For Cohen's kappa and Krippendorff's alpha use "
                            f"the reported sample size for inter-observer agreement. For Cronbach's alpha, Guttman's "
                            f"lambda, and ICC use the sample reported for intra-observer agreement. To do that, we "
                            f"recommend using specialized software for sample size calculation, e.g. GPower "
                            f"(https://www.psychologie.hhu.de/arbeitsgruppen/allgemeine-psychologie-und-arbeitspsychologie/gpower), "
                            f"or online calculators such as Sample Size Calculator (https://wnarifin.github.io/ssc_web.html).")
                logger.info("*" * 100)
            else:
                logger.error(f"Unsupported question type '{qtype}'.")

        logger.info(f"Generated {len(questions)} questions.")
        # Questions.bulk_insert(questions)
        # logger.debug(f"Inserted {len(questions)} questions to the database.")

        # this step must come after the questions are inserted into the database because generation required question id
        [question.generate() for question in questions]

        # update the database to reflect changes in json field
        session.commit()

        return questions



