#!/bin/bash

echo +x

export PROJECTHOME="/home/gorana/Projects/PyMED-DX"
export TOOLHOME="${PROJECTHOME}/pymeddx"
export PYTHONPATH="${TOOLHOME}":$PYTHONPATH


# make space for new, empty db file
if [ -f "${TOOLHOME}/database/survey.db" ]; then
    mv "${TOOLHOME}/database/survey.db" "${TOOLHOME}/database/survey.backup.db"
fi


# load observers
python "${TOOLHOME}/main.py" load observers --filepath "${PROJECTHOME}/examples/observers.json"

# load images
python "${TOOLHOME}/main.py" load images -d "${PROJECTHOME}/examples/qtype1/images" -e .png -q 1 -m images.json

# generate questions
python "${TOOLHOME}/main.py" generate questions -q 1

# generate regular questionnaires
python "${TOOLHOME}/main.py" generate questionnaire --qtype 1 --qsubtype regular --kquestions 8

# generate control questionnaires
python "${TOOLHOME}/main.py" generate questionnaire --qtype 1 --qsubtype control --nquestionnaire 3 --kquestions 8

# export export regular
python "${TOOLHOME}/main.py" export --directory "${PROJECTHOME}/examples/qtype1/questionnaires" --format html --qtype 1 --qsubtype regular

# export control
python "${TOOLHOME}/main.py" export --directory "${PROJECTHOME}/examples/qtype1/questionnaires" --format html --qtype 1 --qsubtype control