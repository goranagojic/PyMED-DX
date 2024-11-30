#!/bin/bash

echo +x

export PROJECTHOME=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/..
export TOOLHOME="${PROJECTHOME}/pymeddx"
export PYTHONPATH="${TOOLHOME}":$PYTHONPATH


# make space for new, empty db file
if [ -f "${TOOLHOME}/database/survey.db" ]; then
    mv "${TOOLHOME}/database/survey.db" "${TOOLHOME}/database/survey.backup.db"
fi

read -p $'\nStep 1: Load observers.\nPress ENTER to continue.'
# load observers
python "${TOOLHOME}/main.py" load observers --filepath "${PROJECTHOME}/examples/observers.json"

read -p $'\nStep 2: Load images.\nPress ENTER to continue.'
# load images
python "${TOOLHOME}/main.py" load images -d "${PROJECTHOME}/examples/qtype1/images" -e .png -q 1 -m images.json

read -p $'\nStep 3: Generate questions in the database.\nPress ENTER to continue.'
# generate questions
python "${TOOLHOME}/main.py" generate questions -q 1

read -p $'\nStep 4a: Generate regular questionnaires in database.\nPress ENTER to continue.'
# generate regular questionnaires
python "${TOOLHOME}/main.py" generate questionnaire --qtype 1 --qsubtype regular --kquestions 8

read -p $'\nStep 4b: Generate control questionnaires in database.\nPress ENTER to continue.'
# generate control questionnaires
python "${TOOLHOME}/main.py" generate questionnaire --qtype 1 --qsubtype control --nquestionnaire 3 --kquestions 8

read -p $'\nStep 5a: Export regular questionnaires to html.\nPress ENTER to continue.'
# export export regular
python "${TOOLHOME}/main.py" export --directory "${PROJECTHOME}/examples/qtype1/questionnaires" --format html --qtype 1 --qsubtype regular

read -p $'\nStep 5b: Export control questionnaires to html.\nPress ENTER to continue.'
# export control
python "${TOOLHOME}/main.py" export --directory "${PROJECTHOME}/examples/qtype1/questionnaires" --format html --qtype 1 --qsubtype control

# copy prepared database
#cp "${PROJECTHOME}/examples/qtype1/survey.db" "${TOOLHOME}/database/"

read -p $'\nStep 6: Load responses to the datapase.\nPress ENTER to continue.'
# import results
python "${TOOLHOME}/main.py" load responses --directory "${PROJECTHOME}/examples/qtype1/responses" --qtype 1

read -p $'\nStep 7: Analyze the data that was loaded.\nPress ENTER to continue.'
# calculate diagnostic value
python "${TOOLHOME}/main.py" analyze metrics --qtype 1 --mtype dv

read -p $'\nStep 8: Run inter observer statistics.\nPress ENTER to continue.'
# run stats - inter observer
python "${TOOLHOME}/main.py" analyze stats --qtype 1 --stype inter

read -p $'\nStep 9: Run intra observer statistics.\nPress ENTER to continue.'
# run stats - intra observer
python "${TOOLHOME}/main.py" analyze stats --qtype 1 --stype intra -o 1

read -p $'\nStep 10: Export boxplot based on results.\nPress ENTER to continue.'
# run visualizations - boxplot
python "${TOOLHOME}/main.py" analyze visual --qtype 1 --vtype boxplot --directory "${PROJECTHOME}/examples/qtype1/plots"

read -p $'\nStep 11: Export histogram based on results.\nPress ENTER to continue.'
# run visualizations - histograms
python "${TOOLHOME}/main.py" analyze visual --qtype 1 --vtype histogram --directory "${PROJECTHOME}/examples/qtype1/plots"