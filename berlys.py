# -*- coding: utf-8 -*-
#! c:\python\python3
import os
import re
from datetime import datetime, timedelta
from re import search
from pathlib import Path as path
from locale import setlocale as set_local_env, LC_TIME as time_cat

from core import DateHandler


class FileSource:
    def __init__(self):
        #Java Style Constructor
        self.root = ''
        self.destination = ''
        self.absolute_path_filename = ''
        self.original_filename = ''
        self.filename = ''
        self.lines = ''

    #Java Style setters
    def set_root(self, root):
        if isinstance(root, tuple):
            path = os.path.join(*root)
        self.root = path

    def set_destination(self, *path, date_path = '', reset=False):
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

    #Methods
    def move(self):
        if not os.path.exists(self.destination):
            os.makedirs(self.destination)
        fname = datetime.strftime(tomorrow, '%Y-%m-%d.txt')
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

class Route:

    routes = (678, 679, 680, 681, 682, 692, 696)

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
        self.items = re.compile(r"(?P<code>\d{10}) (?P<customer>.{35}) (?P<town>.{20}) (?P<ordnum>.{10}) (?P<vol>.{11})(?: (?P<UM>.{2,3}))?")
        self.lines = []

    def standard(self):
        for route in self.routes_re.findall(self.lines):
            if int(route[0]) in (678, 681, 686):
                print (f"{route[0]}\t{route[1]}\t{route[2]}\t{route[4]}\t{route[5]}\t{route[6]}\t{route[7]}")
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
        for route in self.routes_re.findall(source.lines):
            if int(route[0]) in route_ids:
                print (f"{route[0]}")
                for line in self.items.findall(route[3]):
                    nom_client = line[1].strip()
                    nom_ciutat = line[2].strip()
                    volum = line[4].strip()
                    print (f"{nom_client}\t{volum}\tPVL\t({nom_ciutat})")
                print
                
    def write(self, route_ids=(680,), fname='rutes.txt'):
        with open(fname, 'w', encoding='utf8') as f:
            for route in self.routes_re.findall(source.lines):
                if int(route[0]) in route_ids:
                    print (f"{route[0]}")
                    for line in self.items.findall(route[3]):
                        nom_client = line[1].strip()
                        nom_ciutat = line[2].strip()
                        volum = line[4].strip()
                        l = f"{nom_client}\t{volum}\tPVL\t({nom_ciutat})"
                        print (l)
                        f.write(l+'\n')
                    print
                

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
    date.tomorrow()
    wd = date.get_weekday()

    source = FileSource()
    source.set_root((path.home(), 'Downloads'))
    source.set_destination(
        path.cwd(),
        'dades',
        'Berlys',
        date_path = datetime.strftime(date.to_date(), '%Y$s%m'.replace('$s', os.path.sep)),
        reset=True
    )
    source.set_original_filename(r'Volumen Rutas.txt')
    source.set_absolute_path_filename()
    source.run()

    route = Route()
    week_routes = {
        'dl.': (680, 681),
        'dt.': (678, 679, 681, 696),
        'dc.': (678, 679, 681),
        'dj.': (680, 681),
        'dv.': (678, 679, 681),
        'ds.': (679, 681)
    }
    route.routing(week_routes[wd])