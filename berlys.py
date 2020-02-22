# -*- coding: utf-8 -*-
# ! c:\python\python3

"""
    Programa que imprimeix per pantalla les rutes assignades al repartidor o totes les assignades a l'empressa.

    L'opció manual -d carrega el fitxer anomenat "Volumen Rutas.txt" de la carpeta de descàrregues ../../../Downloads
    que s'haurà descarregat prèviament des del navegador consultant el correu electrònic manualment. Aleshores obtenim
    les dades i reanomenem el fitxer a la carpeta amb el nom: "<DATA REPARTIMENT>.txt" dins de la carpeta
    d'arxiu anomenada ../../data/<ANY ACTUAL>/<MES ACTUAL>. L'esmentat paràmetre <DATA REPARTIMENT> és la data de
    repartiment, normalment del dia posterior al de la descàrrega del fitxer i <ANY ACTUAL> i <MES ACTUAL> són l'any
    i el mes que els correspon respectivament.

    Si no es troba el fitxer dins de la carpeta de descàrregues, es recerca a la carpeta
    ../../data/<ANY ACTUAL>/<MES ACTUAL> i se n'extrau les dades. Aquí <ANY ACTUAL> i <MES ACTUAL> són l'any i el mes en
    curs. S'han de recòrrer les carpetes fins trobar el fitxer més recent que conté les dades de repartiment.

    Si es passa l'opció -g, descarreguem el fitxer directament del correu a la carpeta pertinent
    ../../data/<ANY ACTUAL>/<MES ACTUAL> i s'aprofiten les dades per a obtindre els clients de la ruta/rutes assignades
     al repartidor o a tota l'empresa depenent si s'ha triat l'opció -r o --all.

    - Amb l'opció -r [r1 [r2 ][...]] especifiquem quines rutes mostrar, seran les rutes assignades a un repartidor.
    - L'opció --all mostrarà totes les rutes assignades a l'empresa.

    Segons el dia de la setmana hi ha unes rutes assignades per defecte al repartidor de manera que amb l'opció -d es
    pot utilitzar sense especificar rutes (opció -r).
"""

import json
import os
import re

from argparse import ArgumentParser as argparser
from locale import atof as string_to_float, format_string as local_env_fmt
from pathlib import Path as path

from Berlys.getmail import GetMail
from Berlys.filename_handler import FilenameHandler
from core import DateHandler, Internationalization


class DirSource:
    """
        L'objectiu d'esta classe és diferent a la del projecte principal (i inicial).
        Ací el que s'obté són els pobles visitats per cada ruta segons el dia de la setmana
        corresponent, ja que una mateixa ruta (R696) s'utilitza per a un sector determinat
        segons el dia de la setmana.

        Per exemple:
        - R696 dilluns, dimecres i divendres és per a Orpesa
        - R696 dimarts, dijous i dissabte és per a Sagunt.
    """
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
                with open(item.absolute(), 'r', encoding=_encoding) as file:
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
        self.root = r"..\..\data\berlys\data"
        print(self.root)
        self.run()


class FileSource:
    """
    Representa el fitxer d'on s'extrau l'informació de les rutes assignades a totes les empreses.

    La seua funció és carregar el fitxer, llegir-lo i escriure'l a la carpeta corresponent.

    Podem descarregar del correu electrònic els fitxers adjunts tant de les rutes com altres fitxers
    que aleshores s'emmagatzemen a la carpeta ../../data/attachments i no seran tractats.
    """
    def __init__(self):
        self.filename_handler = FilenameHandler()
        self.content = ''

    def get_delivery_date(self) -> DateHandler:
        print (self.content)
        match = re.search(r'(?P<date>\d{2}(\.)\d{2}\.\d{4})', self.content)
        return DateHandler(match.group('date'))

    def move(self):
        old_fh = FilenameHandler()
        new_fh = FilenameHandler()
        old_filename = old_fh.from_download_dir()
        dlv_date = self.get_delivery_date()
        new_filename = new_fh.to_data_dir(dlv_date)

        if not os.path.exists(new_fh.path):
            os.makedirs(new_fh.path)
        if not os.path.exists(new_filename):
            os.rename(old_filename, new_filename)

    def set_content(self, filename):
        with open(filename, 'r', encoding=_encoding) as f:
            self.content = f.read()

    def run(self):
        filename = self.filename_handler.from_download_dir()
        if os.path.exists(filename):
            self.set_content(filename)
            self.move()
        else:
            filename = self.filename_handler.from_data_dir()
            self.set_content(filename)

    def download_source(self):
        gmail = GetMail()
        gmail.login()
        gmail.dispatch()
        self.content = gmail.last_data
        gmail.close()


class Route:
    """
        Obtenim les rutes i els clients a visitar mitjançant expressions regulars.
    """

    # Rutes per defecte assignades a l'empresa.
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
            r"(?P<customer_id>\d{10}) (?P<customer>.{35}) (?P<town>.{20}) "
            r"(?P<ordnum>.{10}) (?P<vol>.{11})(?: (?P<UM>.{2,3}))?"
        )

    def dispatch(self, route_ids=(680,)):
        route_volumes = {}
        routes = {}
        for route in self.routes_re.findall(source.content):
            if int(route[0]) in route_ids:
                header = f"{route[2]}\t{route[0]}\t{route[1].lstrip('25 ')}"
                for line in self.customers_re.findall(route[3]):
                    customer_name = line[1].strip()
                    town_name = line[2].strip()
                    volume = line[4].strip()
                    route_volumes[customer_name] = route_volumes.get(customer_name, 0) + string_to_float(volume)
                    if not routes.get(header):
                        routes[header] = {}
                    item = {customer_name: (route_volumes[customer_name], town_name, route[0])}
                    routes[header].update(item)
        i = 1
        volume = 0.0
        for route in routes:
            print(route)
            route_pvl = 0
            for customer in routes[route]:
                customer_volume = routes[route][customer][0]
                volume += customer_volume
                route_pvl += customer_volume
                print(f'{i}\t\t{customer}\t{local_env_fmt("%.3f", customer_volume)}\t{routes[route][customer][1]}')
                i += 1
            print(f'\t\troute vol. total:\t\t{local_env_fmt("%.3f", route_pvl)}')
        print(f'\t\tall routes vol. total:\t{local_env_fmt("%.3f", volume)}')

    def daily(self):
        # Mètode per a un repartidor que treballa amb les mateixes rutes segons el dia de la setmana
        # se li assignen unes o altres.

        if week_routes.get(wd):
            self.dispatch(week_routes[wd])
        else:
            raise KeyError('Today you must to take a pause.')

    def fetch_towns(self, text) -> dict:
        # Ací pretenem obtindre el número de localitats que té cada ruta.
        # Este mètode no correspon al projecte principal.
        # S'utilitza amb l'objecte DirSource que recorre tots els fitxers
        # amb l'objectiu de saber a quines localitats es visiten segons
        # el dia de la setmana.
        routes = dict()
        for route in self.routes_re.findall(text):
            towns = set()
            if int(route[0]) in self.route_tuple:
                for line in self.customers_re.findall(route[3]):
                    town = line[2].strip()
                    towns.add(town)
                routes.update({route[0]: towns})
        return routes


if __name__ == '__main__':
    r"""
    Llegim un fitxer de C:\Users\<USERNAME>\Downloads\Volumen Rutas.txt
    El reanomenem a C:\Users\<USERNAME>\OneDrive\scripts\data\berlys\<YEAR>\<MONTH>\<TOMORROW:%Y-%m-%d>.txt
    
    Si no existeix el fitxer C:\Users\<USERNAME>\Downloads\Volumen Rutas.txt és perque
    ja s'ha reanomenat i hem de llegir el darrer fitxer mogut a la carpeta
     C:\Users\<USERNAME>\OneDrive\scripts\data\berlys\<YEAR>\<MONTH>\
    amb el format "%Y/%m/%d.txt" que contindrà les dades que ens interessen.
    """
    intl = Internationalization()
    intl.init()
    intl.set_local_time('Catalan')

    date = DateHandler()
    if 18 < date.get_hour() < 24:
        date.tomorrow()
    wd = date.get_weekday()

    source = FileSource()
    route = Route()
    # Rutes per defecte assignades a un repartidor
    # segons el dia de la setmana.
    week_routes = {
        'dl.': (680, 681),
        'dt.': (680, 681),
        'dc.': (680, 681),
        'dj.': (680,),
        'dv.': (680, 681),
        'ds.': (680, 682, 688),
    }

    argparser = argparser()
    argparser.add_argument('-a', '--all', dest='all', action='store_true')
    argparser.add_argument('-d', dest='daily', action='store_true')
    argparser.add_argument('-g', dest='mail', action='store_true')
    argparser.add_argument('-m', dest='mailwithlist', type=int, nargs='+')
    argparser.add_argument('-r', dest='routelist', type=int, nargs='+')
    argparser.add_argument('-w', dest='weekdays', action='store_true')
    args = argparser.parse_args()

    _encoding = 'utf-8'

    if args.mail:
        source.download_source()

    if args.mailwithlist:
        source.download_source()
        route.dispatch(args.mailwithlist)

    if args.daily:
        source.run()
        route.daily()

    elif args.routelist:
        source.run()
        route.dispatch(args.routelist)

    elif args.all:
        source.run()
        route.dispatch(route.route_tuple)

    if args.weekdays:
        directory = DirSource()
        directory.routes_by_weekday()
