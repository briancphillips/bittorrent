BitTorrent client written in Python. Usage is as follows:

```
$ python main.py <filename>
```

##Example usage:
Assuming there is a file named `file.torrent` stored in the same directory as BitPy, usage would be like this:

```
$ python main.py file.torrent
```

You should then see a screen like this:

![status screenshot](http://i.imgur.com/sMoldft.png)

Client create a `Downloads` folder within its working directory to store all torrent downloads. Each torrent file will receive its own folder within `Downloads` named the same thing as the main torrent filename.

- Up to 30 peers at once (as recommended by the BitTorrent specification)
- Multifile downloads
- Pausing and resuming of downloads (it creates a temporary `status.txt` file during download that is uses to check progress if the download is halted for any reason)
- HTTP and UDP trackers
