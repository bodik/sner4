"""parsers to import from agent outputs to storage"""

import json
import sys

from pprint import pprint
from nessus_report_parser import parse_nessus_xml

from sner.server import db
from sner.server.parser import register_parser
from sner.server.model.storage import Host, Note, Service, Vuln


@register_parser('nessus')
class NessusParser():
	"""nessus .nessus output parser"""

#	JOB_OUTPUT_DATAFILE = 'output.xml'


	@staticmethod
	def import_host(nessushost):
		"""pull host to storage"""

		host = Host.query.filter(Host.address == nessushost['tags']['host-ip']).one_or_none()
		if not host:
			host = Host(address=nessushost['tags']['host-ip'])
			db.session.add(host)

		if (not host.hostname) and nessushost['tags']['host-fqdn']:
			host.hostname = nessushost['tags']['host-fqdn']
			##TODO: add additional hostnames as notes??

		if (not host.os) and nessushost['tags']['operating-system']:
			host.os = nessushost['tags']['operating-system']
	
		return host


	@staticmethod
	def import_report_item(host, report_item):
		report_item['port'] = int(report_item['port']) #TODO: push casting to the parser itself ?

		service = None
		if report_item['port']:
			service = Service.query.filter(Service.host == host, Service.proto == report_item['protocol'], Service.port == report_item['port']).one_or_none()
			if not service:
				service = Service(host=host, proto=report_item['protocol'], port=report_item['port'], name=report_item['service_name'], state='nessus')
				db.session.add(service)

		xtype = 'nessus.%s' % report_item['plugin_id']
		vuln = Vuln.query.filter(Vuln.host == host, Vuln.xtype == xtype).one_or_none()
		if not vuln:
			vuln = Vuln(
				host=host,
				service=service,
				xtype=xtype,
				name=report_item['plugin_name'],
				severity=report_item['severity'],
				descr="## Synopsis\n\n%s\n##Description\n\n%s" % (report_item['synopsis'], report_item['description']),
				data=report_item['plugin_output'])
			db.session.add(vuln)
			#TODO: refs
			#TODO: note with full data and linked by xtype ?and refs

		return vuln


	@staticmethod
	def data_to_storage(data):
		"""parse data and put/update models in storage"""

		report = parse_nessus_xml(data)['report']
		for ihost in report['hosts']:
			host = NessusParser.import_host(ihost)

			for ireport_item in ihost['report_items']:
				NessusParser.import_report_item(host, ireport_item)

			print('parsed host: %s' % host)
		db.session.commit()


def debug_parser():
	"""cli helper, pull data from report and display"""

	with open(sys.argv[1], 'r') as ftmp:
		report = parse_nessus_xml(ftmp.read())['report']

	for host in report['hosts']:
		print('# host: %s' % host["name"])
		print('## host tags')
		print(host["tags"])
		print('## host report_items')
		for item in host["report_items"]:
			print('### item %s' % item['plugin_name'])
			print(item)


if __name__ == '__main__':
	debug_parser()
