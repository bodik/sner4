"""sner parsers"""


registered_parsers = {} # pylint: disable=invalid-name
def register_parser(name):
	"""register parser class to registry"""

	def register_parser_real(cls):
		if cls not in registered_parsers:
			registered_parsers[name] = cls
		return cls
	return register_parser_real


import sner.server.parser.nmap # pylint: disable=wrong-import-position
