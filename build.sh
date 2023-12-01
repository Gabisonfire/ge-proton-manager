#!/bin/bash
pipenv run pyinstaller --onefile --paths $(pipenv --venv)/lib/python3.11/site-packages/ -n ge-proton-manager main.py