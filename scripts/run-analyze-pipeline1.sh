#!/bin/bash

export PROJECTHOME=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/..
export TOOLHOME="${PROJECTHOME}/pymeddx"
export PYTHONPATH="${TOOLHOME}":$PYTHONPATH


# make space for new, empty db file
if [ -f "${TOOLHOME}/database/survey.db" ]; then
    mv "${TOOLHOME}/database/survey.db" "${TOOLHOME}/database/survey.backup.db"
fi

# copy prepared database
#cp "${PROJECTHOME}/examples/qtype1/survey.db" "${TOOLHOME}/database/"

# import results
python "${TOOLHOME}/main.py" load responses --directory "${PROJECTHOME}/examples/qtype1/responses" --qtype 1

# calculate diagnostic value
python "${TOOLHOME}/main.py" analyze metrics --qtype 1 --mtype dv

# run stats - inter observer
python "${TOOLHOME}/main.py" analyze stats --qtype 1 --stype inter

# run stats - intra observer
python "${TOOLHOME}/main.py" analyze stats --qtype 1 --stype intra

# run visualizations - boxplot
python "${TOOLHOME}/main.py" analyze visual --qtype 1 --vtype boxplot --directory "${PROJECTHOME}/examples/qtype1/plots"

# run visualizations - histograms
python "${TOOLHOME}/main.py" analyze visual --qtype 1 --vtype histogram --directory "${PROJECTHOME}/examples/qtype1/plots"