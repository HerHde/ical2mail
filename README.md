# ical2mail
A Python3 script to fetch iCalendar/ical/ics-feeds from the web and send an email with upcoming events.

## Requirements
In order to use this script you need
- a SMTP account/server
- one or more URLs to ICS/iCalendar files
- Python 3, [pip](https://pip.pypa.io/en/stable/installing/) and [virtualenv](https://virtualenv.pypa.io/en/stable/installation/) installed.

## Installation
Download this repository, create a new virtualenv and configure the script.

    git clone git@github.com:HerHde/ical2mail.git
    cd ical2mail
    virtualenv --python=/usr/bin/python3 venv
    source venv/bin/activate
    pip install -r requirements.txt

Now copy/rename the `config.py.sample` to `config.py`, open it in your preferred editor and make adjustments, at least you need to configure `MAIL_FROM`, `MAIL_TO`, `ICAL_URLS` and the `SMTP_*` variables.

## Usage
You need to enter the `virtualenv` every time you are in a new shell session. Inside the repository's directory run

    source venv/bin/activate
    python ical2mail.py

If no text appears, everything went well!

## Modification
To get a different formatted output, you can use [Jinja2-templates](http://jinja.pocoo.org/docs/latest/templates/). Modify the default [template](templates/plain.jinja) or create a new one in the `templates/` folder and update the config.

## Contributors
This script is inspired by [Cord Beermann](https://cord.de/cord-beermann)'s [Calendar2Mail](https://cord.de/selfmade) script, which is written in Pearl and served my purposes well for a long time. Thank you Cord!

I heavily used [Severin "tiefpunkt" Schols](http://tiefpunkt.com/)'s [ical2email](https://github.com/tiefpunkt/ical2email) as a base, a Python 2 script, which does slightly the same as this script, but in a different manner. Thank you tiefpunkt! Without your script I would have procrastinated the implementation of mine a long time.

This script is written and maintained by Henrik "HerHde" Hüttemann.
## License
This work is licensed under the [GNU GPLv3](LICENSE).