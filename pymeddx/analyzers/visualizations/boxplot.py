import pandas as pd
import plotly.express as px

from typing import Optional, Union, List
from pathlib import Path

from utils.logger import logger
from utils.database import session, engine
from model.response import ResponseType1
from model.question import QuestionType1
from model.image import Image
from model.copeland_score import CopelandScores, CopelandScore

from analyzers.metrics.diagnostic_score import DiagnosticScore


def boxplot_observers(qtype, output_dir, **kwargs):
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

    # Load data from database
    data = pd.read_sql(stmt, engine)
    if qtype == 2:
        data.rename(columns={'avg_1': 'value'}, inplace=True)

    boxplot(
        data=data,
        by='observer_id',
        column='value',
        type='observers',
        output_dir=output_dir,
        **kwargs
    )


def boxplot_datasets(qtype, output_dir, **kwargs):
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

    # Load data from database
    data = pd.read_sql(stmt, engine)

    if qtype == 2:
        data.rename(columns={'avg_1': 'value'}, inplace=True)

    boxplot(
        data=data,
        by=['model', 'dataset'],
        column='value',
        type="datasets",
        output_dir=output_dir,
        **kwargs
    )


def boxplot_models(qtype, output_dir, **kwargs):
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

    # Load data from database
    data = pd.read_sql(stmt, engine)

    if qtype == 1:
        logger.info(f"Boxplot model diagrams are unsupported for QType {qtype}.")
        return
    elif qtype == 2:
        data.rename(columns={'avg_1': 'value'}, inplace=True)

    boxplot(
        data=data,
        by='model',
        column='value',
        type="models",
        output_dir=output_dir,
        **kwargs
    )


def boxplot(
        data: pd.DataFrame,
        by: Union[List[str], str],
        column: Union[List[str], str],
        type: str,
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
):
    """
    Create a boxplot for diagnostic scores across different observers.

    :param qtype: Integer specifying the type of response to query (e.g., 1 for ResponseType1).
    :param output_dir: Path to the directory where the plot will be saved. If None, plot will be displayed.
    :raises NotImplementedError: If qtype is unsupported.
    """

    # Prepare the box plot
    if isinstance(by, str):
        by = [by]
    if isinstance(column, str):
        column = [column]

    # Create box plot using Plotly Express
    fig = px.box(
        data_frame=data,
        x=by[0] if by else None,
        y=column[0],  # Assuming `column` contains a single value
        title=kwargs.get('title', f'Box Plot of {column[0]}'),
        labels={by[0]: kwargs.get('xlabel', by[0]), column[0]: kwargs.get('ylabel', column[0])}
    )

    # Set x-axis and y-axis labels
    fig.update_xaxes(title_text=kwargs.get('xlabel', by[0] if by else ''))
    fig.update_yaxes(title_text=kwargs.get('ylabel', column[0]))

    # Optionally, add custom x-tick and y-tick labels
    xtick_labels = kwargs.get('xtick_labels')
    ytick_labels = kwargs.get('ytick_labels')
    if xtick_labels:
        fig.update_xaxes(tickvals=list(range(len(xtick_labels))), ticktext=xtick_labels)
    if ytick_labels:
        fig.update_yaxes(tickvals=list(range(len(ytick_labels))), ticktext=ytick_labels)

    # Display or save the box plot
    if output_dir is None:
        fig.show()
    else:
        output_path = Path(output_dir) / f"boxplot-{type}.html"
        fig.write_html(output_path)
        logger.info(f"Exported boxplot to the path '{output_path}'.")


def _export_data(boxplot, out, xtickmapping=None, ytickmapping=None):
    """
    Serialize boxplot data for external use.

    The function generate files with quartile data, x and y ticks data.
    Quartile data file can have data on multiple boxplots separated in different rows.
    Quartile file format is:
    <ordinal number> <lower wisker value> <lower box value> <median value> <upper box value> <upper wisker value>

    Both x and y tick data is saved into a same file. Format of that file is:
    xticklabels: [<xlabel1>, <xlabel2>, ..., <xlabelN>]
    yticklabels: [<ylabel1>, <ylabel2>, ..., <ylabelN>]
    Both xticklabels and yticklabels are automatically generated by reading appropriate matplotlib fields corresponding
    to a boxplot. Tick labels can be mapped to different values using xtickmapping and ytickmapping parameters.
    This can be useful to generate more human-friendly ticks that later can be consumed in some automatic pipeline.

    :param boxplot: TODO
    :param out: TODO
    :param xtickmapping: TODO
    :param ytickmapping: TODO
    :return: None
    """

    xticklabels = [xtick.label.get_text() for xtick in boxplot.ax.axes.xaxis.majorTicks]
    yticklabels = [ytick.label.get_text() for ytick in boxplot.ax.axes.yaxis.majorTicks]

    quartiles = boxplot[1]

    with open(out, "w") as f:
        for i in range(0, len(quartiles["boxes"])):
            # for every box there are two caps meaning that for each boxplot two
            # consecutive caps are needed (boxes[0] matches caps[0] and caps[1])
            lower_whisker_bound = quartiles["caps"][2 * i].get_ydata()[0]
            lower_box_bound = quartiles["boxes"][i].get_ydata()[0]
            median = quartiles["medians"][i].get_ydata()[0]
            upper_box_bound = quartiles["boxes"][i].get_ydata()[2]
            upper_whisker_bound = quartiles["caps"][2 * i + 1].get_ydata()[1]
            f.write(f"{i} {lower_whisker_bound} {lower_box_bound} {median} {upper_box_bound} {upper_whisker_bound}\n")

    if xticklabels is not None or yticklabels is not None:
        out_dir, out_filename = out.parent, out.stem
        with open(out_dir / f"{out_filename}-ticklabels.dat", "w") as fticks:
            if xtickmapping is not None:
                mappings = [xtickmapping[xtl] for xtl in xticklabels if xtl in xtickmapping]
                fticks.write(f"xticklabels: {mappings}\n")
            else:
                fticks.write(f"xticklabels: {xticklabels}\n")
            if ytickmapping is not None:
                mappings = [ytickmapping[ytl] for ytl in yticklabels if ytl in ytickmapping]
                fticks.write(f"yticklabels: {mappings}\n")
            else:
                fticks.write(f"yticklabels: {yticklabels}\n")