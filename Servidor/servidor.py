import socket
import os
import math
import hashlib
import threading
import queue
import time
# Cola Utilizada para almacenar las respuesta de la verificación del hash proveniente de los clientes.
cola = queue.Queue()


class Variables:
    """ Clase que almacena las variables globales del servidor."""
    cantidadClientesListos = 0
    cantidadClientesEnviar = 0
    clientesListos = False

    HOST = '127.0.0.1'
    PORT = 65432
    HOST_CLIENT = ''
    PORT_CLIENT = 0
    set_up = True

    sock = None
    CHUNK_SIZE = 1024
    fragmentsQuantity = 0
    MCAST_GRP = '224.1.1.1'
    MCAST_PORT = 5007

    path_file = None
    sizeFile = 0
    fileName = ""
    file_sent = False

    indexLogs = 1
    fileLogs = None


def send_config():
    """ Configura el socket para el envio de paquetes."""
    MULTICAST_TTL = 255
    Variables.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    Variables.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)


def send(data):
    """Envia los datos pasados por parametro al multicast configurado anteriormente.

    Parámetros:
    data -- datos a transmitir

    """
    Variables.sock.sendto(data, (Variables.MCAST_GRP, Variables.MCAST_PORT))


def receive_config():
    """Configura el socket para recibir información de los clientes.

    Puede escuchar maximo 25 conexiones.

    """
    Variables.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    Variables.sock.bind((Variables.HOST, Variables.PORT))
    Variables.sock.listen(25)


def receive(conn, chunk_size):
    """Recibe los datos enviados desde algún cliente.

    Retorna los datos que envio el cliente.

    Parámetros:
    conn -- Socket de comunicación con el cliente.
    chunck_size -- Cantidad de datos que leera del buffer.

    """
    return conn.recv(chunk_size)


def server_config():
    """Configura el servidor.

    Configura que texto se va a enviar, la cantidad de clientes a los cuales se le enviaran los datos simultaneamente
    y la cantidad de fragmentos a enviar.

    """
    eligio = False
    while eligio is not True:
        print("Ingrese el número del archivo que desea enviar: ")
        print("1. Datos.txt")
        print("2. Libro.epub")
        archivo = int(input(""))
        if archivo == 1:
            Variables.path_file = './archivos/Datos.txt'
            Variables.sizeFile = (os.path.getsize('./archivos/Datos.txt'))
            Variables.fileName = "Datos.txt"
            eligio = True
        elif archivo == 2:
            Variables.path_file = './archivos/Libro.epub'
            Variables.sizeFile = (os.path.getsize('./archivos/Libro.epub'))
            Variables.fileName = "Libro.epub"
            eligio = True
        else:
            print("No existe ese archivo")
    Variables.cantidadClientesEnviar = int(input("Ingrese a cuantos clientes en simultaneo desea enviar el archivo \n"))

    Variables.fragmentsQuantity = math.ceil(Variables.sizeFile / 65000)
    Variables.CHUNK_SIZE = math.ceil(Variables.sizeFile / Variables.fragmentsQuantity)


def send_receive_hash_validation(conn, col):
    """Envia el hash del archivo al cliente y recibe la respuesta del mismo.

    Parámetros:
    conn -- Socket de comunicación con el cliente.
    col -- cola dónde se almacena la respuesta del cliente.

    """
    i = 0
    while i < 15:
        data = receive(conn, 2048)
        if b'hash' in data:
            with open(Variables.path_file, "rb") as file:
                hash = b'hash:' + hashlib.sha1(file.read()).digest()
                conn.sendall(hash)
        elif b'envio' in data:
            col.put(data)
        i += 1


class Thread(threading.Thread):
    """ Clase utilizada para la creación de los Threads."""

    def __init__(self, conn, col):
        """Configura el Thread que se va a lanzar.

        Parámetros:
        conn -- Socket de comunicación con el cliente.
        col -- cola dónde se almacena la respuesta del cliente.

        """
        threading.Thread.__init__(self)
        self.conn = conn
        self.col = col

    def run(self):
        """ Lanza el Thread. """
        send_receive_hash_validation(self.conn, self.col)


def start_server():
    """Inicia el server.

    Empieza recibiendo las conexiones de los clientes.
    Cuando ya los clientes se encuentran listos para recibir se empieza a transmitir el archivo.
    Por último el servidor crea un socket para cada cliente que ha recibido el archivo para hacer la verificación
        del hash. Cuando se hace este proceso con todos los clientes el servidor reinicia la configuración

    """
    receive_config()
    numero = 0
    while True:
        if Variables.clientesListos is False:
            if Variables.set_up:
                server_config()
                Variables.set_up = False
            print("Recibiendo Conexiones")
            conn, addr = Variables.sock.accept()
            data = receive(conn, 2048)
            if data == b'ready':
                Variables.cantidadClientesListos += 1
            if Variables.cantidadClientesEnviar == Variables.cantidadClientesListos:
                Variables.clientesListos = True
        elif Variables.file_sent is False:
            send_config()
            send(str('fileName:' + Variables.fileName + ' fragmentos:'
                     + str(Variables.fragmentsQuantity) + ' sizeFile:'
                 + str(Variables.sizeFile)).encode('utf-8'))

            i = 0
            with open(Variables.path_file, "rb") as file:
                data = file.read(Variables.CHUNK_SIZE)
                print("Enviando...")
                tiempo_inicial = time.time()
                while data:
                    i += 1
                    send(data)
                    data = file.read(Variables.CHUNK_SIZE)
                Variables.file_sent = True
                tiempo_final = time.time()

            # Logs
            Variables.fileLogs = './logs/Log' + str(Variables.indexLogs) + '.txt'
            with open(Variables.fileLogs, "a+") as file:
                file.write('Fecha: ' + time.strftime("%d/%m/%y") + ' Hora: ' + time.strftime("%I:%M:%S"))
                file.write('\nMultiCastGroup: ' + str(Variables.MCAST_GRP)
                           + '  MulticastPort: ' + str(Variables.MCAST_PORT))
                file.write('\nNombre Archivo: ' + Variables.fileName +
                           ' Tamaño: ' + str(Variables.sizeFile/1024) + ' KB')
                file.write('\nTamaño de paquete: ' + str(Variables.CHUNK_SIZE) + ' KB  Paquetes Enviados: ' + str(i))
                file.write('\nTiempo de Transferencia: ' + str(tiempo_final-tiempo_inicial) + ' segundos\n')
                file.write('\nEstado de los Archivos Enviados:')
        else:
            if numero != Variables.cantidadClientesEnviar:
                print("Recibiendo Conexiones para verificación del hash...")
                receive_config()
                conn, addr = Variables.sock.accept()
                numero += 1
                t = Thread(conn, cola)
                t.daemon = True
                t.start()
            if cola.empty() is not True:
                with open(Variables.fileLogs, "a+") as file:
                    file.write('\n  ' + cola.get().decode('utf-8'))
                Variables.cantidadClientesListos -= 1
                if Variables.cantidadClientesListos == 0:
                    with open(Variables.fileLogs, "a+") as file:
                        file.write('\n\n--------------------------------------------\n\n')
                    Variables.cantidadClientesEnviar = 0
                    Variables.clientesListos = False
                    Variables.file_sent = False
                    Variables.set_up = True
                    numero = 0


start_server()

