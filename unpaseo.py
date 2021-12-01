#!/usr/bin/python3

import argparse
import logging
import re
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Set

import requests
from bs4 import BeautifulSoup

URL = "https://onepaseoliving.com/plans-availability/"

UNIT_DIV = r'class="gridder_item-inner"'
UNIT_LI = r'<li class="gridder-list 2722746" data-beds="0" data-townhome="no" ' \
          r'data-griddercontent="#content2722746">'
AVAILABLE_STR = 'Available Now'
UNAVAILABLE_STR = 'No Vacancy'

MASTER_UNITS = {
    'Studio S1', '1 x 1 A2', '1 x 1 A3', '2 x 2 B1',
    '2 x 2 B2', '2 x 2 B2.1', '2 x 2 B3', '2 x 2 B3.1',
    '3 x 2 C1', '3 x 2 C2', 'Townhome 1', 'Townhome 1b',
    'Townhome 2', 'Townhome 1a', 'Townhome 1c', 'Townhome 2a'
}
INTERESTED_UNITS = {
    'Studio S1', '1 x 1 A2', '1 x 1 A3', '2 x 2 B1',
    '2 x 2 B2', '2 x 2 B2.1',
}


class Unit(object):
    def __init__(self, name: str, available: bool) -> None:
        self.name = name
        self.available = available

    def __str__(self) -> str:
        return f"{self.name}:\t{self.available}"


class Processor(object):
    def __init__(self, url):
        self.url = url
        self.units = []

    def fetch_webpage(self, url: str):
        req = requests.get(url)
        return BeautifulSoup(req.text, "html.parser")

    def get_unit_name(self, el) -> str:
        figure = el.find('figure')
        matches = re.findall(r'title="One Paseo (.*)"', str(figure))
        return matches[0] if len(matches) > 0 else None

    def process(self):
        self.units = []
        soup = self.fetch_webpage(self.url)
        for el in soup.find_all("li", attrs={'class': 'gridder-list'}):
            name = self.get_unit_name(el).replace(" Floorplan", "").rstrip()
            if re.findall(AVAILABLE_STR, str(el)):
                available = True
            elif re.findall(UNAVAILABLE_STR, str(el)):
                available = False
            self.units.append(Unit(name, available))

    def check_missing(self):
        lowered_found = {s.name.lower() for s in self.units}
        lowered_master = {s.lower() for s in MASTER_UNITS}
        return lowered_master - lowered_found

    def get_availble_interested_units(self, units: Set[Unit]):
        return units.intersection(INTERESTED_UNITS)

    def generate_report(self):
        report = ""
        available_units = {u.name for u in self.units if u.available}
        report += f"Found {len(self.units)} units\n"
        missing_units = self.check_missing()
        available_interested_units = self.get_availble_interested_units(
            available_units)
        if len(missing_units) > 0 or len(available_interested_units) > 0:
            report_misunits = '\n\t- '.join(
                missing_units) if len(missing_units) > 0 else 0
            report += "\nAvailable:\n\t- " + '\n\t- '.join(available_units)
            report += f"\n\nMissing:\n\t- {report_misunits}"
            self.send_text(report)
            self.send_report(report)
            logging.info(f"Generated report:\n{report}")
        else:
            logging.info(
                f"No interested units available, only availab"
                f"le units: {available_units}")

    def send_text(self, report: str):
        global args

        if args.messagescript:
            subprocess.run([
                "/usr/bin/osascript",
                args.messagescript,
                ".applescript",
                args.number,
                str(report)
            ])

    def send_report(self, report: str):
        global args

        msg = MIMEMultipart()
        msg["From"] = args.fromemail
        msg["To"] = args.recemail
        msg["Subject"] = "One Paseo Units Available"
        msg.attach(MIMEText(report, "plain"))

        text = msg.as_string()
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(args.fromemail, args.password)

        server.sendmail(args.fromemail, args.recemail, text)
        server.quit()


def main():
    processor = Processor(URL)
    processor.process()
    processor.generate_report()


if __name__ == "__main__":
    logging.basicConfig(
        format='[%(levelname)s] %(asctime)s - %(message)s', level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f", "--fromemail", required=True, type=str,
        help="Email to send from."
    )
    parser.add_argument(
        "-r", "--recemail", required=True, type=str,
        help="Email to send to"
    )
    parser.add_argument(
        "-p", "--password", required=True, type=str,
        help="Password to sending email"
    )
    parser.add_argument(
        "-n", "--number", required=False, type=str,
        help="Phone number to send reports to"
    )
    parser.add_argument(
        "-m", "--messagescript", required=False, type=str,
        help="Path to applescript to send iMessage"
    )
    args = parser.parse_args()
    main()
