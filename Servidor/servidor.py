import socket
import os
import math
import hashlib


class GLOBALES:
    cantidadClientesListos = 0
    cantidadClientesEnviar = 0
    clientesListos = False

    HOST = '127.0.0.1'
    PORT = 65432
    sock = None
    CHUNK_SIZE = 1024
    fragmentsQuantity = 0
    MCAST_GRP = '224.1.1.1'
    MCAST_PORT = 5007

    path_file = None
    sizeFile = 0
    fileName = ""
    archivoEnviado = False


def send_config():
    # regarding socket.IP_MULTICAST_TTL
    # ---------------------------------
    # for all packets sent, after two hops on the network the packet will not
    # be re-sent/broadcast (see https://www.tldp.org/HOWTO/Multicast-HOWTO-6.html)
    MULTICAST_TTL = 2
    GLOBALES.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    GLOBALES.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)


def send(data):
    GLOBALES.sock.sendto(data, (GLOBALES.MCAST_GRP, GLOBALES.MCAST_PORT))


def receive_config():
    GLOBALES.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    GLOBALES.sock.bind((GLOBALES.HOST, GLOBALES.PORT))
    GLOBALES.sock.listen()


def receive(conn, chunk_size):
    return conn.recv(chunk_size)


def server_config():
    eligio = False
    while eligio is not True:
        print("Ingrese el número del archivo que desea enviar: ")
        print("1. Datos.txt")
        print("2. Libro.epub")
        archivo = int(input(""))
        if archivo == 1:
            GLOBALES.path_file = './archivos/Datos.txt'
            GLOBALES.sizeFile = (os.path.getsize('./archivos/Datos.txt'))
            GLOBALES.fileName = "Datos.txt"
            eligio = True
        elif archivo == 2:
            GLOBALES.path_file = './archivos/Libro.epub'
            GLOBALES.sizeFile = (os.path.getsize('./archivos/Libro.epub'))
            GLOBALES.fileName = "Libro.epub"
            eligio = True
        else:
            print("No existe ese archivo")
    GLOBALES.cantidadClientesEnviar = int(input("Ingrese a cuantos clientes en simultaneo desea enviar el archivo \n"))

    GLOBALES.fragmentsQuantity = math.ceil(GLOBALES.sizeFile / 65000)
    GLOBALES.CHUNK_SIZE = math.ceil(GLOBALES.sizeFile / GLOBALES.fragmentsQuantity)


def iniciar_server():
    receive_config()
    configurar = True
    while True:
        if GLOBALES.clientesListos is False:
            if configurar:
                server_config()
                configurar = False
            print("Recibiendo Conexiones")
            conn, addr = GLOBALES.sock.accept()
            data = receive(conn, 2048)
            if data == b'ready':
                GLOBALES.cantidadClientesListos += 1
            if GLOBALES.cantidadClientesEnviar == GLOBALES.cantidadClientesListos:
                GLOBALES.clientesListos = True
                print("Clientes listos")
        elif GLOBALES.archivoEnviado is False:
            print("Listo para transmitir")
            send_config()
            send(str('fileName:' + GLOBALES.fileName + ' fragmentos:' + str(GLOBALES.fragmentsQuantity)).encode('utf-8'))

            i = 0
            with open(GLOBALES.path_file, "rb") as file:
                data = file.read(GLOBALES.CHUNK_SIZE)
                print("Enviando")
                while data:
                    i += 1
                    send(data)
                    data = file.read(GLOBALES.CHUNK_SIZE)
                GLOBALES.archivoEnviado = True
            print("Paquetes enviados: " + str(i))
        else:
            receive_config()
            conn, addr = GLOBALES.sock.accept()
            data = receive(conn, 2048)
            if b'hash' in data:
                print("Enviando hash")
                with open(GLOBALES.path_file, "rb") as file:
                    hash = b'hash:' + hashlib.sha1(file.read()).digest()
                    send_config()
                    send(hash)
            elif b'envio' in data:
                GLOBALES.cantidadClientesListos -= 1
                if GLOBALES.cantidadClientesListos == 0:
                    GLOBALES.clientesListos = False
                    GLOBALES.archivoEnviado = False
                    configurar = True
                print(data.decode("utf-8"))


iniciar_server()

