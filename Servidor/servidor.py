import socket
import os
import math
import hashlib


class Variables:
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
    file_sent = False


def send_config():
    # regarding socket.IP_MULTICAST_TTL
    # ---------------------------------
    # for all packets sent, after two hops on the network the packet will not
    # be re-sent/broadcast (see https://www.tldp.org/HOWTO/Multicast-HOWTO-6.html)
    MULTICAST_TTL = 2
    Variables.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    Variables.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)


def send(data):
    Variables.sock.sendto(data, (Variables.MCAST_GRP, Variables.MCAST_PORT))


def receive_config():
    Variables.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    Variables.sock.bind((Variables.HOST, Variables.PORT))
    Variables.sock.listen()


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


def start_server():
    receive_config()
    configurar = True
    while True:
        if Variables.clientesListos is False:
            if configurar:
                server_config()
                configurar = False
            print("Recibiendo Conexiones")
            conn, addr = Variables.sock.accept()
            data = receive(conn, 2048)
            if data == b'ready':
                Variables.cantidadClientesListos += 1
            if Variables.cantidadClientesEnviar == Variables.cantidadClientesListos:
                Variables.clientesListos = True
                print("Clientes listos")
        elif Variables.file_sent is False:
            send_config()
            send(str('fileName:' + Variables.fileName + ' fragmentos:' + str(Variables.fragmentsQuantity)).encode('utf-8'))

            i = 0
            with open(Variables.path_file, "rb") as file:
                data = file.read(Variables.CHUNK_SIZE)
                print("Enviando...")
                while data:
                    i += 1
                    send(data)
                    data = file.read(Variables.CHUNK_SIZE)
                Variables.file_sent = True
            print("Paquetes enviados: " + str(i))
        else:
            receive_config()
            conn, addr = Variables.sock.accept()
            data = receive(conn, 2048)
            if b'hash' in data:
                print("Enviando hash")
                with open(Variables.path_file, "rb") as file:
                    hash = b'hash:' + hashlib.sha1(file.read()).digest()
                    send_config()
                    send(hash)
            elif b'envio' in data:
                Variables.cantidadClientesListos -= 1
                if Variables.cantidadClientesListos == 0:
                    Variables.clientesListos = False
                    Variables.file_sent = False
                    configurar = True
                print(data.decode("utf-8"))


start_server()

