import socket
import os
import math
import hashlib
import threading
import queue
import time
cola = queue.Queue()


class Variables:
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
    Variables.sock.listen(25)


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


def send_receive_hash_validation(num, conn, col):
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
    def __init__(self, num, conn, col):
        threading.Thread.__init__(self)
        self.num = num
        self.conn = conn
        self.col = col

    def run(self):
        send_receive_hash_validation(self.num, self.conn, self.col)


def start_server():
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
                t = Thread(numero, conn, cola)
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

