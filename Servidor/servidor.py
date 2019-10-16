import socket


class GLOBALES:
    clientes = 0
    recibiendo = True
    HOST = '127.0.0.1'
    PORT = 65432
    sock = None


def iniciarServer():
    MCAST_GRP = '224.1.1.1'
    MCAST_PORT = 5007
    # regarding socket.IP_MULTICAST_TTL
    # ---------------------------------
    # for all packets sent, after two hops on the network the packet will not
    # be re-sent/broadcast (see https://www.tldp.org/HOWTO/Multicast-HOWTO-6.html)
    MULTICAST_TTL = 2

    GLOBALES.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    GLOBALES.sock.bind((GLOBALES.HOST, GLOBALES.PORT))
    GLOBALES.sock.listen()
    while True:
        if GLOBALES.recibiendo:
            print("Recibiendo Conexiones")
            conn, addr = GLOBALES.sock.accept()
            data = conn.recv(2048)
            if data == b'ready':
                GLOBALES.clientes += 1
            if GLOBALES.clientes == 1:
                GLOBALES.recibiendo = False
                print("Clientes listos")
        else:
            print("Listo para transmitir")
            GLOBALES.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            GLOBALES.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
            i = 0
            with open('./archivos/Datos.txt', 'rb') as file:
                data = file.read(2048)
                print("Enviando")
                while data:
                    i += 1
                    GLOBALES.sock.sendto(data, (MCAST_GRP, MCAST_PORT))
                    data = file.read(2048)
            print("Paquetes enviados: " + str(i))
            break


iniciarServer()

