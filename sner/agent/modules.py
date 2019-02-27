"""sner agent execution modules"""

import json


class Dummy():
	"""simple dummy agent module"""

	def __init__(self, assignment):
		self.assignment = assignment

	def run(self):
		"""run the agent"""

		with open('assignment.json', 'w+') as ftmp:
			ftmp.write(json.dumps(self.assignment))
		return 0
