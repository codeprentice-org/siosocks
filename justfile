set shell := ["bash", "-c"]

default:
    just --summary

dependencies:
    pip install -U pip setuptools
    pip install -r requirements.txt

test *args:
    python -m pytest {{args}}

code:
    code .

pycharm:
    pyCharm .
