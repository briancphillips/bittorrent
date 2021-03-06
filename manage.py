import sys
import socket
import random
import time
from queue import Queue
from threading import Thread, Lock, activeCount
import os

from util.filemanager import FileManager
from util.filewriter import FileWriter




class Connection(object):
    # Class to manage connections with peers
    TIMEOUT = 1

    MESSAGE_HANDLERS = {
                0: 'handle_choke',
                1: 'handle_unchoke',
                2: 'handle_interested',
                3: 'handle_not_interested',
                4: 'handle_have',
                5: 'handle_bitfield',
                6: 'handle_request',
                7: 'handle_piece',
                8: 'handle_cancel',
                9: 'handle_port'
            }

    MAX_CONNECTIONS = 30
    MAX_REQUESTS_PER_PEER = 5

    def __init__(self, tracker_response, torrent):
        self.tc = tracker_response
        self.info_hash = torrent.get_info_hash()
        self.num_peers = len(self.tc.resp['peers'])
        self.interval = self.tc.resp['interval']
        self.handshake = self.create_handshake()
        self.current_connections = set()
        self.name = torrent.name

        self.to_write = Queue()
        self.threads = {}
        self.peerlist_lock = Lock()
        self.file_lock = Lock()
        self.completion_status_lock = Lock()
        self.connections_lock = Lock()
        self.file_manager = FileManager(torrent, self.to_write)
        self.file_writer = FileWriter(torrent, self.to_write, self.file_manager)

        self.download_file()

    def create_handshake(self):
        pstrlen = bytes([19])
        pstr = b'BitTorrent protocol'
        reserved = b'\0' * 8
        info_hash = self.info_hash
        peer_id = self.tc.peer_id
        return pstrlen + pstr + reserved + info_hash + peer_id

    def get_peers(self):
        index = 0
        while len(self.current_connections) < self.MAX_CONNECTIONS and not self.file_manager.complete and self.available_peers != []:
            peer = self.available_peers[index%len(self.available_peers)]
            self.available_peers.remove(peer)
            if peer not in self.current_connections:
                self.start(peer)
            index += 1

    def download_file(self):
        peers = self.tc.resp['peers']
        self.available_peers = list(peers.values())
        random.shuffle(self.available_peers)

        self.get_peers()
        self.start_maintain_peerlist()

    def start_maintain_peerlist(self):
        t = Thread(target=self.maintain_peers)
        t.start()

    def maintain_peers(self):
        while True:            
            percent_complete = self.file_manager.download_status()
            os.system('cls' if os.name=='nt' else 'clear')

            print("Queue size:", self.file_manager.download_queue.qsize())
            print("Outstanding requests:", len(self.file_manager.outstanding_requests))

            print("Downloading", self.name)
            print("There are %r current connections and %r available peers." % (len(self.current_connections), len(self.available_peers)))
            needed, total = self.file_manager.get_piece_numbers()
            print("Pieces remaining: " + str(needed))
            print("Active threads: " + str(activeCount()))
            print("Active peers:", len(self.threads))
            print(self.status_bar(percent_complete))

            self.file_manager.enqueue_outstanding_requests()

            if self.available_peers == [] and not self.file_manager.complete:
                peers = self.tc.resp['peers']
                self.available_peers = list(peers.values())
                random.shuffle(self.available_peers)

            if not self.file_manager.complete:
                self.get_peers()
            if self.file_manager.complete:
                print("Complete - writing file to disk.")
                self.connections_lock.acquire()
                try:
                    while len(self.current_connections) > 0:
                        self.close_peer_connection(self.current_connections.pop())
                finally:
                    self.connections_lock.release()
                return
            time.sleep(1)

    def start(self, peer):
        # self.peerlist_lock.acquire()
        # try:
        #     self.current_connections.add(peer)
        # finally:
        #     self.peerlist_lock.release()
        self.current_connections.add(peer)

        self.threads[peer] = Thread(target=self.connect_to_peer, args=(peer,))
        self.threads[peer].start()

    
    def close(self):
        """Close the socket underlying this connection."""
        self.rfile.close()

        if not self.linger:
            # Python's socket module does NOT call close on the kernel socket
            # when you call socket.close(). We do so manually here because we
            # want this server to send a FIN TCP segment immediately. Note this
            # must be called *before* calling socket.close(), because the latter
            # drops its reference to the kernel socket.
            if hasattr(self.socket, '_sock'):
                self.socket._sock.close()
            self.socket.close()
        else:
            # On the other hand, sometimes we want to hang around for a bit
            # to make sure the client has a chance to read our entire
            # response. Skipping the close() calls here delays the FIN
            # packet until the socket object is garbage-collected later.
            # Someday, perhaps, we'll do the full lingering_close that
            # Apache does, but not today.
            pass 
    
    def connect_to_peer(self, peer):
        s = peer.connection()
        if s:
            if self.initial_connection(peer):
                self.wait_for_response(peer)
        else:
            self.close_peer_connection(peer)
        return

    def initial_connection(self, peer):
        r = self.send_handshake(peer)
        s = peer.connection()
        if r is not None and len(r) > 0:
            if self.validate_hash(r) == False:
                print("Hash invalid")
                self.close_peer_connection(peer)
                return False
            else:
                return True
        else:
            self.close_peer_connection(peer)
            return False

    def send_handshake(self, peer):
        s = peer.connection()
        message = self.handshake
        try:
            sent = s.send(message)
            return self.wait_for_handshake(peer)
        except (ConnectionRefusedError, socket.timeout, BrokenPipeError, ConnectionResetError) as e:
            self.close_peer_connection(peer)
            return None

    def wait_for_handshake(self, peer):
        s = peer.connection()
        try:
            r0 = s.recv(1)
        except:
            return None
        expected_length = int.from_bytes(r0, byteorder = 'big') + 49
        bytes_received = len(r0)
        received_from_peer = r0

        if bytes_received == 0:
            return received_from_peer

        while bytes_received < expected_length:
            bytes_read = s.recv(expected_length - bytes_received)

            if len(bytes_read) == 0:
                return received_from_peer

            bytes_received += len(bytes_read)
            received_from_peer += bytes_read
        if s:
            s.settimeout(5)
        return received_from_peer

    def validate_hash(self, response):
        prefix = response[0]
        return response[prefix + 1 + 8:-20] == self.info_hash

    def send_message(self, peer, message):
        s = peer.connection()
        try:
            sent = s.send(message)
        except:
            self.close_peer_connection(peer)
            return False

        if sent < 0:
            self.close_peer_connection(peer)
            return False
        else:
            return True

    def wait_for_response(self, peer):
        s = peer.connection()

        msg_len = 1
        while msg_len != 0 and not self.file_manager.complete:
            try:
                msg_len = int.from_bytes(s.recv(4), byteorder='big')
                msg_len = max(msg_len, 1)
            except:
                self.close_peer_connection(peer)
                return

            try:
                msg_id = s.recv(1)
                bytes_read = s.recv(msg_len - 1)
            except:
                self.close_peer_connection(peer)
                return

            received_from_peer = b''
            received_from_peer += bytes_read
            bytes_received = 1

            while len(bytes_read) != 0 and bytes_received < msg_len - 1:
                try:
                    bytes_read = s.recv(msg_len - 1 - len(received_from_peer))
                except (socket.timeout, ConnectionResetError, OSError):
                    self.close_peer_connection(peer)
                    return False
                bytes_received += len(bytes_read)
                received_from_peer += bytes_read

            if int.from_bytes(msg_id, byteorder='big') not in self.MESSAGE_HANDLERS:
                self.close_peer_connection(peer)
                return False

            handler = getattr(self, self.MESSAGE_HANDLERS[int.from_bytes(msg_id, byteorder='big')])
            handler(peer, received_from_peer)

        if msg_len == 1:
            self.close_peer_connection(peer)
            return False
        else:
            return received_from_peer
            return True

    def send_request(self, peer):
        while peer.current_request_count < self.MAX_REQUESTS_PER_PEER and not self.file_manager.complete:
            self.request_next_block(peer)

    def request_next_block(self, peer):
        try:
            self.file_lock.acquire()
            next_index, next_begin, block_length = self.file_manager.get_next_block(peer)
        finally:
            self.file_lock.release()

        if next_index != None:
            msg = self.compose_request_message(next_index, next_begin, block_length)
            self.send_message(peer, msg)
            peer.current_request_count += 1
        else:
            self.close_peer_connection(peer)

    def handle_choke(self, peer, message):
        self.close_peer_connection(peer)

    def handle_unchoke(self, peer, message):
        self.send_request(peer)

    def handle_interested(self, peer, message):
        pass

    def handle_not_interested(self, peer, message):
        pass

    def handle_have(self, peer, message):
        piece = int.from_bytes(message, byteorder='big')
        peer.add_piece(piece)

        if peer.interested == False:
            interested_msg = self.compose_interested_message()
            peer_resp = self.send_message(peer, interested_msg)
            if peer_resp:
                peer.interested = True

        return True

    def handle_bitfield(self, peer, message):
        pieces = bin(int.from_bytes(message, byteorder='big'))[2:]
        available_indices = [i for i in range(len(pieces)) if pieces[i] == '1']
        peer.add_from_bitfield(available_indices)

        if peer.interested == False:
            interested_msg = self.compose_interested_message()
            peer_resp = self.send_message(peer, interested_msg)
            if peer_resp:
                peer.interested = True

        return True

    def handle_request(self, peer, message):
        pass

    def handle_piece(self, peer, message):
        if self.file_manager.complete:
            self.close_peer_connection(peer)
        else:
            index = int.from_bytes(message[:4], byteorder='big')
            begin = int.from_bytes(message[4:8], byteorder='big')
            block = message[8:]
            self.completion_status_lock.acquire()
            try:
                self.file_manager.update_status(index, begin, block)
                peer.current_request_count -= 1
            finally:
                self.completion_status_lock.release()
            self.send_request(peer)

    def handle_cancel(self, peer, message):
        pass

    def handle_port(self, peer, message):
        pass

    def compose_interested_message(self):
        interested = (1).to_bytes(4, byteorder='big') + (2).to_bytes(1, byteorder='big')
        return interested

    def compose_request_message(self, index, begin, length):
        req = (13).to_bytes(4, byteorder='big') + (6).to_bytes(1, byteorder='big') + \
            (index).to_bytes(4, byteorder='big') +(begin).to_bytes(4, byteorder='big') + \
            (length).to_bytes(4, byteorder='big')
        return req

    def close_peer_connection(self, peer):
        self.peerlist_lock.acquire()
        try:
            if peer in self.current_connections:
                self.current_connections.remove(peer)
                del self.threads[peer]
            if peer not in self.available_peers:
                self.available_peers.append(peer)
            peer.shutdown()
        finally:
            self.peerlist_lock.release()

    def status_bar(self, percent_complete):
        int_percent_complete = int(percent_complete)
        front = "#"*int_percent_complete
        back = " "*(100-int_percent_complete)
        bar = "[" + front + back + "] " + "%.2f"%(percent_complete) + "%"
        return bar
