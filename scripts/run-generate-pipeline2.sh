#!/bin/bash

export PROJECTHOME=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/..
export TOOLHOME="${PROJECTHOME}/pymeddx"
export PYTHONPATH="${TOOLHOME}":$PYTHONPATH


# make space for new, empty db file
if [ -f "${TOOLHOME}/database/survey.db" ]; then
    mv "${TOOLHOME}/database/survey.db" "${TOOLHOME}/database/survey.backup.db"
fi

# load observers
python "${TOOLHOME}/main.py" load observers --filepath "${PROJECTHOME}/examples/observers.json"

# load images
## reference images
python "${TOOLHOME}/main.py" load images -d "${PROJECTHOME}/examples/qtype2/images/originals" -e .png -q 2 -m originals.json

## outputs of ml-models
python "${TOOLHOME}/main.py" load images -d "${PROJECTHOME}/examples/qtype2/images/ml-outputs" -e .png -q 2 -m ml-outputs.json

# generate questions
python "${TOOLHOME}/main.py" generate questions -q 2

# generate questionnaires
python "${TOOLHOME}/main.py" generate questionnaire --qtype 2 --qsubtype regular

# export export 
python "${TOOLHOME}/main.py" export --directory "${PROJECTHOME}/examples/qtype2/questionnaires" --format html --qtype 2 --qsubtype regular

# import results
#python main.py load responses --directory /home/gorana/Projects/softwarex-integration/database/s2-2 --qtype 2

# calculate copeland score
# python main.py 

# run stats - inter observer
# python main.py 

# run stats - intra observer
# python main.py 

# run visualizations - boxplot
# python main.py 

# run visualizations - histograms
# python main.py 