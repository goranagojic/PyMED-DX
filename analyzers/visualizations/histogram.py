import pandas as pd
from typing import Optional, Union, List
from pathlib import Path

import plotly.express as px

from utils.logger import logger
from utils.database import session, engine
from model.response import ResponseType1
from model.question import QuestionType1
from model.image import Image
from model.copeland_score import CopelandScore

from analyzers.metrics.diagnostic_score import DiagnosticScore


def histogram(
    stmt: str,
    by: Union[List[str], str],
    column: Union[List[str], str],
    filename: str,
    output_dir: Optional[Union[str, Path]] = None,
    **kwargs
):
    """
        Generates and displays or saves a histogram plot based on data retrieved from a database query.

        :param stmt: The SQL statement as a string, used to query data from the database.
        :param by: Column(s) to group data by for separate histograms for each unique group value. Can be a single
                   string or a list of strings.
        :param column: Column(s) to plot in the histogram. Assumes a single value within `column`.
        :param filename: A string identifier for the histogram type, used in naming the output file if saved.
        :param output_dir: Optional. Path to save the generated histogram as an HTML file. If `None`, the plot is
                           displayed directly instead.
        :param kwargs: Additional keyword arguments for customizing the plot:
            - title (str): Title for the histogram.
            - xlabel (str): Label for the x-axis.
            - ylabel (str): Label for the y-axis.
            - xtick_labels (list): Custom labels for the x-axis ticks.
            - ytick_labels (list): Custom labels for the y-axis ticks.

        :return: None.
        """

    # Load data from database
    data = pd.read_sql(stmt, engine)

    # Plot histogram for all values in `column`
    if by is None:
        fig = px.histogram(
            data_frame=data,
            x=column,  # Assuming `column` contains a single value; adjust as needed
            nbins=len(range(-6, 7)),  # Number of bins corresponding to the range
            title=kwargs.get('title', f'Histogram of {column[0]}'),
            labels={column[0]: kwargs.get('xlabel', column[0]), column[1]: kwargs.get('ylabel', column[1])}
        )
    else:
        fig = px.histogram(
            data_frame=data,
            x=column,  # Assuming `column` contains a single value; adjust as needed
            nbins=len(range(-6, 7)),  # Number of bins corresponding to the range
            title=kwargs.get('title', f'Histogram of {column[0]}'),
            labels={column[0]: kwargs.get('xlabel', column[0]), column[1]: kwargs.get('ylabel', column[1])},
            facet_col=by
        )

    # Set x-axis and y-axis labels
    fig.update_xaxes(title_text=kwargs.get('xlabel', column[0]))
    fig.update_yaxes(title_text=kwargs.get('ylabel', 'Frequency'))

    # Optionally, add custom x-tick and y-tick labels
    xtick_labels = kwargs.get('xtick_labels')
    ytick_labels = kwargs.get('ytick_labels')
    if xtick_labels:
        fig.update_xaxes(tickvals=list(range(len(xtick_labels))), ticktext=xtick_labels)
    if ytick_labels:
        fig.update_yaxes(tickvals=list(range(len(ytick_labels))), ticktext=ytick_labels)

    # Display or save the histogram
    if output_dir is None:
        fig.show()
    else:
        output_path = Path(output_dir) / f"histogram-{filename}.html"
        fig.write_html(output_path)
        logger.info(f"Exported histogram to the path '{output_path}'.")


def histogram_observers(qtype, output_dir, **kwargs):
    query_map = {
        1: session.query(ResponseType1.id, ResponseType1.observer_id, DiagnosticScore.value)
            .join(DiagnosticScore, DiagnosticScore.response_id == ResponseType1.id)
            .statement
        # TODO Add a maping for type 2
    }

    # Fetch the query based on qtype or raise error if unsupported
    stmt = query_map.get(qtype)
    if stmt is None:
        raise NotImplementedError(f"Questionnaire type {qtype} is not supported")

    histogram(
        stmt=stmt,
        by='observer_id',
        column='value',
        filename='observers',
        output_dir=output_dir,
        **kwargs
    )


def histogram_datasets(qtype, output_dir, **kwargs):

    query_map = {
        1: session.query(ResponseType1.id, QuestionType1.id, Image.id, Image.dataset, DiagnosticScore.value)
            .join(DiagnosticScore, DiagnosticScore.response_id == ResponseType1.id)
            .join(QuestionType1, ResponseType1.question_id == QuestionType1.id)
            .join(Image, QuestionType1.image_id == Image.id)
            .statement,
        2: session.query(CopelandScore.id, CopelandScore.value, Image.model, Image.dataset)
            .join(Image, CopelandScore.image_id == Image.id)
            .where(Image.model != "")
            .statement
    }

    # Fetch the query based on qtype or raise error if unsupported
    stmt = query_map.get(qtype)
    if stmt is None:
        raise NotImplementedError(f"Questionnaire type {qtype} is not supported")

    if qtype == 1:
        by = 'dataset'
    else:
        by = 'dataset'

    histogram(
        stmt=stmt,
        by=by,
        column='value',
        filename='datasets',
        output_dir=output_dir,
        **kwargs
    )


def histogram_models(qtype, output_dir, **kwargs):
    query_map = {
        1: None,
        2: session.query(CopelandScore.id, CopelandScore.value, Image.model, Image.dataset)
            .join(Image, CopelandScore.image_id == Image.id)
            .where(Image.model != "")
            .statement
    }

    # Fetch the query based on qtype or raise error if unsupported
    stmt = query_map.get(qtype)
    if stmt is None:
        raise NotImplementedError(f"Questionnaire type {qtype} is not supported")

    histogram(
        stmt=stmt,
        by='model',
        column='value',
        filename='models',
        output_dir=output_dir,
        **kwargs
    )