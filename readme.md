BitTorrent client written in Python.

Terms:

```
Queue size: All traffic processed by the system is in the form of network packets.

Pieces: BitTorrent splits the file up into chunks called pieces, each of a certain size. Sometimes it's 256KB, sometimes it's 1MB. As each peer receives a piece, they become a seed of that piece for other peers. With BitTorrent, we do not have a single source to download from.


```

Installation:

```
$ pip -r requirements.txt
```

Usage is as follows:

```
$ python main.py <filename>
```

##Example usage:
Assuming there is a file named `file.torrent` stored in a subfolder named torrents, usage would be like this:

```
$ python main.py torrents/file.torrent
```

You should then see a screen like this:

![status screenshot](http://i.imgur.com/sMoldft.png)

Client create a `Downloads` folder within its working directory to store all torrent downloads. Each torrent file will receive its own folder within `Downloads` named the same thing as the main torrent filename.

- Up to 30 peers at once (as recommended by the BitTorrent specification)
- Multifile downloads
- Pausing and resuming of downloads (it creates a temporary `status.txt` file during download that is uses to check progress if the download is halted for any reason)
- HTTP and UDP trackers
