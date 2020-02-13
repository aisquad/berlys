# -*- coding: utf-8 -*-
# ! c:\python\python3
import email
import imaplib
import json
import os
import re

from argparse import ArgumentParser as argparser
from datetime import datetime, timedelta
from re import search
from pathlib import Path as path
from locale import setlocale as set_local_env, LC_TIME as time_cat, atof as string_to_float, \
    format_string as local_env_fmt

from core import DateHandler


class Gmail:
    def __init__(self):
        self.detach_dir = "."
        self.config = None
        self.session = None

    def get_config(self):
        filename = os.path.join(self.detach_dir, "selae", "data", "config.json")
        with open(filename) as f:
            self.config = json.load(f)

    def set_session(self):
        self.session = imaplib.IMAP4_SSL(self.config['imap'])

    def login(self):
        self.get_config()
        self.set_session()
        email_address = f"{self.config['usr_email']}@{self.config['srv_email']}"
        type_, account_details = self.session.login(email_address, self.config['password'])
        if type_ != 'OK':
            raise Exception('Not able to sign in!')

    def check_dir(self):
        if 'attachments' not in os.listdir(self.detach_dir):
            os.mkdir('attachments')

    def optimize_size(self, params):
        if params.get('size'):
            params['size'] = int(params['size'])

    def optimize_date(self, params, key_header):
        dt = datetime.strptime(params[f'{key_header}-date'], "%a, %d %b %Y %H:%M:%S %Z")
        params[f'{key_header}-date'] = int(datetime.timestamp(dt))

    def optimize_dates(self, params):
        if params.get('creation-date'):
            self.optimize_date(params, 'creation')
        if params.get('modification-date'):
            self.optimize_date(params, 'modification')

    def parse_params(self, string):
        string = string.replace("\r\n\t", "").replace("\"", "").replace("; ", ";")
        params = dict([(item, "") if item.count("=") == 0 else tuple(item.split("=")) for item in string.split(";")])
        self.optimize_size(params)
        self.optimize_dates(params)
        return params

    def discard_parts(self, part):
        if part.is_multipart():
            # print ("#1 SKIPPING multipart")
            return True
        elif not part.get_content_disposition():
            # print ("#2 SKIPPING no content disposition")
            return True
        return False

    def wanted(self, filename_ext):
        if filename_ext and filename_ext.startswith(self.config["subject"]):
            return True

    def download_file(self, filename_ext, part):
        params = self.parse_params(part.get("Content-Disposition"))
        cdate = datetime.fromtimestamp(params['creation-date'])
        next_day = cdate + timedelta(days=1)
        filename, ext = os.path.splitext(filename_ext)
        new_filename = f"{filename} {next_day.strftime('%Y-%m-%d')}{ext}"
        file_path = os.path.join(self.detach_dir, 'attachments', new_filename)
        if not os.path.isfile(file_path):
            print(f"creating '{new_filename}'.")
            try:
                with open(file_path, 'wb') as fp:
                    fp.write(part.get_payload(decode=True))
            except OSError as e:
                print("Rejecting", e, part.get_filename())
        else:
            print(f"filename '{new_filename}' already exists.")

    def mail_sweep(self, email_body):
        mail = email.message_from_string(email_body.decode())
        for part in mail.walk():
            if self.discard_parts(part):
                continue

            filename_ext = part.get_filename()

            if self.wanted(filename_ext):
                self.download_file(filename_ext, part)

    def iterate(self, data):
        # Iterating over all emails
        for msg_id in data:
            type_, message_parts = self.session.fetch(msg_id, '(RFC822)')

            if type_ != 'OK':
                print('Error fetching mail.')
                break

            self.mail_sweep(message_parts[0][1])

    def dispatch(self):
        self.check_dir()

        self.session.select("Berly's")
        since_date = datetime.today() - timedelta(days=7)
        set_local_env(time_cat, "en_US.UTF8")
        since_date = since_date.strftime("%d-%b-%Y")
        type_, data = self.session.search(
            None,
            f'(SUBJECT "{self.config["subject"]}")',
            f'SENTSINCE {since_date} FROM {self.config["sender"]}'
        )
        if type_ != 'OK':
            print('Error searching Inbox.')
            return

        data = data[0].split()
        data.sort()
        data.reverse()
        self.iterate(data)

    def close(self):
        self.session.close()
        self.session.logout()


class DirSource:
    def __init__(self):
        self.root = ''
        self.reading_dirs = []
        self.files = []

    def read(self):
        pass

    def set_root(self, root):
        self.root = root

    def run(self):
        weekdays = {
            'dl.': dict(),
            'dt.': dict(),
            'dc.': dict(),
            'dj.': dict(),
            'dv.': dict(),
            'ds.': dict(),
            'dg.': dict()
        }
        for item in path(self.root).rglob('*.txt'):
            if re.search(r"\d{4}-\d{2}-\d{2}\.txt$", item.name):
                with open(item.absolute(), 'r', encoding='utf-8') as file:
                    txt = file.read()
                route_ = Route()
                date_ = DateHandler(item.name.rstrip("tx."))
                wday = date_.get_weekday()
                routes = route_.fetch_towns(txt)
                if not weekdays[wday]:
                    weekdays[wday] = routes
                else:
                    for route_ in routes:
                        if weekdays[wday].get(route_):
                            for town in routes[route_]:
                                weekdays[wday][route_].add(town)
                        else:
                            weekdays[wday][route_] = routes[route_]

        for wday in weekdays:
            for rt in weekdays[wday]:
                weekdays[wday][rt] = list(weekdays[wday][rt])
        print(json.dumps(weekdays, indent=4))


class FileSource:
    def __init__(self):
        # Java Style Constructor
        self.root = ''
        self.destination = ''
        self.absolute_path_filename = ''
        self.original_filename = ''
        self.filename = ''
        self.lines = ''

    # Java Style setters
    def set_root(self, root):
        path = os.path.join(*root) if isinstance(root, tuple) else root
        self.root = path

    def set_destination(self, *path, date_path='', reset=False):
        if not reset:
            self.destination = os.path.join(self.root, *path, date_path)
        else:
            self.destination = os.path.join(*path, date_path)

    def set_original_filename(self, filename=r'Volumen Rutas.txt'):
        self.original_filename = filename

    def set_absolute_path_filename(self, filename=''):
        if not filename:
            filename = self.original_filename
        self.absolute_path_filename = os.path.join(self.root, filename)
        if not self.filename:
            self.filename = self.absolute_path_filename

    # Methods
    def move(self):
        if not os.path.exists(self.destination):
            os.makedirs(self.destination)
        fname = date.to_format('%Y-%m-%d.txt')
        self.filename = os.path.join(self.destination, fname)
        os.rename(self.absolute_path_filename, self.filename)

    def read(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf8') as f:
                self.lines = f.read()
        else:
            print("El fitxer '%s' no eixsteix." % self.filename)

    def run(self):
        """
        Define correctly paths and filenames fisrt before running this method.
        """
        if os.path.exists(self.absolute_path_filename):
            self.move()
        else:
            files = [f for f in os.listdir(self.destination) if search('[\d-]+\.txt', f)]
            files.sort()
            self.filename = os.path.join(self.destination, files[-1])
        self.read()

    def show_filenames(self):
        print(
            f"FILENAME: {self.filename}\n"
            f"ABS PATH FILENAME: {self.absolute_path_filename}\n"
            f"DESTINATION: {self.destination}\n\n"
        )


class Route:
    routes = (678, 679, 680, 681, 682, 686, 688, 696)

    def __init__(self):

        self.routes_re = re.compile(
            r"25\s+BERLYS ALIMENTACION S\.A\.U\s+[\d:]+\s+[\d.]+\s+Volumen de pedidos de la ruta :\s+"
            r"(?P<routeid>\d+)\s+(?P<routedesc>[^\n]+)\s+Día de entrega :\s+(?P<date>[^ ]{10})(?P<paradas>.+?)"
            r"NUMERO DE CLIENTES\s+:\s+(?P<costnum>\d+).+?"
            r"SUMA VOLUMEN POR RUTA\s+:\s+(?P<volamt>[\d,.]+) (?P<um1>(?:PVL|KG)).+?"
            r"SUMA KG POR RUTA\s+:\s+(?P<weightamt>[\d,.]+) (?P<um2>(?:PVL|KG)).+?"
            r"(?:CAPACIDAD TOTAL CAMIÓN\s+:\s+(?P<truckcap>[\d,.]+) (?P<um3>(?:PVL|KG)))?",
            re.DOTALL
        )
        self.items = re.compile(
            r"(?P<code>\d{10}) (?P<customer>.{35}) (?P<town>.{20}) (?P<ordnum>.{10}) (?P<vol>.{11})(?: (?P<UM>.{2,3}))?")
        self.lines = []

    def standard(self):
        for route in self.routes_re.findall(self.lines):
            if int(route[0]) in (678, 681, 686):
                print(f"{route[0]}\t{route[1]}\t{route[2]}\t{route[4]}\t{route[5]}\t{route[6]}\t{route[7]}")
                for line in self.items.findall(route[3]):
                    col0 = line[0].strip()
                    col1 = line[1].strip()
                    col2 = line[2].strip()
                    col3 = line[3].strip()
                    col4 = line[4].strip()
                    col5 = line[5].strip() if line[5] else ''
                    print(f"{col0}\t{col1}\t{col2}\t{col3}\t{col4}\t{col5}")
                print()

    def routing(self, route_ids=(680,)):
        route_volumes = {}
        routes = {}
        volume = 0
        for route in self.routes_re.findall(source.lines):
            if int(route[0]) in route_ids:
                for line in self.items.findall(route[3]):
                    nom_client = line[1].strip()
                    nom_ciutat = line[2].strip()
                    volum = line[4].strip()
                    # print (f"{nom_client}\t{volum}\tPVL\t({nom_ciutat})")
                    route_volumes[nom_client] = route_volumes.get(nom_client, 0) + string_to_float(volum)
                    if not routes.get(route[0]):
                        routes[route[0]] = {}
                    item = {nom_client: (route_volumes[nom_client], nom_ciutat, route[0])}
                    routes[route[0]].update(item)
        i = 1
        for route in routes:
            print(f'#R{route}')
            for client in routes[route]:
                client_volume = routes[route][client][0]
                volume += client_volume
                print(f'{i}\t\t{client}\t{local_env_fmt("%.3f", client_volume)}\t{routes[route][client][1]}')
                i += 1
        print(f'\t\t\t{local_env_fmt("%.3f", volume)}')

    def write(self, route_ids=(680,), fname='rutes.txt'):
        with open(fname, 'w', encoding='utf8') as f:
            for route in self.routes_re.findall(source.lines):
                if int(route[0]) in route_ids:
                    print(f"{route[0]}")
                    for line in self.items.findall(route[3]):
                        nom_client = line[1].strip()
                        nom_ciutat = line[2].strip()
                        volum = line[4].strip()
                        l = f"{nom_client}\t{volum}\tPVL\t({nom_ciutat})"
                        print(l)
                        f.write(l + '\n')
                    print

    def fetch_towns(self, text) -> dict:
        routes = dict()
        for route in self.routes_re.findall(text):
            towns = set()
            if int(route[0]) in self.routes:
                for line in self.items.findall(route[3]):
                    town = line[2].strip()
                    towns.add(town)
                routes.update({route[0]: towns})
        return routes


def dayly():
    if week_routes.get(wd):
        route.routing(week_routes[wd])
    else:
        raise KeyError('Today you must to take a pause.')
    print(f"\nDATE: {date.to_short_french_datetime()}")


def routes_by_weekday():
    dir = DirSource()
    dir.root = r"C:\Users\igorr\OneDrive\Eclipse\Python\dades\Berlys"
    print(dir.root)
    dir.run()


if __name__ == '__main__':
    r"""
    Llegim un fitxer de C:\Users\<USERNAME>\Downloads\Volumen Rutas.txt
    El reanomenem a C:\Users\<USERNAME>\OneDrive\-\Python\dades\Berlys\<data demà>.txt
    
    Si no existeix el fitxer C:\Users\<USERNAME>\Downloads\Volumen Rutas.txt és perque
    ja s'ha reanomenat i hem de llegir el darrer fitxer mogut a la carpeta C:\Users\<USERNAME>\OneDrive\-\Python\Berlys\
    amb el format %Y/%m/%d.txt que contindrà les dades que ens interessen.
    """
    set_local_env(time_cat, 'Catalan_Andorra.UTF-8')
    date = DateHandler()
    if 18 < date.get_hour() < 24:
        date.tomorrow()
    wd = date.get_weekday()

    source = FileSource()
    source.set_root((path.home(), 'Downloads'))
    source.set_destination(
        path.cwd(),
        'dades',
        'Berlys',
        date_path=datetime.strftime(date.to_date(), '%Y$s%m'.replace('$s', os.path.sep)),
        reset=True
    )
    source.set_original_filename(r'Volumen Rutas.txt')
    source.set_absolute_path_filename()
    source.run()
    # source.show_filenames()

    route = Route()
    week_routes = {
        'dl.': (680, 681),
        'dt.': (680, 681),
        'dc.': (680, 681),
        'dj.': (680, 679),
        'dv.': (680, 688),
        'ds.': (680, 682, 688),
    }

    argparser = argparser()
    argparser.add_argument('-d', dest='dayly', action='store_true')
    argparser.add_argument('-w', dest='weekdays', action='store_true')
    argparser.add_argument('-r', dest='routelist', type=int, nargs='+')
    argparser.add_argument('-g', dest='mail', action='store_true')
    args = argparser.parse_args()

    if args.dayly:
        dayly()
    if args.weekdays:
        routes_by_weekday()
    if args.routelist:
        route.routing(args.routelist)
    if args.mail:
        gmail = Gmail()
        gmail.login()
        gmail.dispatch()
        gmail.close()
