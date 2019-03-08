"""sner agent execution modules"""

import json
import logging
import os
import shlex
import signal
import subprocess


class Base():
	"""simple dummy agent module"""

	def __init__(self):
		self.log = logging.getLogger('sner.agent.module.%s' % __class__)
		self.process = None


	def run(self, assignment):
		"""run the agent"""

		with open('assignment.json', 'w+') as ftmp:
			ftmp.write(json.dumps(assignment))
		return 0


	def execute(self, cmd, output_file='output'):
		"""execute command and capture output"""

		with open(output_file, 'w') as output_fd:
			self.process = subprocess.Popen(shlex.split(cmd), stdin=subprocess.DEVNULL, stdout=output_fd, stderr=subprocess.STDOUT, preexec_fn=os.setsid)
			retval = self.process.wait()
			self.process = None
		return retval


	def terminate(self):
		"""terminate executed command"""

		if not self.process:
			return
		self.process.poll()
		if self.process.returncode is None:
			try:
				os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
			except Exception as e:
				self.log.error(e)


class Dummy(Base):
	"""testing agent impl"""
	pass


class Nmap(Base):
	"""nmap wrapper"""

	def run(self, assignment):
		"""run the agent"""

		super().run(assignment)
		with open('targets', 'w') as ftmp:
			ftmp.write('\n'.join(assignment['targets']))
		return self.execute('/usr/bin/nmap -iL targets -oA output %s' % assignment['params'])
