import json

import click

import analyzers.visualizations.boxplot as bplot
import analyzers.visualizations.histogram as hist
from analyzers.metrics.copeland_score import copeland_score
from analyzers.metrics.diagnostic_score import (DiagnosticScore,
                                                DiagnosticScores)
from generators.surveygeneratortype1 import SurveyGenerator as SGen1
from generators.surveygeneratortype2 import SurveyGenerator as SGen2
from model.copeland_score import CopelandScore, CopelandScores
from model.observer import Observers
from model.question import *
from model.response import Responses
from utils.database import engine, Base

Base.metadata.create_all(engine)


@click.group()
def pymeddx():
    """
    A Python tool for diagnostic value evaluation in medical images.
    It accelerates and simplifies subjective assessment studies by
    streamlining both questionnaire creation and response analysis.

    Start by loading observers and images to the database. After that,
    generate questions and questionnaires. When the questionnaires
    are done, load the responses to the database, aggregate and
    analyze them.
    """
    pass


@pymeddx.group(short_help="Load data to the database.")
def load():
    """
    Depending on the given command, loads data about images, observers
    or responses to the database.
    """
    pass


@load.command(short_help="Load all observers from the filepath to the database.")
@click.option('-f', '--filepath', type=click.Path(exists=True), required=False,
              help="Path to .txt file with all observers.")
def observers(filepath):
    """
    Load all observers from the filepath to the database.
    """
    with open(filepath, 'r') as file:
        data = json.load(file)

    # Iterate over each dictionary in the list
    for entry in data:
        name, token = entry['name'], entry['token']
        Observers.insert(name=name, access_token=token)
        logger.info(f"User '{name}' added to the database.")


@load.command(short_help="Load image data to the database.")
@click.option('-q', '--qtype', type=click.Choice(["1", "2"]), required=True,
              help="Questionnaire type. Currently supported values are 1 and 2.")
@click.option('-d', '--directory', type=click.Path(exists=True), required=True,
              help="Path to the directory containing the images. Immediate parent directory will be considered as a "
                   "dataset name.")
@click.option('-e', '--extension', multiple=True, required=True,
              help="A list image extensions to be loaded from the directory. An extension is a string preceded by a dot"
                   " sign (e.g. '.png').")
@click.option('-m', '--metadata-file', type=str, required=False,
              help="An image metadata filename. If not specified, metadata file must be named after the innermost "
                   "directory of the `directory` option.")
def images(qtype, directory, extension, metadata_file):
    """
    Load image data to the database.
    """
    Images.load_images(
        qtype=qtype,
        directory=directory,
        extensions=list(extension),
        metadata_file=metadata_file
    )


@load.command(short_help="Load questionnaire responses to the database.")
@click.option('-d', '--directory', type=click.Path(exists=True), required=True,
              help="Path to the directory containing the responses.")
@click.option('-q', '--qtype', type=click.Choice(["1", "2"]), required=True,
              help="Questionnaire type. Currently supported values are 1 and 2.")
def responses(directory, qtype):
    """
    Load questionnaire responses to the database.

    :param directory: Path to a directory that contains subdirectories. Each subdirectory should represent an
    individual observer and contain their completed questionnaire responses downloaded upon questionnaire completion.
    Each subdirectory should be named after id of an observer whose responses it contains.
    """
    observer_ids = [observer.id for observer in Observers.get_observers()]

    directory = Path(directory)
    qtype = int(qtype)

    if not directory.is_dir():
        raise ValueError(f"The specified path '{directory}' is not a valid directory.")

    for observer_dir in directory.iterdir():
        # Check if it is a directory and if the observer ID is numeric
        if observer_dir.is_dir() and observer_dir.name.isdigit():
            observer_dir_name = int(observer_dir.name)
            if observer_dir_name in observer_ids:
                logger.info(f"Loading responses for user {observer_dir_name} from '{observer_dir}'.")
                for response_file in observer_dir.glob("*.html"):
                    if qtype == 1:
                        Responses.load_from_file(response_file, observer_id=observer_dir_name, qtype=1)
                    else:
                        Responses.load_from_file(response_file, observer_id=observer_dir_name, qtype=2)
                # Placeholder for loading responses into the database
                # load_responses(observer_dir)
            else:
                logger.warning(f"Skipping. Directory '{observer_dir.name}' does not correspond to any existing database "
                               f"users. Responses from this directory will not be loaded.")
        else:
            logger.info(f"Skipping. Invalid response directory naming scheme ('{observer_dir.name}'). The name of the "
                        f"file should be the same as an ID of the observer who generated responses.")


@pymeddx.group(short_help="Generate questions or whole questionnaires.")
def generate():
    """
    Generate questions or questionnaires of chosen type and store them
    in the database.
    """
    pass


@generate.command(short_help="Generate questions.")
@click.option('-q', '--qtype', type=int, multiple=True, required=True,
              help="Type of questionnaire the questions are generated for. Currently supported values are 1 and 2.")
@click.option('-r', '--repeat', type=int, required=False,
              help="Only applies to type 2 questionnaires. This option is used to specify how many times will each "
                   "image from the image group repeat when generating the questions.", default=5)
def questions(qtype, repeat):
    """
    Generate questions depending on the chosen questionnaire type. If
    generating type 2 questionnaire was chosen, you can specify how many
    times an image from an image group will repeat.
    """
    print(f"Generating questions.")
    Questions.generate(question_types=list(qtype), n_repeat=repeat)


@generate.command(short_help="Generate questionnaires.")
@click.option('-q', '--qtype', type=int, required=True,
              help="Questionnaire type. Currently supported values are 1 and 2.")
@click.option('-s', '--qsubtype', type=click.Choice(['regular', 'control'], case_sensitive=False), required=False,
              help="Questionnaire subtype. Questionnaires of type 1 can be regular and control, but questionnaires"
                   "of type 2 can only be regular. Currently  supported values are `regular` and `control`.", default='regular')
@click.option('-n', '--nquestionnaire', type=int, required=False,
              help="Number of questionnaires to be generated. If not specified, questionnaires will be generated"
                   " until all questions have been used up.")
@click.option('-k', '--kquestions', type=int, required=False,
              help="Number of questions per questionnaire. Used only in questionnaires type 1.", default=20)
def questionnaire(qtype, qsubtype, nquestionnaire, kquestions):
    """
    Generate questionnaires of specified type from the database questions.
    """
    logger.info("Starting questionnaire generation...")
    if qtype == 1:
        survey_gen = SGen1(survey_type=qsubtype, questions_per_survey=kquestions)
        survey_gen.generate_all(n_surveys=nquestionnaire)
    elif qtype == 2:
        survey_gen = SGen2()
        survey_gen.generate_all(n_surveys=nquestionnaire)
    else:
        logger.error(f"Unsupported questionnaire type {qtype}.")
        raise ValueError(f"Unsupported questionnaire type {qtype}.")


@pymeddx.command(short_help="Export questionnaires from database.")
@click.option('-d', '--directory', type=click.Path(exists=True), required=True,
              help="Path to directory where the data will be exported.")
@click.option('-f', '--format', type=click.Choice(['json', 'html']), required=False,
              help="Format of output data. Currently  supported values are `json` and `html`.", default="html")
@click.option('-q', '--qtype', type=int, required=True,
              help="Questionnaire type. Currently supported values are 1 and 2.")
@click.option('-s', '--qsubtype', type=click.Choice(['regular', 'control'], case_sensitive=False), required=False,
              help="Questionnaire subtype. Questionnaires of type 1 can be regular and control, but questionnaires"
                   "of type 2 can only be regular. Currently  supported values are `regular` and `control`.", default='regular')
def export(directory, format, qtype, qsubtype):
    """
    Exports questionnaire data to the specified directory. Currently
    supports questionnaire export in json and html formats.
    """
    logger.info("Starting questionnaire export...")
    if qtype == 1:
        SGen1.export_surveys(directory, export_type=format, survey_type=qsubtype)
    elif qtype == 2:
        # there are no type 2 control surveys
        SGen2.export_surveys(directory, export_type=format, survey_type='regular')
    else:
        logger.error(f"Unsupported questionnaire type {qtype}.")
        raise ValueError(f"Unsupported questionnaire type {qtype}.")


@pymeddx.group(short_help="Analyze the loaded data.")
def analyze():
    """
    Calculate all the necessary metrics using the loaded responses.
    After calculating the metrics, run the statistical tests for
    more insights into the loaded responses.
    """
    pass


@analyze.command(short_help="Calculate all the metrics.")
@click.option('-q', '--qtype', type=int, required=True,
              help="Questionnaire type. Currently supported values are 1 and 2.")
@click.option('-m', '--mtype', type=click.Choice(['dv', 'cs'], case_sensitive=False), required=True,
              help="Type of metric calculation to be ran. Currently supported values are 'dv' for 'diagnostic-value'"
                   "and 'cs' for 'copeland-score'.")
def metrics(qtype, mtype):
    """
    Calculate the metrics of the loaded responses using one of the available
    methods. The support values are 'dv' for diagnostic-value and 'cs' for
    'copeland-score'.
    """
    if qtype == 1:
        if mtype == 'dv':
            responses = Responses.get_all_responses(type=qtype)
            if len(responses) == 0:
                logger.error("Cannot calculate the diagnostic score because there are no responses in the database. "
                             "Please import responses first, then try calculating the diagnostic score again.")
                return
            for r in responses:
                if r.diagnostic_score is None or len(r.diagnostic_score) == 0:
                    diagnostic_score = DiagnosticScore(r)
                    DiagnosticScores.insert(diagnostic_score)
                    logger.debug(f"Inserted diagnostic score to the database: ({r.id}, {diagnostic_score})")
                logger.info(f"Diagnostic value calculation done!")
        else:
            logger.error(f"Unsupported metric type '{mtype}' for qtype {qtype}. Consider using a different "
                         f"questionnaire type.")
            return
    elif qtype == 2:
        if mtype == 'cs':
            cscores_df = copeland_score()
            logger.info(f"Copeland score calculation done!")
            for index, row in cscores_df.iterrows():
                img_id = row['img_id']
                cscore = row['copeland_score']
                cs = CopelandScore(img_id=img_id, value=cscore)
                CopelandScores.insert(cs)
                logger.debug(f"Inserted copeland score to the database: ({int(img_id)}, {cscore})")
            model_scores = CopelandScores.get_score_group_by_models()
            if len(model_scores) != 0:
                logger.info(f"\nList of models and associated Copeland scores sorted in descending order.")
                logger.info(f"The presented scores are averaged across images produced by the same model.")
                for i, (model, score) in enumerate(model_scores):
                    logger.info(f"[{i}] {model}: {score}")

                logger.info(f"\nNext, you can run commands to visualize Copeland scores.")
            else:
                logger.error(f"Copeland scores per models could not be printed because the resulting list is empty. "
                             f"Check if Copeland scores has been calculated or if images have assigned model names.")
        else:
            logger.error(f"Unsupported metric type '{mtype}' for qtype {qtype}.")
            raise ValueError(f"Unsupported metric type '{mtype}' for qtype {qtype}.")
    else:
        logger.error(f"Unsupported qtype type '{qtype}'. Currently supported types are ['1', '2'].")
        return


@analyze.command(short_help="Run statistical tests.")
@click.option('-q', '--qtype', type=int, required=True,
              help="Questionnaire type. Currently supported values are 1 and 2.")
@click.option('-s', '--stype', type=click.Choice(['inter', 'intra']), required=True,
              help='Run inter-observer or intra-observer statistical analyzes.')
@click.option('-o', '--oid', type=int, multiple=True,
              help="Identifier of the observer to include in calculation. Currently used only to select observers for "
                   "intra-observer agreement calculations.")
def stats(qtype, stype, oid):
    """
    Run statistical tests on the loaded response data. Calculates the
    cohens-kappa and the krippendorff-alpha for inter-observer agreement and Guttman's lambda, Cronbach's alpha and ICC
    for intra-observer agreement.
    """

    responses = Responses.get_all_responses(type=qtype)
    if len(responses) == 0:
        logger.error(f"Cannot calculate the diagnostic score because there are no responses of type {qtype} in the "
                     f"database. Please import responses first, then try calculating the diagnostic score again.")
        return

    if stype == 'inter' and oid is not None:
        logger.warning("The 'oid' parameter is not applicable when 'stype' is set to 'inter'. Ignoring 'oid'.")

    if stype.lower() == 'inter':
        from analyzers.statistics.interobserver import stats_wrapper

        logger.info(f"Calculating Cohen's kappa...")
        r = stats_wrapper(qtype=qtype, fn='cohens-kappa')
        logger.info(f"Pairwise observer agreement:\n{r['pairwise_observers']}")
        logger.info('')

        logger.info(f"Calculating Krippendorff alpha...")
        r = stats_wrapper(qtype=qtype, fn='krippendorff-alpha', pairwise=True)

        logger.info(f"Inter-observer agreement of all observers: {r['all_observers']}")
        if 'pairwise_observers' in r:
            logger.info(f"Pairwise observer agreement:\n{r['pairwise_observers']}")
    elif stype.lower() == 'intra':
        from analyzers.statistics.intraobserver import stats_wrapper

        logger.info('(Guttman) Check that the inequality holds: 0 < L1 < L3 <= L2')
        logger.info('(Cronbach) Check that the equality holds: Cronbach Alpha = Guttmans L3')

        stats_wrapper(qtype=qtype, fn='actionbars-alpha', observer_ids=oid)
        stats_wrapper(qtype=qtype, fn='icc', observer_ids=oid)
        stats_wrapper(qtype=qtype, fn='guttmans-lambda-1', observer_ids=oid)
        stats_wrapper(qtype=qtype, fn='guttmans-lambda-2', observer_ids=oid)
        stats_wrapper(qtype=qtype, fn='guttmans-lambda-3', observer_ids=oid)
        stats_wrapper(qtype=qtype, fn='guttmans-lambda-4', observer_ids=oid)
        stats_wrapper(qtype=qtype, fn='guttmans-lambda-5', observer_ids=oid)
        stats_wrapper(qtype=qtype, fn='guttmans-lambda-6', observer_ids=oid)
    else:
        logger.error(f"Unsupported statistical analysis type.")


@analyze.command(short_help="Draw boxplot or histogram.")
@click.option('-q', '--qtype', type=int, required=True,
              help="Questionnaire type. Currently supported values are 1 and 2.")
@click.option('-d', '--directory', type=click.Path(exists=True), required=True,
              help="Path to the directory where to save the visuals.")
@click.option('-v', '--vtype', type=click.Choice(['boxplot', 'histogram']), required=True,
              help="Questionnaire type. Currently supported values are 1 and 2.")
def visual(qtype, directory, vtype):
    """
    Draws boxplot or histogram of the calculated data.
    """
    responses = Responses.get_all_responses(type=qtype)
    if len(responses) == 0:
        logger.error(f"Cannot calculate the diagnostic score because there are no responses of type {qtype} in the "
                     f"database. Please import responses first, then try calculating the diagnostic score again.")
        return

    if qtype == 1:
        logger.info(f"Plotting boxplots for diagnostic score.")
        # plots group by model are not supported for QType1 at the moment
        if vtype == 'boxplot':
            bplot.boxplot_observers(
                qtype=qtype,
                title="Diagnostic Score per Observers",
                xlabel="Observers",
                ylabel="Diagnostic score",
                output_dir=directory
            )
            # datasets boxplot
            bplot.boxplot_datasets(
                qtype=qtype,
                title="Diagnostic Score per Datasets",
                xlabel="Datasets",
                xtick_labels=['Test'],
                ylabel="Diagnostic score",
                output_dir=directory
            )
        elif vtype == 'histogram':
            logger.info(f"Plotting histograms for diagnostic score.")
            hist.histogram_observers(
                qtype=qtype,
                title="Diagnostic Score Distribution",
                xlabel="Diagnostic Score",
                ylabel="Count",
                output_dir=directory
            )
            hist.histogram_datasets(
                qtype=qtype,
                title="Diagnostic Score Distribution",
                xlabel="Diagnostic Score",
                ylabel="Count",
                output_dir=directory
            )
    elif qtype == 2:
        if vtype == 'boxplot':
            logger.info(f"Plotting boxplot for Copeland score.")
            bplot.boxplot_models(
                qtype=qtype,
                title="Copeland score per Models",
                xlabel="Models",
                ylabel="Copeland score",
                output_dir=directory
            )
        elif vtype == 'histogram':
            logger.info(f"Plotting histograms for Copeland score.")
            hist.histogram_models(
                qtype=qtype,
                title="Copeland Score Distribution",
                xlabel="Copeland Score",
                ylabel="Value",
                output_dir=directory
            )


if __name__ == '__main__':
    pymeddx()
