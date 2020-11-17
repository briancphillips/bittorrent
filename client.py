import sys
from parse import PT
from torrent import Torrent
from tracker import Tracker
from manage import Connection
from util.filemanager import FileManager


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Please provide a torrent file.\nUsage: "python main.py <torrent filename>"')
        sys.exit(1)
    filename = sys.argv[1]
    torrent = PT(filename).parse()
    tc = Tracker(torrent)
    conn = Connection(tc, torrent)
