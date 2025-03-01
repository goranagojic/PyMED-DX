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

# Load images
command "Step 2: Load images." "python ${TOOLHOME}/main.py load images --directory ${PROJECTHOME}/examples/qtype1/images --extension .png --qtype 1 --metadata-file images.json"

# Generate questions
command "Step 3: Generate questions in the database." "python ${TOOLHOME}/main.py generate questions --qtype 1"

# Generate regular questionnaires
command "Step 4a: Generate regular questionnaires in database." "python ${TOOLHOME}/main.py generate questionnaire --qtype 1 --qsubtype regular --kquestions 8"

# Generate control questionnaires
command "Step 4b: Generate control questionnaires in database." "python ${TOOLHOME}/main.py generate questionnaire --qtype 1 --qsubtype control --nquestionnaire 3 --kquestions 8"

# Export regular questionnaires
command "Step 5a: Export regular questionnaires to html." "python ${TOOLHOME}/main.py export --directory ${PROJECTHOME}/examples/qtype1/questionnaires --format html --qtype 1 --qsubtype regular"

# Export control questionnaires
command "Step 5b: Export control questionnaires to html." "python ${TOOLHOME}/main.py export --directory ${PROJECTHOME}/examples/qtype1/questionnaires --format html --qtype 1 --qsubtype control" 

# At this point the questionnaires should be filled out
# and the results should be prepare like in the folder:
# "examples/qtype1/responses". Because this is an example
# we have prepared a database and the results to show how
# to load and analyze them.
read -p $'DISCLAIMER! At this stage, the questionnaires exported in the previous step,\nshould be completed by human experts. For the purposes of an end-to-end\npipeline demonstration, we provide prefilled questionnaires along with a\ncorresponding database file, which will be copied in this step. After\nthis the demonstration will proceed to the response import process.\nPress ENTER to continue or press CTRL+C to abort.\n'

wget 'https://drive.usercontent.google.com/download?id=1gvBjpwo7w_DiCDKr_Yqkn-iheI9jgSyx&export=download&authuser=1&confirm=t' -O "${TOOLHOME}/database/qt1.zip"
unzip -o "${TOOLHOME}/database/qt1.zip" -d "${TOOLHOME}/database/"
rm -rf "${PROJECTHOME}/examples/qtype1/responses"/*
mv -f "${TOOLHOME}/database/responses/"* "${PROJECTHOME}/examples/qtype1/responses"
rm -rf "${TOOLHOME}/database/responses/"
rm -rf "${TOOLHOME}/database/qt1.zip"

# Import results
command "Step 6: Load responses to the database." "python ${TOOLHOME}/main.py load responses --directory ${PROJECTHOME}/examples/qtype1/responses --qtype 1"

# Calculate the diagnostic value
command "Step 7: Analyze the data that was loaded." "python ${TOOLHOME}/main.py analyze metrics --qtype 1 --mtype dv"

# Run stats - inter observer
command "Step 8: Run inter observer statistics." "python ${TOOLHOME}/main.py analyze stats --qtype 1 --stype inter"

# Run stats - intra observer
command "Step 9: Run intra observer 1 statistics." "python ${TOOLHOME}/main.py analyze stats --qtype 1 --stype intra --oid 1"

# Run visualizations - boxplot
command "Step 10: Export boxplot based on results." "python ${TOOLHOME}/main.py analyze visual --qtype 1 --vtype boxplot --directory ${PROJECTHOME}/examples/qtype1/plots"

# Run visualizations - histograms
command "Step 11: Export histogram based on results." "python ${TOOLHOME}/main.py analyze visual --qtype 1 --vtype histogram --directory ${PROJECTHOME}/examples/qtype1/plots"
