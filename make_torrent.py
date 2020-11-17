from dottorrent import Torrent
import os
import logging

logger = logging.getLogger('make_torrent')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)






def make_torrent(location, comment):
	try:
		t = Torrent(
			location,
			trackers = ['udp://bucketvids.com:2255'],
			private = True,
			comment = comment,
			include_md5 = True
		)

		logger.info("Generating torrent for location : %s ... " %(location))
		t.generate()

		filename = location.split('/')[-1] + '.torrent'
		path = os.path.join(os.getcwd(),filename)
		print(path)
		logger.info("Torrent file be saved in path : %s" %(path))

		with open(path, 'wb') as fp:
			t.save(fp)
			logger.info("Torrent saved! Enjoy seeding ...")
		return True

	except FileNotFoundError:
		logger.error("File(s) not found")
		return False
	except Exception as e:
		raise e

make_torrent("Downloads/Tears of Steel","Testing")