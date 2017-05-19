#!/bin/bash

echo "--- installing virtualenv ---"
# shall ignore if already installed
pip install virtualenv

# which python3
python3_path=$( which python3.6 ) # ubuntu folks may want 3.5

echo "--- setting the virtualenv using python3 path ---"

virtualenv --python=$python3_path venv/fogenv
source venv/fogenv/bin/activate

# make sure you see prompt now with (fogenv) as prefix

echo "--- installing requirements which were frozen using [pip freeze > requirements.txt]---"
pip install -r requirements.txt


# run tests?

# echo "--- deactivating the virtualenv ---"
# deactivate

# echo "--- removing virtualenv directory ---"
# rm -rf venv/fogenv/