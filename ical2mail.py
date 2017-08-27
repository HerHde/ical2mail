#!/usr/bin/env python3
""" A Python3 script to fetch iCalendar/ical/ics-feeds from the web and send an email
with upcoming events."""
from email.message import Message
import smtplib
from datetime import datetime, timedelta, date
from pytz import timezone
from icalendar import Calendar, vDDDTypes
from dateutil import rrule
import requests
import jinja2
import config

TZ = timezone(config.ICAL_TZ)
TODAY = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
DATE_MIN = TODAY - timedelta(days=config.DAYS_PREV)
DATE_MAX = TODAY + timedelta(days=config.DAYS_NEXT) - timedelta(microseconds=1)
EVENT_PROPERTIES = {
    "unique": [
        "class", "created", "description", "dtstart", "geo", "last-mod",
        "location", "organizer", "priority", "dtstamp", "seq", "status",
        "summary", "transp", "uid", "url", "recurid"
    ],
    "xor": [
        "dtend", "duration"
    ],
    "many": [
        "attach", "attendee", "categories", "comment", "contact", "exdate",
        "exrule", "rstatus", "related", "resources", "rdate", "rrule", "x-prop"
    ]
}


def to_tz_datetime(adate, dtend=False):
    """Return a timezoned datetime from a given date or datetime.

        Args:
            adate: A date or datetime instance.
            dtend: A boolean defining whether a date is a dtend and therefore should
                be set to 23:59.

        Returns:
            An offset-aware timezoned datetime.
    """
    if type(adate) is date and dtend:
        adate = datetime(adate.year, adate.month, adate.day, 23, 59, 59, 0, TZ)
    elif type(adate) is date and not dtend:
        adate = datetime(adate.year, adate.month, adate.day, 0, 0, 0, 0, TZ)
    else:
        adate = adate.astimezone(TZ)
    return adate

def format_date(adate):
    """Return a dictionary containing formatted versions of adate."""
    return {
        "dt": to_tz_datetime(adate),
        "datetime": to_tz_datetime(adate).strftime(config.FORMAT_DATETIME),
        "date": to_tz_datetime(adate).strftime(config.FORMAT_DATE),
        "time": to_tz_datetime(adate).strftime(config.FORMAT_TIME)
    }

def parse_ics(ics):
    """Parse an ics-file and return the vevents as a list of tuples.

        Returns:
            A list of tuples containing
                1. the event as an icalendar event
                1. the starttime as a datetime
                1. the endtime as a datetime
                1. the duration as a timedelta
                of an event.
    """
    if isinstance(ics, dict):
        response = requests.get(
            ics["url"],
            auth=requests.auth.HTTPBasicAuth(
                ics["username"],
                ics["password"]
            )
        )
        ics_url = ics["url"]
    else:
        response = requests.get(ics)
        ics_url = ics

    cal = Calendar.from_ical(response.text)
    event_list = []

    for event in cal.walk('vevent'):
        dtstart = event.get('dtstart').dt
        duration = event.get('dtend').dt - dtstart

        dtstart = to_tz_datetime(dtstart)

        # Generate recurrences
        if "rrule" in event:
            rule = rrule.rrulestr(
                event.get('rrule').to_ical().decode('utf8'),
                dtstart=to_tz_datetime(event.get('dtstart').dt)
            )
            for dtstart_rec in rule.between(DATE_MIN - timedelta(microseconds=1), DATE_MAX):
                event_list.append(
                    (
                        event,
                        dtstart_rec,
                        dtstart_rec + duration,
                        duration,
                        ics_url
                    )
                )
        elif dtstart >= DATE_MIN and dtstart < DATE_MAX:
            event_list.append(
                (
                    event,
                    dtstart,
                    to_tz_datetime(event.get('dtend').dt, True),
                    duration,
                    ics_url
                )
            )
    return remove_modified_recurrence(event_list)

def debug_events(event_list):
    """Print the events in event_list fpr debugging purposes."""
    for item in event_list:
        for prop in ["summary", "uid", "dtstart", "sequence", "recurrence-id", "rrule"]:
            if prop in item[0]:
                print(prop.rjust(14), end=': ')
                if isinstance(item[0][prop], vDDDTypes):
                    print(item[0][prop].dt)
                else:
                    print(item[0][prop])
        print("start".rjust(14), end=': ')
        print(item[1])
        print("ende".rjust(14), end=': ')
        print(item[2])
        print()

def remove_modified_recurrence(event_list):
    """Remove events which have a modified recurrence."""
    recurrences = []
    for item in event_list:
        if "recurrence-id" in item[0]:
            recurrences.append((item[0].get("uid"), item[0].get("recurrence-id").dt))

    for item in event_list:
        for rec in recurrences:
            if item[1] == rec[1] and item[0].get("uid") == rec[0]:
                event_list.remove(item)
    return event_list

def simplify_events(event_list):
    """Prepare events for an easy usage in Templates."""
    simple_events = []
    for item in event_list:
        new_event = {}
        for prop in EVENT_PROPERTIES["unique"]:
            if prop in item[0]:
                if isinstance(item[0].get(prop), vDDDTypes):
                    new_event[prop] = to_tz_datetime(item[0].get(prop).dt)
                else:
                    new_event[prop] = item[0].get(prop).to_ical().decode()
            # else:
            # 	new_event[prop] = ""
        # Duration ignored, only parsing dtend
        new_event["dtend"] = to_tz_datetime(item[0].get("dtend").dt)
        new_event["duration"] = item[3]
        new_event["ics_url"] = item[4]
        # TODO Not properly parsed but pasted
        for prop in EVENT_PROPERTIES["many"]:
            if prop in item[0]:
                new_event[prop] = item[0].get(prop)
            # else:
            # 	new_event[prop] = []
        # Now the simple properties
        new_event["start"] = format_date(item[1])
        new_event["end"] = format_date(item[2])
        simple_events.append(new_event)
    return simple_events

def generate_output(event_list):
    """Parse events with the template and return the output.

        Return:
            A tupel containing
                1. the content and
                1. the title
                for usage in emails.
    """
    template_loader = jinja2.FileSystemLoader(searchpath="templates/")
    template_env = jinja2.Environment(
        loader=template_loader,
        trim_blocks=True,
        lstrip_blocks=True
    )

    header_title_template = template_env.from_string(config.MAIL_SUBJECT)
    template = template_env.get_template(config.TEMPLATE_FILE)

    template_vars = {
        "today": format_date(TODAY),
        "date_min": format_date(DATE_MIN),
        "date_max": format_date(DATE_MAX),
        "days_prev": config.DAYS_PREV,
        "days_next": config.DAYS_NEXT,
        "format_datetime": config.FORMAT_DATETIME,
        "format_date": config.FORMAT_DATE,
        "format_time": config.FORMAT_TIME,
        "calendars": config.ICAL_URLS,
        "timezone": config.ICAL_TZ,
        "mail_from": config.MAIL_FROM,
        "mail_to": config.MAIL_TO,
        "mail_title": config.MAIL_SUBJECT,
        "events": simplify_events(event_list)
    }

    return [
        template.render(template_vars),
        header_title_template.render(template_vars)
    ]

def send_mail(content):
    """Send out an email."""
    if isinstance(config.MAIL_TO, list):
        mail_to_list = config.MAIL_TO
    else:
        mail_to_list = [config.MAIL_TO]

    for mail_to in mail_to_list:
        msg = Message()
        msg.set_payload(content[0], "utf-8")
        msg["Subject"] = content[1]
        msg["From"] = config.MAIL_FROM
        msg["To"] = mail_to

        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(config.SMTP_USER, config.SMTP_PASS)
        server.sendmail(config.MAIL_FROM, mail_to, msg.as_string())
        server.quit()

def main():
    events = []
    for url in config.ICAL_URLS:
        events += parse_ics(url)

    events = sorted(events, key=lambda event: event[1])
    output_text = generate_output(events)

    if config.DRYRUN:
        print("TITLE: " + output_text[1])
        print("----------------------------------------")
        print(output_text[0].replace(' ', ' '))
    else:
        send_mail(output_text)

if __name__ == "__main__":
    main()
