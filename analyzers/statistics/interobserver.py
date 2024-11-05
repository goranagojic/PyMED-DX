import itertools
import krippendorff

import numpy as np
import pandas as pd

from typing import Dict, Any
from sqlalchemy import asc, desc
from sklearn.metrics import cohen_kappa_score

from utils.database import session, engine
from utils.logger import logger

from model.response import ResponseType1, ResponseType2
from model.question import QuestionType2
from analyzers.metrics.diagnostic_score import DiagnosticScore


def stats_wrapper(qtype: int, fn: str, **kwargs) -> Dict[Any, float]:
    """
    Executes a specified statistical calculation function on data retrieved based on the `qtype` and `fn` arguments.

    :param qtype:
        The type of questionnaire to retrieve results from the database.
    :param fn:
        The name of the statistical function to run. Valid options are:
            - 'cohens-kappa' - to run Cohen's kappa calculation
    :return:
        DataFrame with the result of the calculation.
    :raises NotImplementedError:
        If `qtype` is not defined in `query_map`.
    """
    query_map = {
        # load info for all answers (response id, observer who have the response, and the score), for all answers
        # to non-redundant questions (questions
        1: session.query(ResponseType1.id, ResponseType1.observer_id, DiagnosticScore.value)
            .join(DiagnosticScore, DiagnosticScore.response_id == ResponseType1.id)
            .where(ResponseType1.is_redundant == False)
            .statement,
        # load infor on all responses without responses on redundant questions
        2: session.query(ResponseType2.id, ResponseType2.observer_id, ResponseType2.choice)
            .join(QuestionType2, ResponseType2.question_id == QuestionType2.id)
            .where(QuestionType2.is_redundant == False)
            .order_by(asc(ResponseType2.observer_id), asc(ResponseType2.id))
            .statement
    }

    # Fetch the query based on qtype or raise error if unsupported
    stmt = query_map.get(qtype)
    if stmt is None:
        raise NotImplementedError(f"Questionnaire type {qtype} is not supported")

    # Load data from database
    data = pd.read_sql(stmt, engine)

    if qtype == 1:
        logger.info(f"Running inter-observer calculations on metric diagnostic score.")
    elif qtype == 2:
        logger.info(f"Running inter-observer calculations on chosen responses.")

        # choice column should be renamed to 'value' so that cohen's and krippendorff coefficients can be calculated
        data.rename(columns={'choice': 'value'}, inplace=True)
    else:
        logger.error(f"Unknown question type {qtype}.")
        raise ValueError(f"Unknown question type {qtype}.")

    if fn.lower() == 'cohens-kappa':
        return cohens_kappa(data)
    elif fn.lower() == 'krippendorff-alpha':
        return krippendorff_alpha(data, **kwargs)
    else:
        logger.warning(f"Unsupported calculation type. This command has no effect.")


def cohens_kappa(data: pd.DataFrame) -> Dict[Any, Any]:
    """
    Calculates the pairwise Cohen's kappa score for inter-observer agreement for multiple observers.

    :param data:
        DataFrame containing 'observer_id' and 'value' columns representing observer ratings.
    :return:
        A DataFrame where rows and columns represent observer IDs, and each cell holds the Cohen's kappa score.
    :raises ValueError:
        If observers do not have responses of the same length, preventing score calculation.
    """
    # Used this link for referent implementation: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html#sklearn.metrics.cohen_kappa_score
    observer_ids = np.unique(data['observer_id'])
    logger.info(f"Found {len(observer_ids)} observers in a database.")

    scores_per_observer = []
    for oid in observer_ids:
        scores_per_observer.append(data[data['observer_id'] == oid]['value'].tolist())

    # Check if all observers has responded to the same number of questions
    reference_length: int = len(scores_per_observer[0])
    if not all(len(scores) == reference_length for scores in scores_per_observer):
        logger.error(f"Inconsistent response lengths between observers. This will prevent Cohen's score calculation. "
                        f"Exiting")
        raise ValueError("Inconsistent response lengths between observers.")

    agreement_matrix = np.zeros((len(observer_ids), len(observer_ids)))
    for i, j in itertools.combinations(range(len(observer_ids)), r=2):
        agreement_matrix[i, j] = cohen_kappa_score(
            scores_per_observer[i],
            scores_per_observer[j]
        )
        agreement_matrix[j, i] = agreement_matrix[i, j]

    agreement_df = pd.DataFrame(agreement_matrix, index=observer_ids, columns=observer_ids)

    return {'pairwise_observers': agreement_df}


def krippendorff_alpha(data: pd.DataFrame, **kwargs) -> Dict[Any, float]:
    """
    Calculates Krippendorff's alpha for inter-rater reliability among multiple users with possiblity
    to calculate pair-wise alpha values as well.

    :param data: A Pandas DataFrame containing observer IDs and their corresponding values.
                 Must contain 'observer_id' and 'value' columns.
    :param pairwise: Calculate pair-wise Krippendorff's alpha score for each distinct observer pair.
    :return: A DataFrame with Krippendorff's alpha values for each pair of observers.
    """
    observer_ids = np.unique(data['observer_id'])

    all_raters = list()
    for oid in observer_ids:
        values = np.array(data[data['observer_id'] == oid]['value'])
        all_raters.append(values)

    retval = dict()
    r = krippendorff.alpha(
        reliability_data=all_raters,
        level_of_measurement='nominal'
    )
    retval['all_observers'] = r

    pairwise = kwargs.get('pairwise')
    if pairwise:
        agreement_matrix = np.zeros((len(observer_ids), len(observer_ids)))
        for i, j in itertools.combinations(range(len(observer_ids)), r=2):
            agreement_matrix[i, j] = krippendorff.alpha(
                reliability_data=[all_raters[i], all_raters[j]],
                level_of_measurement='nominal'
            )
            agreement_matrix[j, i] = agreement_matrix[i, j]

        agreement_df = pd.DataFrame(agreement_matrix, index=observer_ids, columns=observer_ids)
        retval['pairwise_observers'] = agreement_df

    return retval

