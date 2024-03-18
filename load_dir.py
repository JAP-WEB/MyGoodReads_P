import os
import re
import redis
from bs4 import BeautifulSoup #importar libreria

r = redis.StrictRedis(host='localhost', port=6379, db=0)

def load_dir(path):
    #cargar el directorio
    files = os.listdir(path)
    print(files)
    #filtrar los archivos
    for f in files:
        match = re.match(r"^book(\d+).html$", f)
        if match is not None:
            with open(path + f) as file:
                html = file.read()
                book_id = match.group(1)
                #llamar a metodo
                create_index(book_id, html)
                r.set(book_id, html)
                print(f"{file} loaded into Redis")
        
#Metodo que toma el book_id y el doc html
#crea un diccionario que descompone el doc
def create_index(book_id, html):
    #se hace la sopa
    soup = BeautifulSoup(html, 'html.parser')
    #asignar el texto del doc html a variable, se separa
    ts = str(soup.p).lower()
    palabras = ts.split()
    #para cada termino en palabras guardar t y su book_id
    for t in palabras:
        t = t.replace(",","")
        r.sadd(t,book_id) #t es el conjunto y sadd permite agregar conjunto

load_dir("html/books/")