from model.image import Image, Images
from utils.database import Base, session

from sqlalchemy import func
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship


class CopelandScore(Base):
    __tablename__ = "copeland_score"

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(Integer, nullable=False)

    image_id = Column(Integer, ForeignKey("image.id"), nullable=False)
    image = relationship("Image", back_populates="copeland_score")

    def __init__(self, img_id, value):
        self.image = Images.get_by_id(img_id)
        self.value = value

    def __repr__(self):
        return "<Copeland score for image {}: {}>".format(self.image_id, self.value)


class CopelandScores:

    @staticmethod
    def insert(copeland_score):
        try:
            session.add(copeland_score)
        except:
            session.rollback()
            raise
        finally:
            session.commit()

    @staticmethod
    def get_score_group_by_models(return_statement=False):
        """
        Calculate the average Copeland score grouped by model.

        This function queries the database to compute the average Copeland score for images,
        grouped by the model used to generate them. Only images with a non-empty model name
        are considered, effectively excluding reference images (which do not have an assigned
        model name). The results are ordered in descending order of the average Copeland score.

        :param return_statement (bool): If True, returns the SQL statement for the query instead of executing it.

        :return:
            Union[sqlalchemy.sql.elements.TextClause, List[Tuple[str, float]]]:
            - If `return_statement` is True, returns the SQL statement as a TextClause.
            - Otherwise, returns a list of tuples, where each tuple contains:
                - model (str): The name of the model.
                - average_copeland_score (float): The average Copeland score for the model.
        """
        query = (
            session.query(
                Image.model,
                func.avg(CopelandScore.value)
            ).join(Image, CopelandScore.image_id == Image.id)
                .filter(Image.model != "")  # exclude refence images, they are input and thus does not have assigned model name
                .group_by(Image.model)
                .order_by(func.avg(CopelandScore.value).desc())
        )
        if return_statement:
            return query.statement
        else:
            results = query.all()
            return results

    @staticmethod
    def get_score_group_by_datasets(return_statement=False):
        """
        Calculate the average Copeland score grouped by dataset.

        This function queries the database to calculate the average Copeland score for each dataset.
        Images are grouped by their associated dataset, and only images produced by a network
        (i.e., those with a non-empty model name) are considered. Reference images are excluded
        as they serve as input images without an assigned model.

        :param return_statement (bool): If True, returns the SQL statement for the query instead of executing it.

        :return:
            Union[sqlalchemy.sql.elements.TextClause, List[Tuple[str, float]]]:
            - If `return_statement` is True, returns the SQL statement as a TextClause.
            - Otherwise, returns a list of tuples, where each tuple contains:
                - dataset (str): The dataset name.
                - average_copeland_score (float): The average Copeland score for the dataset.
        """
        query = (
            session.query(
                Image.dataset,
                func.avg(CopelandScore.value)
            ).join(Image, CopelandScore.image_id == Image.id)
                .filter(Image.model.isnot(None))    # exclude refence images, they are input and thus does not have assigned model name
                .group_by(Image.dataset)
                .order_by(func.avg(CopelandScore.value).desc())
        )
        if return_statement:
            return query.statement
        else:
            results = query.all()
            return results

    @staticmethod
    def get_score_group_by_observers(return_statement=False):
        # Does not make sense to me to average on observer basis, since
        # scores are assigned to images, and each question contains two images.
        # Maybe if
        raise NotImplementedError
