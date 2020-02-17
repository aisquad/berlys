# -*- coding: utf-8 -*-
# ! c:\python\python3

"""
    Programa que imprimeix per pantalla les rutes assignades al repartidor o totes les assignades a l'empressa.

    L'opció manual -d carrega el fitxer anomenat "Volumen Rutas.txt" de la carpeta de descàrregues ../../../Downloads
    que s'haurà descarregat prèviament des del navegador consultant el correu electrònic manualment. Aleshores obtenim
    les dades i reanomenem el fitxer a la carpeta amb el nom: "Volumen Rutas <DATA REPARTIMENT>.txt" dins de la carpeta
    d'arxiu     anomenada ../../data/<ANY ACTUAL>/<MES ACTUAL>. L'esmentat paràmetre <DATA REPARTIMENT> és la data de
    repartiment,     normalment del dia posterior al de la descàrrega del fitxer i <ANY ACTUAL> i <MES ACTUAL> són l'any
    i el mes en curs respectivament.

    Si no es troba el fitxer dins de la carpèta de descàrregues, se recerca a la carpeta
    ../../data/<ANY ACTUAL>/<MES ACTUAL> i se n'extrau les dades.

    Si es passa l'opció -g, descarreguem el fitxer directament del correu a la carpeta ../../data/attachments
    s'alça còpia a la carpeta ../../data/<ANY ACTUAL>/<MES ACTUAL> i s'aprofiten les dades per a obtindre els
    clients de la ruta/rutes assignades al repartidor o a tota l'empresa depenent si s'ha triat l'opció -r o --all.

    - Amb l'opció -r [r1 [r2 ][...]] especifiquem quines rutes mostrar, seran les rutes assignades a un repartidor.
    - L'opció --all mostrarà totes les rutes assignades a l'empresa.

    Segons el dia de la setmana hi ha unes rutes assignades per defecte al repartidor de manera que l'opció -d, sense
    especificar rutes.
"""

import json
import os
import re

from argparse import ArgumentParser as argparser
from datetime import datetime
from locale import setlocale as set_local_env, LC_TIME as time_cat, atof as string_to_float, \
    format_string as local_env_fmt
from pathlib import Path as path
from re import search

from Berlys.getmail import GetMail
from core import DateHandler


class Config:
    def __init__(self):
        self.filename = os.path.join('..', '..', "resources", "python-berlys-config.json")

    def get_config(self):
        with open(self.filename) as f:
            return json.load(f)


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

    def routes_by_weekday(self):
        self.root = r"C:\Users\igorr\OneDrive\scripts\data\berlys\data"
        print(self.root)
        self.run()


class FileSource:
    def __init__(self):
        self.read_folder = ''
        self.read_filename = ''
        self.write_folder = ''
        self.write_filename = ''
        self.lines = ''
        self.default_filename = ''

    def set_default_filename(self):
        c = Config().get_config()
        self.default_filename = c['default_filename']

    def set_read_folder(self, folder='.'):
        self.read_folder = os.path.join(*folder) if isinstance(folder, tuple) else folder

    def set_read_filename(self, filename=None):
        if not filename:
            filename = self.default_filename
        self.read_filename = filename

    def set_write_folder(self, *path, date_path=''):
        self.write_folder = os.path.join(*path, date_path)

    def set_write_filename(self, filename):
        self.write_filename = filename

    def get_write_filename(self):
        if not self.write_filename:
            basename, ext = os.path.splitext(self.default_filename)
            self.write_filename = date.to_format(f'{basename} %Y-%m-%d{ext}')
        return self.write_filename

    def get_read_filename_absolute_path(self):
        return os.path.join(self.read_folder, self.read_filename)

    def get_write_filename_absolute_path(self):
        return os.path.join(self.write_folder, self.get_write_filename())

    def move(self):
        if not os.path.exists(self.write_folder):
            os.makedirs(self.write_folder)
        self.set_write_filename(date.to_format('%Y-%m-%d.txt'))
        if not os.path.exists(self.get_write_filename_absolute_path()):
            os.rename(
                self.get_read_filename_absolute_path(),
                self.get_write_filename_absolute_path()
            )
        # Faking: write now is read.
        self.set_read_folder(self.write_folder)
        self.set_read_filename(self.write_filename)

    def get_lines(self):
        if os.path.exists(self.get_read_filename_absolute_path()):
            with open(self.get_read_filename_absolute_path(), 'r', encoding='utf8') as f:
                self.lines = f.read()
        else:
            print("El fitxer '%s' no eixsteix." % self.get_read_filename_absolute_path())

    def run(self):
        """
        Define correctly paths and filenames fisrt before running this method.
        """
        if os.path.exists(self.get_read_filename_absolute_path()):
            self.move()
        else:
            files = [f for f in os.listdir(self.write_folder) if search('[\d-]+\.txt', f)]
            files.sort()
            self.set_read_folder(self.write_folder)
            self.set_read_filename(files[-1])
        self.get_lines()

    def init(self):
        self.set_default_filename()
        self.set_read_folder((path.home(), 'Downloads'))
        self.set_read_filename()
        self.set_write_folder(
            '..', '..',
            'data', 'berlys',
            date_path=datetime.strftime(date.to_date(), '%Y$s%m'.replace('$s', os.path.sep)),
        )

    def download_source(self):
        gmail = GetMail()
        gmail.login()
        gmail.dispatch()
        gmail.close()


class Route:
    route_tuple = (678, 679, 680, 681, 682, 686, 688, 696)

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
        self.customers_re = re.compile(
            r"(?P<code>\d{10}) (?P<customer>.{35}) (?P<town>.{20}) (?P<ordnum>.{10}) (?P<vol>.{11})(?: (?P<UM>.{2,3}))?")

    def dispatch(self, route_ids=(680,)):
        route_volumes = {}
        routes = {}
        volume = 0
        for route in self.routes_re.findall(source.lines):
            if int(route[0]) in route_ids:
                header = f"{route[2]}\t{route[0]}\t{route[1].lstrip('25 ')}"
                for line in self.customers_re.findall(route[3]):
                    nom_client = line[1].strip()
                    nom_ciutat = line[2].strip()
                    volum = line[4].strip()
                    # print (f"{nom_client}\t{volum}\tPVL\t({nom_ciutat})")
                    route_volumes[nom_client] = route_volumes.get(nom_client, 0) + string_to_float(volum)
                    if not routes.get(header):
                        routes[header] = {}
                    item = {nom_client: (route_volumes[nom_client], nom_ciutat, route[0])}
                    routes[header].update(item)
        i = 1
        for route in routes:
            print(route)
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
                    for line in self.customers_re.findall(route[3]):
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
            if int(route[0]) in self.route_tuple:
                for line in self.customers_re.findall(route[3]):
                    town = line[2].strip()
                    towns.add(town)
                routes.update({route[0]: towns})
        return routes

    def dayly(self):
        if week_routes.get(wd):
            self.dispatch(week_routes[wd])
        else:
            raise KeyError('Today you must to take a pause.')


if __name__ == '__main__':
    r"""
    Llegim un fitxer de C:\Users\<USERNAME>\Downloads\Volumen Rutas.txt
    El reanomenem a C:\Users\<USERNAME>\OneDrive\scripts\data\berlys\<YEAR>\<MONTH>\Volumen Rutas <TOMORROW:%Y-%m-%d>.txt
    
    Si no existeix el fitxer C:\Users\<USERNAME>\Downloads\Volumen Rutas.txt és perque
    ja s'ha reanomenat i hem de llegir el darrer fitxer mogut a la carpeta
     C:\Users\<USERNAME>\OneDrive\scripts\data\berlys\<YEAR>\<MONTH>\
    amb el format "Volumen Rutas %Y/%m/%d.txt" que contindrà les dades que ens interessen.
    """
    set_local_env(time_cat, 'Catalan_Andorra.UTF-8')
    date = DateHandler()
    if 18 < date.get_hour() < 24:
        date.tomorrow()
    wd = date.get_weekday()

    source = FileSource()
    route = Route()
    week_routes = {
        'dl.': (680, 681),
        'dt.': (680, 681),
        'dc.': (680, 681),
        'dj.': (680,),
        'dv.': (680, 688),
        'ds.': (680, 682, 688),
    }

    argparser = argparser()
    argparser.add_argument('-a', '--all', dest='all', action='store_true')
    argparser.add_argument('-d', dest='dayly', action='store_true')
    argparser.add_argument('-g', dest='mail', action='store_true')
    argparser.add_argument('-r', dest='routelist', type=int, nargs='+')
    argparser.add_argument('-w', dest='weekdays', action='store_true')
    args = argparser.parse_args()

    if args.mail:
        source.download_source()

    if args.dayly:
        source.init()
        source.run()
        route.dayly()

    elif args.routelist:
        source.init()
        source.run()
        route.dispatch(args.routelist)

    elif args.all:
        source.init()
        source.run()
        route.dispatch(route.route_tuple)

    if args.weekdays:
        directory = DirSource()
        directory.routes_by_weekday()
