from vidstream import AudioSender
from vidstream import AudioReceiver

import threading
import socket


#y=-22*log(x-20)+40

def update_position(pos):
    count = 0
    while True:
        if count % 1000000 == 0:
            pos[0] = (pos[0] + 1) % 100
            pos[1] = (pos[1] + 1) % 100
        count += 1

if __name__ == '__main__':
    ip = socket.gethostbyname(socket.gethostname())
    print(ip)
    max_addr = '192.168.1.93'
    max_port = 5555
    marc_addr = '192.168.1.84'
    marc_port = 9999

    receiver = AudioReceiver(marc_addr, marc_port)
    sender = AudioSender(max_addr, max_port)

    # copy this
    pos = [0, 0]
    sender_thread = threading.Thread(target=sender.start_stream, args=(pos,))
    receiver_thread = threading.Thread(target=receiver.start_server, args=(pos,))
    position_thread = threading.Thread(target=update_position, args=(pos,))
    receiver_thread.start()
    sender_thread.start()
    position_thread.start()



