import itertools

import numpy as np
import pandas as pd
import pingouin as pg  # library for Cronbach's alpha

from analyzers.metrics.diagnostic_score import DiagnosticScore
from model.question import Question, QuestionType1, QuestionType2
from model.response import ResponseType1, ResponseType2
from utils.database import engine, session
from utils.logger import logger

from sqlalchemy import select, and_, asc
from sqlalchemy.orm import aliased

from typing import List


def stats_wrapper(qtype: int, fn: str, observer_ids: List[str], **kwargs) -> dict[any, float]:
    """
    Executes a specified statistical calculation function on data retrieved based on the `qtype` and `fn` arguments.

    :param qtype:
        The type of questionnaire to retrieve results from the database.
    :param fn:
        The name of the statistical function to run. Valid options are:
            - 'cronbachs-alpha' - to run Cronbach's alpha calculation
            - 'guttmans-lambda-1' - to run Guttman's lambda 1 calculation
            - 'guttmans-lambda-2' - to run Guttman's lambda 2 calculation
            - 'guttmans-lambda-3' - to run Guttman's lambda 3 calculation
            - 'guttmans-lambda-4' - to run Guttman's lambda 4 calculation
            - 'guttmans-lambda-5' - to run Guttman's lambda 5 calculation
            - 'guttmans-lambda-6' - to run Guttman's lambda 6 calculation
            - 'icc' - to run intraclass correlation calculation
    :return:
        DataFrame with the result of the calculation.
    :raises NotImplementedError:
        If `qtype` is not defined in `query_map`.
    """
    if len(observer_ids) == 0:
        logger.error(f"No observers are specified. Exiting.")
        exit(1)

    # logger.info(f"Loading repeated measurements for intra-observer agreement evaluation.")
    if qtype == 1:
        # extract responses of redundant questions
        redundant_stmt = session.query(
            ResponseType1.id,
            ResponseType1.question_id,
            ResponseType1.observer_id,
            ResponseType1.is_redundant,
            DiagnosticScore.value
        ).join(DiagnosticScore, DiagnosticScore.response_id == ResponseType1.id)\
            .where(ResponseType1.is_redundant == True)\
            .statement
        redundant_df = pd.read_sql(redundant_stmt, engine)
        # redundant_df.to_csv("redudantni.csv")

        # extract responses of regular counterparts for redundant questions.
        question_ids = redundant_df['question_id']
        if len(question_ids) == 0:
            logger.error(f"Cannot perform intra-observer agreement, because there are no control measurements.")
            return

        pairs_stmt = (select(
            ResponseType1.id,
            ResponseType1.question_id,
            ResponseType1.observer_id,
            ResponseType1.is_redundant,
            DiagnosticScore.value
        ).join(DiagnosticScore, ResponseType1.id == DiagnosticScore.response_id)
            .where(
                and_(
                    ResponseType1.question_id.in_(question_ids),
                    ResponseType1.is_redundant == False
                )
            )
        )
        paired_df = pd.read_sql(
            str(pairs_stmt.compile(compile_kwargs={"literal_binds": True})), engine
        )
        paired_df = pd.merge(paired_df, redundant_df, on=["question_id", "observer_id"])
        # paired_df.to_csv("ostalo.csv")
    else:
        ResponseType2Ref = aliased(ResponseType2)

        # implement data fetching for QT2
        query = session.query(ResponseType2.observer_id, ResponseType2.observer_id, ResponseType2.choice, ResponseType2Ref.choice) \
            .join(QuestionType2, QuestionType2.id == ResponseType2.question_id) \
            .join(ResponseType2Ref, QuestionType2.ref_question_id == ResponseType2Ref.question_id)\
            .order_by(asc(ResponseType2.observer_id), asc(ResponseType2.id))\
            .statement

        paired_df = pd.read_sql(query, engine)
        if paired_df.empty:
            logger.error(f"Cannot perform intra-observer agreement, because there are no control measurements.")
            return None

        paired_df.drop('observer_id__1', axis=1, inplace=True)
        paired_df.rename(columns={'choice': 'value_x'}, inplace=True)
        paired_df.rename(columns={'rtype2_choice': 'value_y'}, inplace=True)

    scores_per_observer = []
    for oid in observer_ids:
        observer_data = paired_df[paired_df['observer_id'] == oid]
        scores_per_observer.append(observer_data['value_x'].tolist())   # original measures
        scores_per_observer.append(observer_data['value_y'].tolist())   # repeated measures (this means that each original question has a single repeated question)

        # Uncomment to test results
        # scores_per_observer = testing_scores(1)

        if fn.lower() == 'actionbars-alpha':
            r = cronbachs_alpha(scores_per_observer)
            print(f"[observer {oid}] Cronbach's alpha value: {r['alpha']}")
            print(f"[observer {oid}] Cronbach's alpha 95-percent confidence interval: {r['95-percent-confidence-interval']}")
        elif fn.lower() == 'guttmans-lambda-1':
            r = guttman_lambda_1(scores_per_observer, **kwargs)
            print(f"[observer {oid}] Guttman's lambda 1 value: {r['L1']}")
        elif fn.lower() == 'guttmans-lambda-2':
            r = guttman_lambda_2(scores_per_observer, **kwargs)
            print(f"[observer {oid}] Guttman's lambda 2 value: {r['L2']}")
        elif fn.lower() == 'guttmans-lambda-3':
            r = guttman_lambda_3(scores_per_observer, **kwargs)
            print(f"[observer {oid}] Guttman's lambda 3 value: {r['L3']}")
        elif fn.lower() == 'guttmans-lambda-4':
            logger.warning(f"Lambda 4 calculation is currently unsupported. The existing implementation is resource "
                           f"inefficient.")
            # r = guttman_lambda_4(scores_per_observer, **kwargs)
            # print(f"[observer {oid}] Guttman's lambda 4 value: {r['L4']}")
        elif fn.lower() == 'guttmans-lambda-5':
            r = guttman_lambda_5(scores_per_observer, **kwargs)
            print(f"[observer {oid}] Guttman's lambda 5 value: {r['L5']}")
        elif fn.lower() == 'guttmans-lambda-6':
            r = guttman_lambda_6(scores_per_observer, **kwargs)
            print(f"[observer {oid}] Guttman's lambda 6 value: {r['L6']}")
        elif fn.lower() == 'icc':
            r = icc(scores_per_observer, **kwargs)
            print(f"[observer {oid}] ICC table: {r['icc_table']}")
        else:
            logger.warning(f"Unsupported calculation type. This command has no effect.")


def cronbachs_alpha(scores_per_observer: list[list[float]]) -> dict[any, any]:
    """
    Calculate Cronbach'a alpha score.

    Three different formulas exist, k is number of items:
    1) Original from paper: alpha = k/(k-1) * (1 - (sum variance_over_persons_of_the_n_items)/variance_over_person_of_the_sum_of_n_items) - formula is identical to Guttman Lambda 3
    2) Formula from Wikipedia and others: alpha = k*c / (v + (k-1)*c), where v is average item variance, c is average covariance between items
    3) Formula from blog: alpha = k*r / (1 + (k-1)*r), where r is mean correlation
    We used the pre-implemented formula from pingouin.

    Used this link for referent implementation: https://www.educative.io/answers/how-to-implement-cronbachs-alpha-for-reliability-in-python
    """
    # Transform the list of lists into a DataFrame
    df = pd.DataFrame({f'P{i+1}': col for i, col in enumerate(scores_per_observer)})

    cronbach = pg.cronbach_alpha(data=df)

    return {'alpha': cronbach[0], '95-percent-confidence-interval': cronbach[1]}


def guttman_lambda_1(scores_per_observer: list[list[float]]) -> dict[any, any]:
    """
    Formula from the original paper.

    For a given trial, let s_1^2 , s_2^2, ..., s_n^2 be the variances over persons of the n items in the test,
    and let s_t^2 be the variance over persons of the sum of the items.

    Lambda 1 can be computed from the following formula:

    L1 = 1 - (sum[1..n] s_j^2)/s_t^2

    http://moodle3.f.bg.ac.rs/pluginfile.php/1053/mod_resource/content/1/Callender_Osburn_-_An_Empirical_COmparison_of_Coefficient_Alpha_Gutman_s_Lambda_-_2_and_Msplit_Maximized_Split-Half_Reliability_Estimates.pdf
    """
    n_items = len(scores_per_observer[0])
    n_persons = len(scores_per_observer)

    # The variances over persons of the n items in the test
    s_j2 = np.var(scores_per_observer, axis=0, ddof=0)
    assert len(s_j2) == n_items, 'Guttman lambda 1: lengths do not match, we should get a list of length n_items'
    sum_s_j2 = np.sum(s_j2) # The variance over persons of the sum of the items
    sum_items = np.sum(scores_per_observer, axis=1)
    assert len(sum_items) == n_persons, 'Guttman lambda 1: lengths do not match, we should get a list of length n_persons'
    s_t2 = np.var(sum_items)

    L1 = 1- sum_s_j2/s_t2

    return {'L1': L1}


def guttman_lambda_2(scores_per_observer: list[list[float]]) -> dict[any, any]:
    """
    Formula from the original paper.

    The sum of squares of the covariances between items for the given trial is denoted by C_2
    L2 = L1 + sqrt(n/(n-1) C_2)/s_t^2
    """
    n_items = len(scores_per_observer[0])
    n_persons = len(scores_per_observer)

    cov = np.cov(np.array(scores_per_observer).T)
    assert cov.shape == (n_items, n_items), 'Guttman lambda 2: Covariance matrix shape is invalid, it should be of shape (n_items, n_items)'
    cov2 = np.power(cov, 2)
    C2 = np.sum(cov2) - np.sum(np.diag(cov2))

    # The variance over persons of the sum of the items
    sum_items = np.sum(scores_per_observer, axis=1)
    assert len(sum_items) == n_persons, 'Guttman lambda 2: lengths do not match, we should get a list of length n_persons'
    s_t2 = np.var(sum_items)

    L1 = guttman_lambda_1(scores_per_observer)['L1']

    L2 = L1 + np.sqrt(n_items/(n_items-1)*C2)/s_t2

    return {'L2': L2}


def guttman_lambda_3(scores_per_observer: list[list[float]]) -> dict[any, any]:
    """
    Formula from the original paper.

    L3 = n/(n-1) * L1
    """
    n_items = len(scores_per_observer[0])
    n_persons = len(scores_per_observer)

    L1 = guttman_lambda_1(scores_per_observer)['L1']

    L3 = n_items/(n_items-1) * L1

    return {'L3': L3}


def guttman_lambda_4(scores_per_observer: list[list[float]]) -> dict[any, any]:
    """
    Formula from the original paper.

    The formula for L4 requires that the test be scored as two halves.
    The respective variances of the two parts for the single trial are denoted by s_a^2 and s_b^2
    L4 = max 2(1-(s_a^2 + s_b^2)/s_t^2)

    Note that if there are 2k items (even number), there are C(2k,k)/2 different split-half partitions of the 2k items.
    If there are 2k+1 items (odd number), there are C(2k+1,k) different splits.
    E.g. if there are 10 questions in the questionnaire, there are C(10,5)/2 = 126 possible split-half partitions.
    https://real-statistics.com/reliability/internal-consistency-reliability/split-half-methodology/guttman-reliability/

    Here, we will split into equal first and second part.

    TODO: calculate C(2k,k)/2 instead of C(2k,k)
    """
    n_items = len(scores_per_observer[0])
    n_persons = len(scores_per_observer)

    # The variance over persons of the sum of the items
    sum_items = np.sum(scores_per_observer, axis=1)
    assert len(sum_items) == n_persons, 'Guttman lambda 4: lengths do not match, we should get a list of length n_persons'
    s_t2 = np.var(sum_items)

    def split_sublists(scores, partition):
        split = []
        for i in range(len(scores)):
            row = scores[i]
            # print(row)
            split.append([row[j] for j in partition])
        return split

    L4_list = []

    # Generate all combinations of size n/2
    from itertools import combinations
    items = [*range(n_items)]

    # FIXME this loop takes too long even for moderately small sizes of item list
    for i, comb in enumerate(combinations(items, n_items//2)):
        print(f"iter {i}")
        partition_a = list(comb)
        partition_b = list(set(items) - set(comb))

        scores_a = split_sublists(scores_per_observer, partition_a)
        scores_b = split_sublists(scores_per_observer, partition_b)

        s_a2 = np.sum(np.var(scores_a, axis=1))
        s_b2 = np.sum(np.var(scores_b, axis=1))

        L4_curr = 2*(1-(s_a2 + s_b2)/s_t2)
        L4_list.append(L4_curr)

    L4 = max(L4_list)

    return {'L4': L4}


def guttman_lambda_5(scores_per_observer: list[list[float]]) -> dict[any, any]:
    """
    Formula from the original paper.

    Let C_2j be the sum of the squares of the covariances of item j with the remaining n-1 items
    Let C_2 be the largest of the C_2j.
    L5 = L1 + 2*sqrt(C_2)/s_t^2
    """
    n_items = len(scores_per_observer[0])
    n_persons = len(scores_per_observer)

    # The variance over persons of the sum of the items
    sum_items = np.sum(scores_per_observer, axis=1)
    assert len(sum_items) == n_persons, 'Guttman lambda 5: lengths do not match, we should get a list of length n_persons'
    s_t2 = np.var(sum_items)

    cov = np.cov(np.array(scores_per_observer).T)
    assert cov.shape == (n_items, n_items), 'Guttman lambda 5: Covariance matrix shape is invalid, it should be of shape (n_items, n_items)'
    cov2 = np.power(cov, 2)

    C_2j = np.sum(cov2, axis=0) - np.diag(cov2)
    C_2 = max(C_2j)

    L1 = guttman_lambda_1(scores_per_observer)['L1']

    L5 = L1 + 2*np.sqrt(C_2) / s_t2

    return {'L5': L5}


def guttman_lambda_6(scores_per_observer: list[list[float]]) -> dict[any, any]:
    """
    Formula from the original paper.

    Let e_j2 be the variance of the errors of estimate of item j from its linear multiple regression on the remaining n-1 items.
    L6 = 1 - (sum[1..n] e_j2)/s_t^2

    https://www.cogn-iq.org/statistical-tools/guttman-lambda-6.html
    """
    n_items = len(scores_per_observer[0])
    n_persons = len(scores_per_observer)

    # The variance over persons of the sum of the items
    sum_items = np.sum(scores_per_observer, axis=1)
    assert len(sum_items) == n_persons, 'Guttman lambda 6: lengths do not match, we should get a list of length n_persons'
    s_t2 = np.var(sum_items)

    data = np.array(scores_per_observer)
    e_j2 = []

    from sklearn.linear_model import LinearRegression
    for j in range(n_items):
        X = np.delete(data, j, 1)
        y = data[:, j]

        model = LinearRegression().fit(X, y)

        error = y - model.predict(X)
        error_variance = np.var(error)
        e_j2.append(error_variance)

    L6 = 1 - np.sum(e_j2) / s_t2
    return {'L6': L6}


def icc(scores_per_observer: list[list[float]]) -> dict[any, any]:
    """
    Calculate intraclass correlation (ICC) score.

    Used this link for referent implementation: https://real-statistics.com/reliability/interrater-reliability/intraclass-correlation/
    """
    # Transform the list of lists into a DataFrame
    df = pd.DataFrame({f'P{i+1}': col for i, col in enumerate(scores_per_observer)}).reset_index()
    df = df.melt(id_vars=['index'], var_name='Rater', value_name='Score')
    df = df.rename(columns={'index': 'Question'})

    corr = pg.intraclass_corr(data=df, targets='Question', raters='Rater', ratings='Score').round(3)
    print(corr)
    return {'icc_table': corr}


def testing_scores(test_num):
    """
    Results manually compared with the following:
    https://langtest.jp/shiny/rel/

    Results are not identical with link, but similar:
    https://www.educative.io/answers/how-to-implement-cronbachs-alpha-for-reliability-in-python


    For lambda 6:
    Formula is different! Results my be incorrect.
    https://www.cogn-iq.org/statistical-tools/guttman-lambda-6.html
    """
    scores = [
        [
            [2, 3, 3, 3],
            [3, 3, 4, 4],
            [4, 4, 3, 4],
            [5, 4, 3, 4],
            [3, 4, 2, 4],
            [3, 3, 4, 3],
            [4, 3, 4, 4],
            [3, 3, 2, 2],
            [4, 5, 5, 5],
            [2, 2, 1, 2],
            [4, 3, 4, 3],
            [3, 4, 3, 3],
            [3, 4, 4, 3],
            [3, 4, 3, 4],
            [5, 5, 5, 4]
        ],
        [
            [1, 1, 1],
            [2, 1, 1],
            [2, 1, 2],
            [3, 2, 3],
            [1, 1, 1],
            [2, 3, 3],
            [3, 2, 3],
            [3, 3, 3],
            [2, 3, 2],
            [3, 3, 3]
        ],
    ]

    res_guttman_lambda_3 = [
        0.847,
        0.893,
    ]

    res_guttman_lambda_6 = [
        0.6354,
        0.5954
    ]

    return scores[test_num]
