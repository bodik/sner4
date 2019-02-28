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


logger = logging.getLogger('sner.agent') # pylint: disable=invalid-name
logging.basicConfig(stream=sys.stdout, format='%(levelname)s %(message)s')
logger.setLevel(logging.INFO)


def run_once(server, queue=None):
	"""get and process one job"""

	## get the assignment
	url = '%s/scheduler/job/assign' % server
	if queue:
		url += '/%s' % queue
	assignment = requests.get(url).json()
	if 'id' not in assignment:
		# no work available
		return 0
	if (not re.match(r'[a-f0-9\-]{32}', assignment['id'])) or ('module' not in assignment):
		# assignment corrupted
		return 1
	logger.debug('sner.agent got assignment: %s', assignment)


	## process the assignment
	logger.debug('sner.agent processing assignment')
	jobdir = assignment['id']
	oldcwd = os.getcwd()
	retval = 1
	try:
		os.makedirs(jobdir, mode=0o700)
		os.chdir(jobdir)
		module_instance = getattr(sner.agent.modules, assignment['module'].capitalize())(assignment)
		retval = module_instance.run()
	finally:
		os.chdir(oldcwd)
	output = '%s.tar.bz2' % jobdir
	with tarfile.open(output, 'w:bz2') as ftmp:
		ftmp.add(jobdir)
	shutil.rmtree(jobdir)


	## postback output and retval
	logger.debug('sner.agent uploading assignment output')
	with open(output, 'rb') as ftmp:
		output_data = base64.b64encode(ftmp.read()).decode('utf-8')
	response = requests.post(
		'%s/scheduler/job/output' % server,
		json={'id': assignment['id'], 'retval': retval, 'output': output_data})
	if response.status_code == HTTPStatus.OK:
		os.remove(output)


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
