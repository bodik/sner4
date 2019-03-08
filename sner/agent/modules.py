"""sner agent execution modules"""

import json
import shlex
import subprocess


class Base():
	"""simple dummy agent module"""

	def __init__(self, assignment):
		self.assignment = assignment

	def run(self):
		"""run the agent"""

		with open('assignment.json', 'w+') as ftmp:
			ftmp.write(json.dumps(self.assignment))
		return 0

	@staticmethod
	def execute(cmd, output_file='output'):
		"""execute command and capture output"""

		with open(output_file, 'w') as output_fd:
			retval = subprocess.run(shlex.split(cmd), stdout=output_fd, stderr=subprocess.STDOUT, check=False).returncode
		return retval


class Dummy(Base):
	"""testing agent impl"""
	pass


class Nmap(Base):
	"""nmap wrapper"""

	def run(self):
		"""run the agent"""

		super().run()
		with open('targets', 'w') as ftmp:
			ftmp.write('\n'.join(self.assignment['targets']))
		return self.__class__.execute('/usr/bin/nmap -iL targets -oA output %s' % self.assignment['params'])
