from functools import cached_property
from http.cookies import SimpleCookie # creación y manejo de cookies HTTP
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import urllib.parse # división y creación de URL en base a los componentes
import re # importar libreria expresiones regulares
import redis # conexión con base de datos REDIS
import uuid # #manipula los UUID - identificadores únicos universales
import os # comuincación con el sistema operativo


#----------------------------------------------------------#
# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html
#----------------------------------------------------------#

#>>>>>>>>>Expresiones regulares<<<<<<<<<<
# ^ coincide con el comienzo de la cadena 
# $ final de la cadena
# ?P<> valida la referencia de la cadena de acuerdo al identificador
# \d+ coindide con un número con decimales

# Definición de tuplas de mapeo, patrón de URL y llamada a la función 
mappings = [
    (r"^/books/(?P<book_id>\d+)$", "get_book"),
    (r"^/book/(?P<book_id>\d+)$", "get_book"),
    (r"^/$","index"),
    (r"^/search$","search"),
    ]
    
# Conexión tipo local con la base de datos Redis
# db = número de base de datos en la cual se hará la conexión
r = redis.StrictRedis(host = "localhost", port = 6379, db =0)

# Declaración de clase, hereda propiedades de módulo BaseHTTPRequestHandler 
class WebRequestHandler(BaseHTTPRequestHandler):
    
    # Declaración de función para las solicitudes de búsqueda 
    def search(self):
        #verificación que se haya mandado una búsqueda 
        #'q' es donde se almacena la consulta de búsqueda
        if self.query_data and 'q' in self.query_data:
            query = self.query_data['q']
            #busca en redis las palabras de manera indivual 'split'
            #sinter: devuelve los miembros del conjunto resultante de la intersección dada
            books = r.sinter(query.split(' ')) #busca libros que tengan las palabras consultadas
            lista_libros = [] # declaración de lista
            
            for b in books:  # iteración para crear una lista de libros encontrados
                cadena = b.decode() # decodificar la cadena
                lista_libros.append(cadena) # agregar a lista
                print(lista_libros)

            for i in range(0, len(lista_libros)):  # mostrar resultados de búsqueda de libros
                if i<len(lista_libros):
                    self.get_book(lista_libros[i])
                else:
                    self.index()              
        
        # respuesta HTTP 
        self.send_response(200) # estado de éxito
        self.send_header('Content-type', 'text/html') # cabeceras de contenido
        self.end_headers()

    def cookies(self):  # función para tomar las cookies de las cabeceras de HTTP   
        return SimpleCookie(self.headers.get("Cookie"))
    
    def get_method(self, path):
        # iteración de la ruta y el metodo en mappings
        for pattern, method in mappings:
            # valida la ruta con la expresión regular 
            match = re.match(pattern, path) 
            if match:
                # devuelve el metodo y un diccionario de rutas coincidentes
                return (method, match.groupdict())
                
    def get_session(self):
        cookies = self.cookies() #obtener las cookies 
        session_id = None #se inicializa en nulo
        if not cookies:
            print("No existen cookies")
            cookies = SimpleCookie()
            session_id = uuid.uuid4() # genera un identificador aleatorio
        else:
            # obtiene el valor de la cookie ya registrado
            session_id = cookies["session_id"].value
        return session_id # regresa id de la sesion
        
    # establecer cookies a la sesión actual   
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie() #crea un objeto del tipo SimpleCookie
        cookies["session_id"] = session_id #establece cookie a sesión actual
        cookies["session_id"]["max-age"] = 1000 #tiempo de expiración de cookie
        #envia la cookie como header
        self.send_header("Set-Cookie", cookies.output(header = ""))
        
    # Funcion GET que solicita al servidor que te de la informacion al abrir el navegador 
    # obtiene el metodo que se esta solicitando, tomando el path de la URL como argumento
    # Obtiene el nombre del metodo y lo llama pasando los parametros del diccionario. 
    def do_GET(self):
        method = self.get_method(self.url.path)
        if method:  # Verifica si encuentra el metodo
            method_name, dict_params = method
            method = getattr(self, method_name)
            method(**dict_params) # ** = expande los argumentos del diccionario
            return
        else:
            # si no se encontro ningun metodo, el servidor manda error 404
            self.send_error(404, "Not Found")
    
    def index(self):
        # obtener el session_id llamando a la función get_session
        session_id = self.get_session()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id) # llama a la función 
        self.end_headers()
        #abre el archivo index.html
        with open('html/index.html') as f:
            response = f.read()
        self.wfile.write(response.encode("utf-8"))
        
    def get_book(self, book_id):
        # obtiene el session_id llamando al la función get_session
        session_id = self.get_session()
        # obtiene la recomendación llamando al la función get_recomendation
        get_recomendation = self.get_recomendation(session_id, book_id)
        # crea una pagina con el libro de acuerdo al book_id obtenido de redis
        pagina = r.get(book_id)
        if pagina:
            self.send_response(200) # Despliegue de la pagina
            self.send_header("Content-Type", "text/html")        
            
            self.write_session_cookie(session_id) # escribe las cookies de la sesión
            self.end_headers()
            #despliegue de datos de sesión y recomendaciones
            response = f"""
            {pagina.decode()}
            <p> ID-session: {session_id} </p>
            <p> Te recomendamos leer: {get_recomendation} </p>
            """
            self.wfile.write(response.encode("utf-8"))
        else:
            # mensaje de error en caso de que no exista libro
            self.send_error(404, "Not found")
    
    # Recomendacion de libros donde se agrega un libro a una lista de libros
    # asociados a una sesion especifica. 
    # Obtiene lista de libros asociados a la sesion, limitando el rango de libros
    def get_recomendation(self,session_id,book_id):
        r.rpush(session_id,book_id)
        books = r.lrange(session_id,0 ,6)
        print(session_id,books)
        library = [str(i+1) for i in range(6)] # crea etiquetas de libros (str-cadenas)
        
        # crea lista de recs, revisa los libros leidos, sino los agrega a lista de recs
        recomendation = [book for book in library if book not in
                        [read.decode() for read in books]]
        # Recomienda despues del segundo libro, devolviendo la rec del 3
        if len(recomendation) > 3:  
            return recomendation[2] 
        # Si hay al menos 1 libro en recs, devolver el 1er libro de la lista
        elif len(recomendation) > 0:
            return recomendation[0]
        else:
            return "No te puedo recomendar nada" # No quedan libros en la lista
        
    @property # definir a la función como propiedad de la clase
    #self: objeto de la clase
    def url(self):
        # divide el URL y devuelve un objeto con el resultado
        return urlparse(self.path)

    @property
    def query_data(self):
        # devuelve los parametros de la cadena URL de consulta en un diccionario
        return dict(parse_qsl(self.url.query))

if __name__ == "__main__":
    print("Server starting...")
    #comunicación con IP y puerto 8000
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()