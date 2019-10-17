
"""
import socket
import selectors
import types
from tkinter import *
import struct
import threading
import hashlib
import queuecola = queue.Queue()
def procesar():
    return None


raiz = Tk()
raiz.title("Cliente")
raiz.resizable(0, 0)
raiz.geometry("400x200")
estado = StringVar()
estado.set("Estado de la conexión: Desconectado")
estadoEnvio = StringVar()
estadoEnvio.set("Estado del Envio: Desconectado")
textEstado = Label(raiz, textvariable=estado).place(x=10, y=60)
lblEstadoEnvio = Label(raiz, textvariable=estadoEnvio).place(x=10, y=100)


class Thread(threading.Thread):
    def __init__(self, num, col):
        threading.Thread.__init__(self)
        self.num = num
        self.cola = col

    def run(self):
        procesar()
        sys.stdout.write("Hilo %d\n" % self.num)


def enviarNotificacion():
    t = Thread(1, cola)
    t.daemon = True
    t.start()
    estado.set("Estado de la conexión: Listo")
    estadoEnvio.set("Estado del Envio: Recibiendo...")
    botonListo.config(state=DISABLED)


botonListo = Button(raiz, text="Listo", command=enviarNotificacion)
botonListo.config(state=DISABLED)
botonListo.pack(side="bottom")


def ventanaConnect():
    ventanaConnect = Toplevel()
    ventanaConnect.title("Conectarse")
    ventanaConnect.resizable(0, 0)

    def connect():
        GLOBALES.HOST = '127.0.0.1'
        GLOBALES.PORT = 65432
        ventanaConnect.destroy()
        estado.set("Estado de la conexión: Conectado")
        estadoEnvio.set("Estado del Envio: No Recibido")
        botonListo.config(state='normal')
        boton1.config(state=DISABLED)

    host = StringVar()
    port = StringVar()
    hostLabel = Label(ventanaConnect, text="Ingresa el host del servidor").place(x=10, y=10)
    hostEntry = Entry(ventanaConnect, textvariable=host).place(x=180, y=10)
    portLabel = Label(ventanaConnect, text="Ingresa el puerto del servidor").place(x=10, y=40)
    portEntry = Entry(ventanaConnect, textvariable=port).place(x=180, y=40)
    botonConectar = Button(ventanaConnect, text="Conectar", command=connect)
    botonConectar.pack(side="bottom")
    ventanaConnect.geometry("320x100")


boton1 = Button(raiz, text="Conectarse", command=ventanaConnect)
boton1.place(x=10, y=0)
boton1.config(state='normal')

while True:
    raiz.update_idletasks()
    raiz.update()
    if cola.empty() is not True:
        cola.get()
        estado.set("Estado de la conexión: Desconectado")
        estadoEnvio.set("Estado del Envio: Recibido")
        boton1.config(state='normal')"""

import socket
import struct
import hashlib


class GLOBALES:
    MCAST_GRP = '224.1.1.1'
    MCAST_PORT = 5007
    HOST_SERVER = '127.0.0.1'
    PORT_SERVER = 65432
    IS_ALL_GROUPS = True
    sock = None


def sendConfig():
    GLOBALES.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    GLOBALES.sock.connect((GLOBALES.HOST_SERVER, GLOBALES.PORT_SERVER))


def send(data):
    GLOBALES.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    GLOBALES.sock.connect((GLOBALES.HOST_SERVER, GLOBALES.PORT_SERVER))
    GLOBALES.sock.sendall(data)


def receiveConfig():
    GLOBALES.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    GLOBALES.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if GLOBALES.IS_ALL_GROUPS:
        # on this port, receives ALL multicast groups
        GLOBALES.sock.bind(('', GLOBALES.MCAST_PORT))
    else:
        # on this port, listen ONLY to MCAST_GRP
        GLOBALES.sock.bind((GLOBALES.MCAST_GRP, GLOBALES.MCAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(GLOBALES.MCAST_GRP), socket.INADDR_ANY)

    GLOBALES.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)


def receive(chunk_size):
    data, address = GLOBALES.sock.recvfrom(chunk_size)
    return data, address


def hashVerification(server_hash):
    with open('./archivos/Datos.txt', 'rb') as file:
        client_hash = hashlib.sha1(file.read()).digest()
        return client_hash == server_hash[5:]

def iniciarCliente():
    sendConfig()
    send(b'ready')

    print("Listo para Leer")
    receiveConfig()
    GLOBALES.sock.settimeout(5)
    fragmentos, address = receive(65535)
    print("Cantidad de Fragmentos: " + fragmentos.decode('utf-8'))
    print("Sali de leer")
    i = 0
    with open('./archivos/Datos.txt', 'wb') as file:
        data, address = receive(65535)
        print("Escribiendo")
        while data:
            i += 1
            file.write(data)
            try:
                data = receive(65535)
            except socket.error:
                data = None
        print("Sali de Escribir")
    print("Paquetes recibidos: " + str(i))

    sendConfig()
    send(b'hash')

    receiveConfig()
    GLOBALES.sock.settimeout(5)
    hash, address = receive(4096)
    if b'hash:' in hash:
        print("Enviando respuesta del hash")
        verification = hashVerification(hash)
        message = b'envio:correcto estado:incorrecto'
        if verification:
            message = b'envio:correcto estado:correcto'
        sendConfig()
        send(message)
    print("Termine")




iniciarCliente()
