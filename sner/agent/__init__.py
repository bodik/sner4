#!/usr/bin/env python
"""sner agent"""

import json
import logging
import os
import re
import shutil
import signal
import sys
from argparse import ArgumentParser
from base64 import b64encode
from http import HTTPStatus
from io import BytesIO
from time import sleep
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

import jsonschema
import requests

import sner.agent.protocol
from sner.agent.modules import registered_modules


logger = logging.getLogger('sner.agent') # pylint: disable=invalid-name
logging.basicConfig(stream=sys.stdout, format='%(levelname)s %(message)s')
logger.setLevel(logging.INFO)


class Agent():
	"""agent class to fetch and execute assignments from central job server"""

	def __init__(self):
		self.log = logging.getLogger('sner.agent')
		self.loop = True
		self.module_instance = None


	def run(self, server, queue, oneshot=False):
		"""fetch and process assignment from server"""

		def zipdir(path):
			"""pack directory to in memory zipfile"""
			buf = BytesIO()
			with ZipFile(buf, 'w', ZIP_DEFLATED) as output_zip:
				for root, _dirs, files in os.walk(path):
					for fname in files:
						filepath = os.path.join(root, fname)
						arcname = os.path.join(*(filepath.split(os.path.sep)[1:]))
						output_zip.write(filepath, arcname)
			return b64encode(buf.getvalue()).decode('utf-8')


		### setup signal handlers
		original_signal_handlers = {}
		for isig, ihan in [(signal.SIGTERM, self.terminate), (signal.SIGINT, self.terminate), (signal.SIGUSR1, self.shutdown)]:
			original_signal_handlers[isig] = signal.getsignal(isig)
			signal.signal(isig, ihan)


		retval = 0
		while self.loop:
			## get assignment
			assignment = requests.get('%s/scheduler/job/assign%s' % (server, '/%s'%queue if queue else '')).json()
			self.log.debug('got assignment: %s', assignment)

			if assignment:
				## process it
				retval = self.process_assignment(assignment)
				self.log.debug('processed, retval=%d', retval)

				## upload output
				jobdir = assignment['id']
				output = {'id': assignment['id'], 'retval': retval, 'output': zipdir(jobdir)}
				response = requests.post('%s/scheduler/job/output' % server, json=output)
				if response.status_code == HTTPStatus.OK:
					shutil.rmtree(jobdir)
				else:
					self.log.error('output upload failed')
					retval = 1
					self.loop = False
			elif not oneshot:
				## wait for assignment if not in oneshot mode
				sleep(10)

			## end if requested
			if oneshot:
				self.loop = False


		### restore signal handlers
		for isig, ihan in original_signal_handlers.items():
			signal.signal(isig, ihan)

		return retval


	def shutdown(self, signum=None, frame=None): # pylint: disable=unused-argument
		"""wait for current assignment to finish"""

		self.log.info('shutdown')
		self.loop = False


	def terminate(self, signum=None, frame=None): # pylint: disable=unused-argument
		"""terminate at once"""

		self.log.info('terminate')
		self.loop = False
		if self.module_instance:
			self.module_instance.terminate()


	def process_assignment(self, assignment):
		"""process assignment"""

		jsonschema.validate(assignment, schema=sner.agent.protocol.assignment)
		jobdir = assignment['id']

		oldcwd = os.getcwd()
		try:
			os.makedirs(jobdir, mode=0o700)
			os.chdir(jobdir)
			self.module_instance = registered_modules[assignment['module']]()
			retval = self.module_instance.run(assignment)
		except Exception as e:
			self.log.error(e)
			retval = 1
		finally:
			self.module_instance = None
			os.chdir(oldcwd)

		return retval


def main():
	"""sner agent main"""

	parser = ArgumentParser()
	parser.add_argument('--debug', action='store_true', help='show debug output')
	parser.add_argument('--workdir', default='/tmp', help='workdir')
	parser.add_argument('--server', default='http://localhost:18000', help='server uri')
	parser.add_argument('--queue', help='select specific queue to work on')
	parser.add_argument('--oneshot', action='store_true', help='do not loop for assignments')
	parser.add_argument('--assignment', help='manually specified assignment; mostly for debug purposses')

	parser.add_argument('--shutdown', type=int, help='request gracefull shutdown of the agent specified by PID')
	parser.add_argument('--terminate', type=int, help='request immediate termination of the agent specified by PID')

	args = parser.parse_args()
	if args.debug:
		logger.setLevel(logging.DEBUG)
	logger.debug(args)

	## agent process management helpers
	if args.shutdown:
		return os.kill(args.shutdown, signal.SIGUSR1)
	if args.terminate:
		return os.kill(args.terminate, signal.SIGTERM)

	## agent with custom assignment
	os.chdir(args.workdir)
	if args.assignment:
		tmp = json.loads(args.assignment)
		if 'id' not in tmp:
			tmp['id'] = str(uuid4())
		return Agent().process_assignment(tmp)

	## standard agent
	return Agent().run(args.server, args.queue, args.oneshot)


if __name__ == '__main__':
	sys.exit(main())
