import itertools

import numpy as np
import pandas as pd
from model.image import Image
from model.response import ResponseType2
from utils.database import engine, session
from utils.logger import logger


def copeland_score():
    logger.info(f"Loading repeated measurements for intra-observer agreement evaluation.")

    # get all images that are compared
    # those are images that have group id set (just reference image have group id set to none)
    stmt = session.query(
        Image.id
    ).where(
        Image.group_id is not None
    ).statement

    df = pd.read_sql(stmt, engine)
    df = df.rename(columns={'id': 'candidate'})
    df['copeland_score'] = 0

    stmt = session.query(
        Image.id,
        ResponseType2.img2_id,
        ResponseType2.choice,
        Image.group_id,
        ResponseType2.id,
        Image.model,
        Image.dataset,
    ).join(
        ResponseType2, Image.id == ResponseType2.img1_id
    ).where(
        Image.group_id is not None
    ).order_by(
        Image.group_id,
        Image.id,
        ResponseType2.img2_id
    ).statement

    df_scores = pd.read_sql(stmt, engine)
    df_scores = df_scores.rename(columns={'id_1': 'survey_id', 'id': 'img1_id'})

    rankings = pd.DataFrame(columns=["candidate", "copeland_score"])
    rankings = rankings.astype({
        "candidate": np.int16,
        "copeland_score": np.float16,
    })

    # for candidate in df['candidate']:
    for group in df_scores.groupby('group_id'):
        img1 = group[1]['img1_id'].to_list()
        img2 = group[1]['img2_id'].to_list()

        images = img1 + img2
        candidates = np.unique(images)

        ranking = pd.DataFrame({
            "candidate": candidates,
            "copeland_score": np.zeros(len(candidates), dtype=np.float16)
        })
        ranking = ranking.set_index(ranking["candidate"])

        # create empty pairwise comparison table
        candidate_pairs = [i for i in itertools.combinations(iterable=candidates, r=2)]
        xs = [x for x, _ in candidate_pairs]
        ys = [y for _, y in candidate_pairs]
        pairwise_comparison = pd.DataFrame({
            "candidate1": xs,
            "candidate2": ys,
            "candidate1_wins": np.zeros(len(xs), dtype=np.int16),
            "candidate2_wins": np.zeros(len(ys), dtype=np.int16)
        })

        # populate pairwise table
        for c1, c2 in candidate_pairs:
            logger.info(f"Calculating Copeland score for image pair {c1} and {c2}.")

            # extract from the group all questions where candidate1 and candidate2 compete
            # as img1 and/or img2

            pairs = group[1][
                np.logical_or(
                    np.logical_and(group[1]["img1_id"] == c1, group[1]["img2_id"] == c2),
                    np.logical_and(group[1]["img1_id"] == c2, group[1]["img2_id"] == c1)
                )
            ]
            c1_wins = len(pairs[pairs["choice"] == c1])
            c2_wins = len(pairs[pairs["choice"] == c2])

            row_position = np.logical_and(
                    pairwise_comparison["candidate1"] == c1,
                    pairwise_comparison["candidate2"] == c2
                )
            # https://stackoverflow.com/questions/52173161/getting-a-list-of-indices-where-pandas-boolean-series-is-true
            row_position = row_position[row_position].index.values[0]

            # write win count for candidate 1
            pairwise_comparison.at[
                row_position, 'candidate1_wins'
            ] = c1_wins

            # write win count for candidate 2
            pairwise_comparison.at[
                row_position, 'candidate1_wins'
            ] = c2_wins

            # populate table with copeland ranking score
            if c1_wins > c2_wins:
                ranking.at[c1, "copeland_score"] += 1
            elif c2_wins > c1_wins:
                ranking.at[c2, "copeland_score"] += 1
            else:
                ranking.at[c1, "copeland_score"] += 0.5
                ranking.at[c2, "copeland_score"] += 0.5
                # TODO what now?!
                pass

        # if some image is selected by none of the observers, then it will appear in ranking with score
        # 0 and no other cells populated (such as network name etc.)
        # luckily, there are just a few entries like this so it is easy to manually correct this once ranking file is
        # produced
        rankings = pd.concat([rankings, ranking], ignore_index=True)

    df = df.merge(rankings, on='candidate', how='left', suffixes=('', '_from_df'))
    df['copeland_score'] = df['copeland_score_from_df'].combine_first(df['copeland_score'])
    df.drop(columns=['copeland_score_from_df'], inplace=True)
    df = df.rename(columns={'candidate': 'img_id'})

    return df
