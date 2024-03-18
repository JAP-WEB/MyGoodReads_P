from functools import cached_property
from http.cookies import SimpleCookie #se importa libreria
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import urllib.parse
import re #importar libreria
import redis
import uuid
import os

# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html

mappings = [
    (r"^/books/(?P<book_id>\d+)$", "get_book"),
    (r"^/book/(?P<book_id>\d+)$", "get_book"),
    (r"^/$","index"),
    (r"^/search$","search"),
    ]
    
#objeto
r = redis.StrictRedis(host = "localhost", port = 6379, db =0)

class WebRequestHandler(BaseHTTPRequestHandler):
    def search(self):
        if self.query_data and 'q' in self.query_data:
            query = self.query_data['q']
            booksB = r.sinter(query.split(' '))
            lista = []
            for b in booksB:
                y = b.decode()
                lista.append(y)
                print(lista)

            for i in range(0, len(lista)):
                if i<len(lista):
                    self.get_book(lista[i])
                else:
                    self.index()              

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def cookies(self):
        return SimpleCookie(self.headers.get("Cookie"))
    
    def get_method(self, path):
        for pattern, method in mappings:
            match = re.match(pattern, path)
            if match:
                return (method, match.groupdict())
                
    def get_session(self):
        #corregir el posible error de cookies y evaluar si el error existe
        cookies = self.cookies()
        session_id = None #se inicializa en nulo
        if not cookies:
            print("No existen cookies")
            cookies = SimpleCookie()
            session_id = uuid.uuid4()
        else:
             #evalua si el error existe
            session_id = cookies["session_id"].value
        return session_id #regresa la sesion
        
    # metodo que regrese la cookie
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie()
        cookies["session_id"] = session_id
        cookies["session_id"]["max-age"] = 1000 #tiempo de espera
        self.send_header("Set-Cookie", cookies.output(header = ""))
        
    def do_GET(self):
        method = self.get_method(self.url.path)
        if method:
            method_name, dict_params = method
            method = getattr(self, method_name)
            method(**dict_params)
            return
        else:
            self.send_error(404, "Not Found")

    """        
    def do_GET(self):
        self.url_mapping_response()
        
    def url_mapping_response(self):
        for (pattern, method) in mappings:
            match = self.get_params(pattern, self.path)
            print(match)
            if match is not None:
                md = getattr(self,method)
                md(**match)
                return
            
        self.send_response(404)
        self.end_headers()
        self.wfile.write("Not Found".encode("utf-8"))
    """
    
    def get_params(self, pattern, path):
        match = re.match(pattern, path)
        if match:
            return match.groupdict()
    
    def index(self):
        session_id = self.get_session()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        self.end_headers()
        with open('html/index.html') as f:
            response = f.read()
        self.wfile.write(response.encode("utf-8"))
        #self.send_response(200)
        #self.send_header("Content-Type", "text/html")
        #self.end_headers()
        #index_page = """
        #<body style="background-color:#FAE5D3"></body>
        #<h1 style="color: #20B2AA">Bienvenidos a la biblioteca!</h1>
        #<form action="/search" method="GET">
        #    <label for="q" style="color: #20B2AA;">Search:</label>
        #    <input type="text" name="q" style="background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc; border-radius: 5px;">
        #    <input type="submit" value="Buscar libros" style="background-color: #20B2AA; color: white; padding: 5px 10px; border: none; border-radius: 5px;">
        #</form>
        #""".encode("utf-8")
        #self.wfile.write(index_page)
        
    def get_book(self, book_id):
        session_id = self.get_session()
        get_recomendation = self.get_recomendation(session_id, book_id)
        #r.lpush(f"session:{session_id}", f"book:{book_id}")
        indice = r.get(book_id)
        if indice:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")        
            
            self.write_session_cookie(session_id)
            self.end_headers()
            response = f"""
            {indice.decode()}
        <p> ID-session: {session_id} </p>
        <p> Te recomendamos leer: {get_recomendation} </p>
        """
            self.wfile.write(response.encode("utf-8"))
        else:
            self.send_error(404, "Not found")
            
        """    
        #redis
        #r.lpush(f"session:{session_id}", f"book:{book_id}")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        #antes de end headers se escribe el header de la cookie
        self.end_headers()
        #book_info = f"<h1> Info de Libro {book_id} es correcto </h1>".encode("utf-8")
        book_info = r.get(f"book:{book_id}") or "<h1> No existe el libro </h1>"
        #book_info = book_info + b"Session Id:{session_id}".encode("utf-8")
        self.wfile.write(str(book_info).encode("utf-8"))
        self.wfile.write(f"Session:{session_id}".encode("utf-8"))

        book_list = r.lrange(f"session:{session_id}", 0, -1)
        for book in book_list:
            self.wfile.write(f"   Book:{book}".encode("utf-8"))
        """
    
    def get_recomendation(self,session_id,book_id):
        r.rpush(session_id,book_id)
        books = r.lrange(session_id,0 ,6)
        print(session_id,books)
        
        library = [str(i+1) for i in range(6)]
        recomendation = [book for book in library if book not in
                        [read.decode() for read in books]]
        
        if len(recomendation) > 3:  # Cambiamos la condición a > 3 para que recomiende después del segundo
            return recomendation[2]  # Devolvemos el tercer libro de la lista de recomendaciones
        elif len(recomendation) > 0:
            return recomendation[0]
        else:
            return "No te puedo recomendar nada"
        
    @property
    def url(self):
        return urlparse(self.path)

    @property
    def query_data(self):
        return dict(parse_qsl(self.url.query))

    def get_response(self):
        return f"""
    <h1> Hola Web </h1>
    <p>  {self.path}         </p>
    <p>  {self.headers}      </p>
    <p>  {self.query_data}   </p>
"""
#(se llamo al metodo en self.get_params)
if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()