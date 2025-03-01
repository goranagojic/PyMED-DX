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
read -p $'DISCLAIMER! At this stage, the questionnaires exported in the previous step,\nshould be completed by human experts. For the purposes of an end-to-end\npipeline demonstration, we provide prefilled questionnaires along with a\ncorresponding database file, which will be downloaded in this step. After\nthis the demonstration will proceed to the response import process.\nPress ENTER to continue or press CTRL+C to abort.\n'
wget 'https://drive.usercontent.google.com/download?id=17nm4GUisruuU4CMNinpxBNhofwuOcwKR&export=download&authuser=1&confirm=t' -O "${TOOLHOME}/database/survey.db"

# Import results
command "Step 6: Load responses to the database." "python ${TOOLHOME}/main.py load responses --directory ${PROJECTHOME}/examples/qtype2/responses --qtype 2"

# Calculate the Copeland score
command "Step 7: Analyze the data that was loaded." "python ${TOOLHOME}/main.py analyze metrics --qtype 2 --mtype cs"

# Run stats - inter observer
command "Step 8: Run inter observer statistics." "python ${TOOLHOME}/main.py analyze stats --qtype 2 --stype inter"

# Run stats - intra observer
command "Step 9: Run intra observer 1 statistics." "python ${TOOLHOME}/main.py analyze stats --qtype 2 --stype intra --oid 1"

# Run visualizations - boxplot
command "Step 10: Export boxplot based on results." "python ${TOOLHOME}/main.py analyze visual --qtype 2 --vtype boxplot --directory ${PROJECTHOME}/examples/qtype2/plots"

# Run visualizations - histograms
command "Step 11: Export histogram based on results." "python ${TOOLHOME}/main.py analyze visual --qtype 2 --vtype histogram --directory ${PROJECTHOME}/examples/qtype2/plots"
