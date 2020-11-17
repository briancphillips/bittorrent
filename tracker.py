import socket
import re
import requests
import random
from os import urandom
import os.path
from bcoding import bencode, bdecode
from peer import Peer
from peer2 import Peer2

class Tracker(object):

    '''Class to connect to torrent tracker and get peer info.'''

    def __init__(self, torrent):
        self.torrent = torrent
        self.info_hash = torrent.get_info_hash()
        self.peer_id = urandom(20)
        self.port = 6881
        self.uploaded = 0
        self.downloaded = 0
        self.left = torrent.length - self.downloaded
        self.resp = self.get_t(e='started')

    def gen_p(self, e):
        return {'info_hash': self.info_hash,
                    'peer_id': self.peer_id,
                    'port': self.port,
                    'uploaded': self.uploaded,
                    'downloaded': self.downloaded,
                    'left': self.left,
                    'e': e
                }

    def get_t(self, e):
        max_tracker_attempts = 3
        counter = 0
        response = False
        while not response and counter < max_tracker_attempts * len(self.torrent.tracker_urls):
            response = self.next(counter, e)
            counter += 1
        if counter == max_tracker_attempts * len(self.torrent.tracker_urls):
            print('No working trackers found.')

        return response

    def next(self, counter, e):
        url = self.torrent.tracker_urls[counter%len(self.torrent.tracker_urls)]
        return self.send_request(e, url)

    def conn_req(self):
        conn_id = 0x41727101980 # default, required initial value to identify the protocol
        action = 0x0 # 0 for connection request
        txn_id = int(random.randrange(0, 2**32 - 1))
        msg = conn_id.to_bytes(8, byteorder='big') + action.to_bytes(4, byteorder='big') + \
                txn_id.to_bytes(4, byteorder='big')

        return msg, txn_id

    def comp_announce(self, conn_id, port, e):
        action = 1
        txn_id = int(random.randrange(0, 2**31 - 1))
        ip = 0
        key = int(random.randrange(0, 2**31 - 1))
        num_want = 2**17

        msg = conn_id + action.to_bytes(4, byteorder='big') + txn_id.to_bytes(4, byteorder='big') + \
                self.info_hash + self.peer_id + self.downloaded.to_bytes(8, byteorder='big') + \
                self.left.to_bytes(8, byteorder='big') + self.uploaded.to_bytes(8, byteorder='big') + \
                e.to_bytes(4, byteorder='big') + ip.to_bytes(4, byteorder='big') + \
                key.to_bytes(4, byteorder='big') + num_want.to_bytes(4, byteorder='big') + port.to_bytes(2, byteorder='big')

        return msg, txn_id


    def send_request(self, e, url):
        print("Sending request to tracker ...")
        if url.startswith('http'):
            return self._send_http_request(e, url)
        elif url.startswith('udp'):
            return self._send_udp_request(e, url)

    def _send_http_request(self, e, url):
        payload = self.gen_p(e)
        try:
            r = requests.get(url, params=payload, timeout=1)
            resp = bdecode(bytes(r.text, 'ISO-8859-1'))
            peers = resp['peers']
            peers_dict = {}

            print("HTTP tracker response received ...")
            for i in range(0, len(peers)):
                if not peers[i] in peers_dict.values():
                    #print(Peer(peers[i]))
                    #sys.exit(1)              
                    peers_dict[i] = Peer2(peers[i])

            resp['peers'] = peers_dict

            print("List of %d peers received" % len(resp['peers']))

            return resp

        except (ConnectionResetError, ConnectionError) as e:
            return False


    def _send_udp_request(self, e, url):
        s_tracker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_tracker.settimeout(1)
        addr, port = self.parse_udp_url(url)

        msg, txn_id = self.conn_req()

        try:
            s_tracker.sendto(msg, (addr, int(port)))
            response, _ = s_tracker.recvfrom(2048)
            print("UDP tracker response received ...")
            print("Length of response:", len(response))
        except:
            print("UDP tracker failed:", url)
            return False

        if len(response) >= 16:
            action_resp = int.from_bytes(response[:4], byteorder='big')
            txn_id_resp = int.from_bytes(response[4:8], byteorder='big')
            conn_id_resp = int.from_bytes(response[8:], byteorder='big')
            if txn_id_resp != txn_id or action_resp != 0:
                return False
        else:
            return False

        # Send announce message
        client_port = s_tracker.getsockname()[1]

        es = {
            'none': 0,
            'completed': 1,
            'started': 2,
            'stopped': 3
        }

        return self.send_announce(response[8:], client_port, es[e], addr, port, s_tracker)

    def send_announce(self, conn_id, client_port, e, addr, port, s_tracker):
        msg, txn_id = self.comp_announce(conn_id, client_port, e)

        s_tracker.sendto(msg, (addr, int(port)))

        print("Announce request sent ...")
        response, tracker_addr = s_tracker.recvfrom(4096)
        print("Length of response:", len(response))

        if len(response) >= 20:
            resp = {}

            resp['action'] = int.from_bytes(response[:4], byteorder='big')
            resp['txn_id'] = int.from_bytes(response[4:8], byteorder='big')
            resp['interval'] = int.from_bytes(response[8:12], byteorder='big')
            resp['leechers'] = int.from_bytes(response[12:16], byteorder='big')
            resp['seeders'] = int.from_bytes(response[16:20], byteorder='big')

            if resp['action'] != 1:
                print("Response action type is not 'announce.'")
                return False
            if resp['txn_id'] != txn_id:
                print("Transaction IDs do not match.")
                return False

            print('Leechers:', resp['leechers'])
            print('Seeders:', resp['seeders'])

            peers_dict = {}
            for i in range(20, len(response)-6, 6):
                if response[i:i+6] not in peers_dict:
                    peers_dict[response[i:i+6]] = Peer(response[i:i+6])

            resp['peers'] = peers_dict

            print("List of %d peers received" % len(resp['peers']))

            return resp

        else:
            return False

    def parse_udp_url(self, url):
        port_ip = re.match(r'^udp://(.+):(\d+)', url).groups()
        return port_ip[0], port_ip[1]