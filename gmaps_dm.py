#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Adrián López Tejedor <adrianlzt@gmail.com>
#
# Distributed under terms of the GNU GPLv3 license.

"""
TODO:
    - recortar logo de google 22px del pie de cada foto

"""
import argparse
import requests
import sys
from math import ceil,pow
from tqdm import tqdm
from PIL import Image
from io import BytesIO
from functools import wraps
from datetime import datetime

import logging
logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.WARNING)

LOGO_GOOGLE=22 # Pixeles que ocupa el logo de google en la parte inferior de la imagen


def timing_dt(function):
    """
    Calcula el tiempo de ejecuccion de una funcion
    Agrega a la funcion una nueva variable con el valor en segundos
    """
    @wraps(function)
    def wrapper(*args,**kwargs):
        time1 = datetime.now()
        ret = function(*args,**kwargs)
        time2 = datetime.now()
        return ret, (function.__str__(), (time2 - time1))
    return wrapper

def calcula_incrementos(zoom,width,height):
    """
    Segun el zoom que le pasemos, estimamos los grados que debemos movernos en latitud y longitud
    Tambien depende de los px que queramos para height y width

    Retorna incremento para longitud e incremento para latitud
    """
    inc_lng=0.000000669921875*width*pow(2,21-zoom)
    inc_lat=0.0000004725*(height-LOGO_GOOGLE)*pow(2,21-zoom)

    return inc_lng, inc_lat

@timing_dt
def obtiene_imagenes(lat_init, lng_init, lat_fin, lng_fin, zoom=20, width=640, height=640, debug=False):
    if lat_fin > lat_init:
        avance_lat = 1 # Derecha
    else:
        avance_lat = -1 # izquierda

    if lng_fin > lng_init:
        avance_lng = 1 # arriba
    else:
        avance_lng = -1 # abajo

    incremento_lng,incremento_lat = calcula_incrementos(zoom,width,height)

    num_imagenes_lat = int(ceil(abs(lat_fin-lat_init)/incremento_lat))
    num_imagenes_lng = int(ceil(abs(lng_fin-lng_init)/incremento_lng))

    lat=lat_init
    lng=lng_init

    numero_imagenes_total = num_imagenes_lat*num_imagenes_lng
    if numero_imagenes_total > 10:
        ok = raw_input("Se van a generar %s imagenes (%s a lo ancho, %s a lo largo). Seguimos? [S/n] " % (numero_imagenes_total, num_imagenes_lng, num_imagenes_lat))
        if ok == 'n':
            sys.exit(0)

    images = []
    for i in tqdm(range(num_imagenes_lat,0,-1), disable=debug):
        images_lng = []
        for j in tqdm(range(1,num_imagenes_lng+1), disable=debug):
            url = "http://maps.googleapis.com/maps/api/staticmap?center=%s,%s&zoom=%s&scale=false&size=%sx%s&maptype=satellite&format=png&visual_refresh=true" % (lat,lng,zoom,width,height)
            logger.debug("Procesando imagen %s", url)
            req = requests.get(url)
            img = Image.open(BytesIO(req.content))
            if img.mode != 'P':
                logger.error("Nos han echado. Google Maps no nos da mas imagenes")
                sys.exit(1)
            w,h = img.size
            img = img.crop((0,0,w,h-LOGO_GOOGLE))

            images_lng.append(img)
            lng += incremento_lng*avance_lng

        images.append(images_lng)
        lat += incremento_lat*avance_lat
        lng = lng_init

    return images

@timing_dt
def unir_imagenes(imagenes):
    width,height = imagenes[0][0].size
    total_height = len(imagenes) * height
    total_width = len(imagenes[0]) * width
    fullimage = Image.new('RGB', (total_width, total_height))
    logger.info("Creada imagen total con altura %s y anchura %s", total_height, total_width)

    for i,linea in enumerate(imagenes):
        for j,img in enumerate(linea):
            fullimage.paste(img, (j*width,total_height-(i+1)*height))

    return fullimage

@timing_dt
def guardar_imagen(imagen, nombre):
    imagen.save(nombre)

def main():
    parser = argparse.ArgumentParser(prog="GmapsJoiner", description='Download a join satellite images')
    parser.add_argument("-i", "--inicio", action="store", dest="coord_init", help="Coordenadas iniciales. Eg.: 45.1800992,5.7074098", required=True)
    parser.add_argument("-f", "--fin", action="store", dest="coord_fin", help="Coordenadas finales. Eg.: 45.182037,5.712044", required=True)
    parser.add_argument("-z", "--zoom", action="store", dest="zoom", help="Zoom de las imagenes", default=20, type=int)
    parser.add_argument("-w", "--width", action="store", dest="width", help="Ancho de las imagenes en px", default=640, type=int)
    parser.add_argument("-e", "--height", action="store", dest="height", help="Alto de las imagenes en px", default=640, type=int)
    parser.add_argument('-v', '--verbose', dest='verbose', action='count', default=0, help='verbose output. specify twice for debug-level output.')
    args = parser.parse_args()

    if args.verbose > 1:
        logger.setLevel(logging.DEBUG)
    elif args.verbose > 0:
        logger.setLevel(logging.INFO)

    lat_init,lng_init = args.coord_init.split(",")
    lat_fin,lng_fin = args.coord_fin.split(",")

    logger.info("Obteniendo las imagenes...")
    images,time = obtiene_imagenes(float(lat_init), float(lng_init), float(lat_fin), float(lng_fin), zoom=args.zoom, width=args.width, height=args.height, debug=args.verbose>0)
    logger.info("Tiempo en ejecutarse la funcion obtiene_imagenes(): %s", time[1].total_seconds())

    logger.info("Montando las imagenes...")
    fullimage,time = unir_imagenes(images)
    logger.info("Tiempo en ejecutarse la funcion unir_imagenes(): %s", time[1].total_seconds())

    outfile = "output-%s,%s-%s,%s-%s.png" % (lat_init,lng_init,lat_fin,lng_fin,args.zoom)
    x, timing = guardar_imagen(fullimage, outfile)
    logger.info("Tiempo en ejecutarse la funcion guardar_imagen(): %s", time[1].total_seconds())

    # Para separar el mensaje de las barras de tqdm
    if args.verbose == 0:
        print("\n\n")
    print("Imagen guardada en %s" % outfile)

    logger.info("Abriendo imagen generada")
    fullimage.show()

if __name__ == "__main__":
    main()
