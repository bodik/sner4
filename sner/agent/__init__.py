#!/usr/bin/env python
"""sner agent"""

import argparse
import base64
import json
import logging
import os
import re
import requests
import shutil
import sner.agent.modules
import sys
import tarfile
from contextlib import contextmanager
from http import HTTPStatus


logger = logging.getLogger() # pylint: disable=invalid-name
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(levelname)s %(message)s')


def run_once(server, queue=None):
	"""get and process one job"""

	## get the assignment
	logger.debug('sner.agent attempt to get assignment')
	url = '%s/scheduler/job/assign' % server
	if queue:
		url += '/%s' % queue
	assignment = requests.get(url).json()
	### no work available
	if 'id' not in assignment:
		return 0
	### assignment corrupted
	if (not re.match(r'[a-f0-9\-]{32}', assignment['id'])) or ('module' not in assignment):
		return 1
	logger.debug('sner.agent got assignment: %s', assignment)


	## process the assignment
	logger.debug('sner.agent assignment processing')
	jobdir = assignment['id']
	output = '%s.tar.bz2' % jobdir
	retval = 1

	oldcwd = os.getcwd()
	try:
		os.makedirs(jobdir, mode=0o700)
		os.chdir(jobdir)
		module_instance = getattr(sner.agent.modules, assignment['module'].capitalize())(assignment)
		retval = module_instance.run()
	finally:
		os.chdir(oldcwd)

	with tarfile.open(output, 'w:bz2') as ftmp:
		ftmp.add(jobdir)
	shutil.rmtree(jobdir)
	logger.debug('sner.agent assignment done')


	## postback output and retval
	logger.debug('sner.agent uploading assignment output')
	with open(output, 'rb') as ftmp:
		output_data = base64.b64encode(ftmp.read()).decode('utf-8')
	response = requests.post(
		'%s/scheduler/job/output' % server,
		json={'id': assignment['id'], 'retval': retval, 'output': output_data})
	logger.debug(response)
	if response.status_code == HTTPStatus.OK:
		os.remove(output)
	logger.debug('sner.agent uploading assignment output done')


	return 0


def main():
	"""sner agent main"""

	parser = argparse.ArgumentParser()
	parser.add_argument('--debug', action='store_true', help='show debug output')
	parser.add_argument('--server', default='http://localhost:18000', help='server uri')
	parser.add_argument('--workdir', default='/tmp', help='workdir')
	parser.add_argument('--queue', help='select specific queue to work on')
	args = parser.parse_args()
	if args.debug:
		logger.setLevel(logging.DEBUG)
	logger.debug(args)

	os.chdir(args.workdir)
	return run_once(args.server, args.queue)


if __name__ == '__main__':
	sys.exit(main())
