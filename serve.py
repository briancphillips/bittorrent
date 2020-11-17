from pybtracker import TrackerServer
import asyncio
import logging

logger = logging.getLogger('udp_tracker_server')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)



loop = asyncio.get_event_loop()
logger.info(":: Setting Loop...")
tracker = TrackerServer(local_addr=('0.0.0.0', 2255), loop=loop)
logger.info(":: Setting up tracker at 0.0.0.0:2255 ...")
asyncio.ensure_future(tracker.start())
try:
	logger.info(":: Server started ... 'udp://bucketvids.com:2255'")
	loop.run_forever()
except KeyboardInterrupt:
	logger.exception(":: Server stopped! ...")
	loop.run_until_complete(tracker.stop())
except Exception as e:
	logger.exception(e)
	# raise e