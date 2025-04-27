#!/bin/bash
pip install -r requirements.txt
python -m playwright install chromium
echo "Created by .env-template and config-template.json files. Edit them before running."
