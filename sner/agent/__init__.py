#!/usr/bin/env python
"""sner agent"""

import argparse
import base64
import json
import logging
import os
import re
import shutil
import sys
import uuid
import zipfile
from contextlib import contextmanager
from http import HTTPStatus

import jsonschema
import requests

import sner.agent.modules
import sner.agent.protocol


logger = logging.getLogger('sner.agent') # pylint: disable=invalid-name
logging.basicConfig(stream=sys.stdout, format='%(levelname)s %(message)s')
logger.setLevel(logging.INFO)


def get_assignment(server, queue=None):
	"""get the assignment"""

	url = '%s/scheduler/job/assign' % server
	if queue:
		url += '/%s' % queue

	assignment = requests.get(url).json()
	if not assignment:
		# no work available
		return 0
	jsonschema.validate(assignment, schema=sner.agent.protocol.assignment)
	logger.debug('got assignment: %s', assignment)

	return assignment


def process_assignment(assignment):
	"""process assignment"""

	logger.debug('processing assignment')
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
	output_file = '%s.zip' % jobdir
	with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as output_zip:
		for root, _dirs, files in os.walk(jobdir):
			for fname in files:
				output_zip.write(os.path.join(root, fname))
	shutil.rmtree(jobdir)

	return (retval, output_file)


def upload_output(server, assignment, retval, output_file):
	"""upload processed assignment output_file"""

	logger.debug('uploading assignment output')
	with open(output_file, 'rb') as ftmp:
		output = base64.b64encode(ftmp.read()).decode('utf-8')
	response = requests.post(
		'%s/scheduler/job/output' % server,
		json={'id': assignment['id'], 'retval': retval, 'output': output})

	if response.status_code != HTTPStatus.OK:
		return 1
	return 0


def main():
	"""sner agent main"""

	parser = argparse.ArgumentParser()
	parser.add_argument('--debug', action='store_true', help='show debug output')
	parser.add_argument('--workdir', default='/tmp', help='workdir')
	parser.add_argument('--server', default='http://localhost:18000', help='server uri')
	parser.add_argument('--queue', help='select specific queue to work on')
	parser.add_argument('--single', action='store_true', help='do not loop for another assignments')
	parser.add_argument('--assignment', help='manually specified assignment; mostly for debug purposses')
	args = parser.parse_args()
	if args.debug:
		logger.setLevel(logging.DEBUG)
	logger.debug(args)

	os.chdir(args.workdir)

	## manual assignment
	if args.assignment:
		assignment = json.loads(args.assignment)
		if 'id' not in assignment:
			assignment['id'] = str(uuid.uuid4())
		jsonschema.validate(assignment, schema=sner.agent.protocol.assignment)
		(retval, output_file) = process_assignment(assignment)
		logger.debug('processed from command-line: %d, %s', retval, os.path.abspath(output_file))
		return retval

	## fetch and process assignment from server
	while True:
		assignment = get_assignment(args.server, args.queue)
		if assignment:
			(retval, output_file) = process_assignment(assignment)
			upload_output(args.server, assignment, retval, output_file)
		else:
			break
		if args.single:
			break

	return 0


if __name__ == '__main__':
	sys.exit(main())
