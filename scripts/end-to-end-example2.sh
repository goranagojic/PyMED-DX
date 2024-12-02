#!/bin/bash

command () {
    echo $1
    read -p 'Press ENTER to continue.'
    (set -x; $2)
    echo
}

export PROJECTHOME=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/..
export TOOLHOME="${PROJECTHOME}/pymeddx"
export PYTHONPATH="${TOOLHOME}":$PYTHONPATH


# Make space for new, empty db file
if [ -f "${TOOLHOME}/database/survey.db" ]; then
    mv "${TOOLHOME}/database/survey.db" "${TOOLHOME}/database/survey.backup.db"
fi

# Load observers
command "Step 1: Load observers." "python ${TOOLHOME}/main.py load observers --filepath ${PROJECTHOME}/examples/observers.json"

# Load reference images
command "Step 2a: Load reference images." "python ${TOOLHOME}/main.py load images -d ${PROJECTHOME}/examples/qtype2/images/originals -e .png -q 2 -m originals.json"

# Load reference images
command "Step 2b: Load ML model images." "python ${TOOLHOME}/main.py load images -d ${PROJECTHOME}/examples/qtype2/images/ml-outputs -e .png -q 2 -m ml-outputs.json"

# Generate questions
command "Step 3: Generate questions in the database." "python ${TOOLHOME}/main.py generate questions --qtype 2"

# Generate questionnaires
command "Step 4: Generate questionnaires in database." "python ${TOOLHOME}/main.py generate questionnaire --qtype 2"

# Export regular questionnaires
command "Step 5: Export questionnaires to html." "python ${TOOLHOME}/main.py export --directory ${PROJECTHOME}/examples/qtype2/questionnaires --format html --qtype 2"

# At this point the questionnaires should be filled out
# and the results should be prepare like in the folder:
# "examples/qtype2/responses". Because this is an example
# we have prepared a database and some results to show how to
# load and analyze them.
read -p $'DISCLAIMER! We have already done the Step 6, for you, but at this point the\nquestionnaires should be filled out and the results should be prepared.\nThe database file is too large for git. Therefore, we have stored it on\ngoogle drive and it will automatically download to the correct location.\nJust press ENTER to continue with the example or press CTRL+C to abort.\n'
wget 'https://drive.usercontent.google.com/download?id=1hWfYeN2rRHg3uBFlAJXRzwfqfGEJqm0_&export=download&authuser=1&confirm=t' -O "${TOOLHOME}/database/survey.db"

# Import results
command "Step 7: Load responses to the datapase." "python ${TOOLHOME}/main.py load responses --directory ${PROJECTHOME}/examples/qtype2/responses --qtype 2"

# Calculate the Copeland score
command "Step 8: Analyze the data that was loaded." "python ${TOOLHOME}/main.py analyze metrics --qtype 2 --mtype cs"

# Run stats - inter observer
command "Step 9: Run inter observer statistics." "python ${TOOLHOME}/main.py analyze stats --qtype 2 --stype inter"

# Run stats - intra observer
command "Step 10: Run intra observer 1 statistics." "python ${TOOLHOME}/main.py analyze stats --qtype 2 --stype intra --oid 1"

# Run visualizations - boxplot
command "Step 11: Export boxplot based on results." "python ${TOOLHOME}/main.py analyze visual --qtype 2 --vtype boxplot --directory ${PROJECTHOME}/examples/qtype2/plots"

# Run visualizations - histograms
command "Step 12: Export histogram based on results." "python ${TOOLHOME}/main.py analyze visual --qtype 2 --vtype histogram --directory ${PROJECTHOME}/examples/qtype2/plots"
