import socket
from manage import Connection

class Peer2(object):

    def __init__(self, bin_string):
        self.parse_bin(bin_string)
        self.pieces = set()
        self.interested = False
        self.s = None
        self.current_request_count = 0

    def __repr__(self):
        return "IP: %r, Port: %r" % (self.ip, self.port)

    def parse_bin(self, bin_str):
        self.ip = bin_str['ip']
        self.port = bin_str['port']

    def add_piece(self, piece):
        self.pieces.add(piece)

    def add_from_bitfield(self, message):
        for piece in message:
            self.add_piece(piece)

    def connection(self):
        if not self.s:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(Connection.TIMEOUT)
            try:
                self.s.connect((self.ip, self.port))
            except (ConnectionRefusedError, socket.timeout, BrokenPipeError, ConnectionResetError, OSError) as e:
                # print("Error connecting: %r" % e)
                return False
        return self.s

    def shutdown(self):
        self.interested = False
        if self.s:
            self.s.close()
            self.s = None
