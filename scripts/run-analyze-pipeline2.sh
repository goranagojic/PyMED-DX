#!/bin/bash

export PROJECTHOME=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/..
export TOOLHOME="${PROJECTHOME}/pymeddx"
export PYTHONPATH="${TOOLHOME}":$PYTHONPATH


# make space for new, empty db file
if [ -f "${TOOLHOME}/database/survey.db" ]; then
    mv "${TOOLHOME}/database/survey.db" "${TOOLHOME}/database/survey.backup.db"
fi

wget 'https://drive.usercontent.google.com/download?id=1hWfYeN2rRHg3uBFlAJXRzwfqfGEJqm0_&export=download&authuser=1&confirm=t' -O "${TOOLHOME}/database/survey.db"

# import results
python "${TOOLHOME}/main.py" load responses --directory "${PROJECTHOME}/examples/qtype2/responses" --qtype 2

# calculate copeland score
python "${TOOLHOME}/main.py" analyze metrics --qtype 2 --mtype cs

# run stats - inter observer
python "${TOOLHOME}/main.py" analyze stats --qtype 2 --stype inter

# run stats - intra observer
python "${TOOLHOME}/main.py" analyze stats --qtype 2 --stype intra -o 1 -o 2 -o 3

# run visualizations - boxplot
python "${TOOLHOME}/main.py" analyze visual --qtype 2 --vtype boxplot --directory "${PROJECTHOME}/examples/qtype2/plots"

# run visualizations - histograms
python "${TOOLHOME}/main.py" analyze visual --qtype 2 --vtype histogram --directory "${PROJECTHOME}/examples/qtype2/plots"