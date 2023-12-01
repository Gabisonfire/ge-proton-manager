#!/bin/bash
rm -rf build/
rm -rf dist/
pipenv install --dev
pipenv run pyinstaller --onefile --paths $(pipenv --venv)/lib/python3.11/site-packages/ -n ge-proton-manager main.py