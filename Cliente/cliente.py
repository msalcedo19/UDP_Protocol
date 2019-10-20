from tkinter import *
import threading
import queue
import socket
import struct
import hashlib
import time
cola = queue.Queue()


class Variables:
    MCAST_GRP = '224.1.1.1'
    MCAST_PORT = 5007
    HOST_SERVER = '127.0.0.1'
    PORT_SERVER = 65432
    IS_ALL_GROUPS = True
    sock = None

    fileName = ''
    sizeFile = 0
    integrity = ''
    conn_error = True
    fileLogs = None
    indexLogs = 1


def send_config():
    Variables.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    Variables.sock.connect((Variables.HOST_SERVER, Variables.PORT_SERVER))


def send(data):
    Variables.sock.sendall(data)


def receive_config():
    Variables.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    Variables.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if Variables.IS_ALL_GROUPS:
        # on this port, receives ALL multicast groups
        Variables.sock.bind(('', Variables.MCAST_PORT))
    else:
        # on this port, listen ONLY to MCAST_GRP
        Variables.sock.bind((Variables.MCAST_GRP, Variables.MCAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(Variables.MCAST_GRP), socket.INADDR_ANY)

    Variables.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)


def receive(chunk_size):
    data, address = Variables.sock.recvfrom(chunk_size)
    return data, address


def hash_verification(server_hash):
    with open(Variables.fileName, 'rb') as file:
        client_hash = hashlib.sha1(file.read()).digest()
        return client_hash == server_hash[5:]


def start_client():
    wait_time = 2
    while Variables.conn_error:
        try:
            send_config()
            send(b'ready')
            Variables.conn_error = False
        except socket.error:
            time.sleep(wait_time)
            wait_time *= 2

    Variables.conn_error = True
    receive_config()
    info, address = receive(1024)
    if b'fileName' in info:
        info_string = info.decode('utf-8')
        index = info_string.find('fragmentos')
        index2 = info_string.find('sizeFile')
        Variables.fileName = './archivos/' + info_string[9:index]
        Variables.sizeFile = int(info_string[index2+9:])
    i = 0
    with open(Variables.fileName, 'wb') as file:
        data, address = receive(65507)
        tiempo_inicial = time.time()
        Variables.sock.settimeout(5)
        print("Recibiendo...")
        while data:
            i += 1
            file.write(data)
            try:
                data, address = receive(65507)
            except socket.error:
                data = None
        tiempo_final = time.time()

    # Logs
    Variables.fileLogs = './logs/Log' + str(Variables.indexLogs) + '.txt'
    with open(Variables.fileLogs, "a+") as file:
        file.write('Fecha: ' + time.strftime("%d/%m/%y") + ' Hora: ' + time.strftime("%I:%M:%S"))
        file.write('\nMultiCastGroup: ' + str(Variables.MCAST_GRP)
                   + '  MulticastPort: ' + str(Variables.MCAST_PORT))
        file.write('\nNombre Archivo: ' + Variables.fileName +
                   ' Tamaño: ' + str(Variables.sizeFile / 1024) + ' KB')
        file.write('\nPaquetes Recibidos: ' + str(i))
        file.write('\nTiempo de Transferencia: ' + str(tiempo_final - tiempo_inicial) + ' segundos\n')

    wait_time = 2
    while Variables.conn_error:
        try:
            send_config()
            send(b'hash')
            Variables.conn_error = False
        except socket.error:
            time.sleep(wait_time)
            if wait_time < 16:
                wait_time *= 2
    Variables.conn_error = True
    hash, address = receive(4096)
    if b'hash:' in hash:
        print("Enviando respuesta del hash...")
        verification = hash_verification(hash)
        message = b'envio: address:' + str(Variables.sock.getsockname()).encode('utf-8') + b' estado:incorrecto '
        Variables.integrity = 'incorrecto'
        if verification:
            Variables.integrity = 'correcto'
            message = b'envio: address:' + str(Variables.sock.getsockname()).encode('utf-8') + b' estado:correcto '
        send(message)
        with open(Variables.fileLogs, "a+") as file:
            file.write('\nEstado del archivo recibido: ')
            file.write('\n  ' + message.decode('utf-8'))
            file.write('\n\n------------------------------------------\n\n')
    cola.put('Listo')
    print('Termine')


def procesar():
    start_client()


raiz = Tk()
raiz.title("Cliente")
raiz.resizable(0, 0)
raiz.geometry("400x200")

estado = StringVar()
estado.set("Archivo Recibido: Ninguno")
estadoEnvio = StringVar()
estadoEnvio.set("Estado del Envio: Desconectado")
estadoHash = StringVar()
estadoHash.set("Integridad del archivo: ")

textEstado = Label(raiz, textvariable=estado).place(x=10, y=20)
lblEstadoEnvio = Label(raiz, textvariable=estadoEnvio).place(x=10, y=60)
textEstadoHash = Label(raiz, textvariable=estadoHash).place(x=10, y=100)


class Thread(threading.Thread):
    def __init__(self, num, col):
        threading.Thread.__init__(self)
        self.num = num
        self.cola = col

    def run(self):
        procesar()


def enviarNotificacion():
    t = Thread(1, cola)
    t.daemon = True
    t.start()
    estadoEnvio.set("Estado del Envio: Recibiendo...")
    botonListo.config(state=DISABLED)


botonListo = Button(raiz, text="Listo", command=enviarNotificacion)
botonListo.config(state='normal')
botonListo.pack(side="bottom")

while True:
    raiz.update_idletasks()
    raiz.update()
    if cola.empty() is not True:
        cola.get()
        estado.set("Archivo Recibido: " + Variables.fileName[11:])
        estadoEnvio.set("Estado del Envio: Recibido")
        estadoHash.set("Integridad del archivo: " + Variables.integrity)
        botonListo.config(state='normal')
