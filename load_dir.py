import os
import re
import redis
# permite interactuar con elementos de una pagina web
from bs4 import BeautifulSoup # extrae info en formato html/xml

# conexión tipo locar con la base de datos redis
r = redis.StrictRedis(host='localhost', port=6379, db=0)

# carga los libros (.html) en redis, y utiliza el ID como key
# directorio del html
def load_dir(path):
    files = os.listdir(path) # lista de archivos del diccionario
    print(files)
    
    #filtrar los archivos
    for f in files:
        # verifica el patrón de la ruta especificada con la expresión regular
        match = re.match(r"^book(\d+).html$", f) 
        
        if match is not None:
            with open(path + f) as file: # abre el archivo html
                html = file.read() # lee el archivo
                book_id = match.group(1)  # asigna el valor de su identificador
                # #llama al metodo create_index y le pasa los parametros
                create_index(book_id, html)
                r.set(book_id, html) # almacena el valor de ID como clave en redis 
                # mensaje de confirmación de la carga de libros
                print(f"{file} loaded into Redis")
        
# índice de palabras de los html (libros)
def create_index(book_id, html):
    # crea un objeto que contiene la estructura del html
    soup = BeautifulSoup(html, 'html.parser')
    palabras = str(soup.p).lower() #obtiene el contenido de <p></p> y lo convierte a minusculas
    claves = palabras.split() # divide las palabras por espacios 
    
    for clave in claves:
        clave = clave.replace(",","") #reemplaza/borra las comas del final de la palabra
        r.sadd(clave,book_id) #t es el conjunto y sadd permite agregar id al conjunto

load_dir("html/books/") # ejecución del método para cargar los html(libros)