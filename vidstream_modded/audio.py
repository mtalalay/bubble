import socket
import pyaudio
import select
import threading
import math
import numpy


class AudioSender:

    def __init__(self, host, port, audio_format=pyaudio.paInt16, channels=1, rate=44100, frame_chunk=4096):
        self.__host = host
        self.__port = port

        self.__audio_format = audio_format
        self.__channels = channels
        self.__rate = rate
        self.__frame_chunk = frame_chunk

        self.__sending_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__audio = pyaudio.PyAudio()

        self.__running = False

    #
    # def __callback(self, in_data, frame_count, time_info, status):
    #     if self.__running:
    #         self.__sending_socket.send(in_data)
    #         return (None, pyaudio.paContinue)
    #     else:
    #         try:
    #             self.__stream.stop_stream()
    #             self.__stream.close()
    #             self.__audio.terminate()
    #             self.__sending_socket.close()
    #         except OSError:
    #             pass # Dirty Solution For Now (Read Overflow)
    #         return (None, pyaudio.paComplete)

    def start_stream(self, pos):
        if self.__running:
            print("Already streaming")
        else:
            self.__running = True
            thread = threading.Thread(target=self.__client_streaming, args=(pos,))
            thread.start()

    def stop_stream(self):
        if self.__running:
            self.__running = False
        else:
            print("Client not streaming")

    def __client_streaming(self, pos):
        self.__sending_socket.connect((self.__host, self.__port))
        self.__stream = self.__audio.open(format=self.__audio_format, channels=self.__channels, rate=self.__rate,
                                          input=True, frames_per_buffer=self.__frame_chunk)
        while self.__running:
            # send_data = int.from_bytes((self.__stream.read(self.__frame_chunk), position), byteorder='big')

            # print(count)
            send_data = self.__stream.read(self.__frame_chunk) + bytes(pos)
            # print('send_data')
            # print(list(send_data[-10:]))
            self.__sending_socket.send(send_data)


class AudioReceiver:

    def __init__(self, host, port, slots=8, audio_format=pyaudio.paInt16, channels=1, rate=44100, frame_chunk=4096):
        self.__host = host
        self.__port = port

        self.__slots = slots
        self.__used_slots = 0

        self.__audio_format = audio_format
        self.__channels = channels
        self.__rate = rate
        self.__frame_chunk = frame_chunk

        self.__audio = pyaudio.PyAudio()

        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server_socket.bind((self.__host, self.__port))

        self.__block = threading.Lock()
        self.__running = False

    def start_server(self, pos):
        if self.__running:
            print("Audio server is running already")
        else:
            self.__running = True
            self.__stream = self.__audio.open(format=self.__audio_format, channels=self.__channels, rate=self.__rate,
                                              output=True, frames_per_buffer=self.__frame_chunk)
            thread = threading.Thread(target=self.__server_listening, args=(pos,))
            thread.start()

    def __server_listening(self, pos):
        self.__server_socket.listen()
        while self.__running:
            self.__block.acquire()
            connection, address = self.__server_socket.accept()
            if self.__used_slots >= self.__slots:
                print("Connection refused! No free slots!")
                connection.close()
                self.__block.release()
                continue
            else:
                self.__used_slots += 1

            self.__block.release()
            thread = threading.Thread(target=self.__client_connection, args=(connection, address, pos))
            thread.start()

    def __client_connection(self, connection, address, pos):
        receiver_position = pos
        while self.__running:
            recv_data = connection.recv(2 * self.__frame_chunk + 2)
            # print('recv_data')
            # print(list(recv_data[-10:]))
            audio_data = recv_data[:-2]
            position = recv_data[-2:]
            print(f'({position[0]}, {position[1]})')
            # print(position)
            # lower volume
            distance = round(math.sqrt(
                (receiver_position[0] - int(position[0])) ** 2 + (receiver_position[1] - int(position[1])) ** 2))
            print(f'distance: {distance}')
            if distance > 99:
                distance = -1
            ret = vol_ctrl(audio_data, LOOKUP[distance])
            self.__stream.write(ret)

    def stop_server(self):
        if self.__running:
            self.__running = False
            closing_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            closing_connection.connect((self.__host, self.__port))
            closing_connection.close()
            self.__block.acquire()
            self.__server_socket.close()
            self.__block.release()
        else:
            print("Server not running!")


def vol_ctrl(data, volume):
    sound_level = (volume / 100.)
    ret = []
    for i in range(0, len(data), 2):
        sample = (data[i + 1] << 8) | (data[i] << 0)
        if sample > 0x7FFF:
            sample = sample - 0xFFFF
        # print(sample)
        sample = int(sample * sound_level)
        ret.append((sample >> 0) & 0b1111_1111)
        ret.append((sample >> 8) & 0b1111_1111)

    # ret = [int(i * sound_level) for i in data]
    return bytes(ret)
    # for i in range(len(data)):
    #     data[i] = data[i] * sound_level


def audio_datalist_set_volume(datalist, volume):
    """ Change value of list of audio chunks """
    sound_level = (volume / 100.)
    # for i in range(len(datalist)):
    chunk = numpy.fromstring(datalist, numpy.int16)

    chunk = chunk * sound_level

    datalist = chunk.astype(numpy.int16)


# LOOKUP = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 98, 96,
#          94, 92, 90, 88, 86, 84, 82, 80, 78, 76, 74, 72, 70, 68, 66, 64, 62, 60, 58, 56, 54, 52, 50, 48, 46, 44, 42,
#          40, 38, 36, 34, 32, 30, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
#          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
LOOKUP = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 40,
          33.3773401, 29.5033324, 26.75468019, 24.6226599, 22.88067249, 21.40784312, 20.13202029, 19.00666479, 18,
          17.08936093, 16.25801259, 15.49324625, 14.78518322, 14.1259923, 13.50936038, 12.93012373, 12.38400489,
          11.86742078, 11.3773401, 10.91117552, 10.46670102, 10.04198761, 9.635352682, 9.245319809, 8.870586345,
          8.509997189, 8.16252331, 7.827244046, 7.503332396, 7.190042736, 6.886700477, 6.592693323, 6.307463825,
          6.030503024, 5.761344983, 5.499562071, 5.244760874, 4.996578645, 4.754680191, 4.518755152, 4.288515611,
          4.063693977, 3.844041117, 3.629324697, 3.419327703, 3.213847125, 3.012692778, 2.815686239, 2.622659905,
          2.433456126, 2.24792644, 2.065930869, 1.887337284, 1.712020831, 1.539863406, 1.370753175, 1.204584142,
          1.041255744, 0.880672492, 0.72274363, 0.567382831, 0.414507912, 0.264040572, 0.115906154, 0, 0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0, 0]
