#!/bin/bash

echo "--- installing virtualenv ---"
# shall ignore if already installed
pip3.5 install virtualenv

# which python3.5
python3.5_path=$( which python3.5 )

echo "--- setting the virtualenv using python3.5 path; should be 3.5.2 found $python3.5_path ---"

virtualenv --python=$python3.5_path venv/fogenv
source venv/fogenv/bin/activate

# make sure you see prompt now with (fogenv) as prefix

echo "--- installing requirements which were frozen using [pip freeze > requirements.txt]---"
pip install -r requirements.txt


# run tests?

# echo "--- deactivating the virtualenv ---"
# deactivate

# echo "--- removing virtualenv directory ---"
# rm -rf venv/fogenv/