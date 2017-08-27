#!/bin/bash
cd `dirname $0`
source ./venv/bin/activate
python ical2mail.py
