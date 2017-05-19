#!/bin/bash

echo "--- installing virtualenv ---"
# shall ignore if already installed
pip install virtualenv

# which python3
python3_path=$( which python3.6 )

echo "--- setting the virtualenv using python3 path ---"

virtualenv --python=$python3_path venv/fogenv
source venv/fogenv/bin/activate

# make sure you see prompt now with (venv/fogenv) as prefix

echo "--- installing requirements which were frozen using [pip3.6 freeze > requirements.txt]---"
pip3.6 install -r requirements.txt


# run tests?

# echo "--- deactivating the virtualenv ---"
# deactivate

# echo "--- removing virtualenv directory ---"
# rm -rf venv/fogenv/