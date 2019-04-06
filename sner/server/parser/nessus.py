"""parsers to import from agent outputs to storage"""

import datetime
import json
import sys

from nessus_report_parser import parse_nessus_xml
from nessus_report_parser.model.report_item import ReportItem as nessus_report_ReportItem
from pprint import pprint

from sner.server import db
from sner.server.model.storage import Host, Note, Service, SeverityEnum, Vuln
from sner.server.parser import register_parser


class ReportItemJSONEncoder(json.JSONEncoder):
	"""custom encoder to handle parsed nessus report"""

	def default(self, obj):
		if isinstance(obj, nessus_report_ReportItem):
			return obj.__dict__

		if isinstance(obj, datetime.date):
			return obj.isoformat()

		return super().default(obj)


@register_parser('nessus')
class NessusParser():
	"""nessus .nessus output parser"""

	SEVERITY_MAP = {'0': 'info', '1': 'low', '2': 'medium', '3': 'high', '4': 'critical'}


	@staticmethod
	def import_host(nessushost):
		"""pull host to storage"""

		host = Host.query.filter(Host.address == nessushost['tags']['host-ip']).one_or_none()
		if not host:
			host = Host(address=nessushost['tags']['host-ip'])
			db.session.add(host)

		if (not host.hostname) and nessushost['tags'].get('host-fqdn', None):
			host.hostname = nessushost['tags']['host-fqdn']

		if (not host.os) and nessushost['tags'].get('operating-system', None):
			host.os = nessushost['tags']['operating-system']

		return host


	@staticmethod
	def import_report_item(host, report_item):
		"""import nessus_v2 ReportItem 'element'"""

		report_item['port'] = int(report_item['port']) #TODO: push casting to the parser itself ?

		service = None
		if report_item['port']:
			service = Service.query.filter(Service.host == host, Service.proto == report_item['protocol'], Service.port == report_item['port']).one_or_none()
			if not service:
				service = Service(host=host, proto=report_item['protocol'], port=report_item['port'], name=report_item['service_name'], state='nessus')
				db.session.add(service)

		xtype = 'nessus.%s' % report_item['plugin_id']
		vuln = Vuln.query.filter(Vuln.host == host, Vuln.service == service, Vuln.xtype == xtype).one_or_none()
		if not vuln:
			## create refs, mimic metasploit import
			refs = []
			for ref in report_item.get('cve', []):
				refs.append('%s' % ref)

			for ref in report_item.get('bid', []):
				refs.append('BID-%s' % ref)

			for ref in report_item.get('xref', []):
				refs.append('%s-%s' % tuple(ref.split(':', maxsplit=1)))

			if report_item.get('metasploit_name', None):
				refs.append('MSF-%s' % report_item['metasploit_name'])

			if report_item.get('see_also', None):
				for ref in report_item['see_also'].splitlines():
					refs.append('URL-%s' % ref)

			if report_item.get('plugin_id', None):
				refs.append('NSS-%s' % report_item['plugin_id'])

			## create note with full vulnerability data
			note = Note(
				host=host,
				service=service,
				xtype=xtype,
				data=json.dumps(report_item, cls=ReportItemJSONEncoder))
			db.session.add(note)
			db.session.flush()
			refs.append('SN-%s' % note.id)

			## create vulnerability
			vuln = Vuln(
				host=host,
				service=service,
				xtype=xtype,
				name=report_item['plugin_name'],
				severity=SeverityEnum(NessusParser.SEVERITY_MAP[report_item['severity']]),
				descr="## Synopsis\n\n%s\n\n##Description\n\n%s" % (report_item['synopsis'], report_item['description']),
				data=report_item['plugin_output'],
				refs=refs)
			db.session.add(vuln)

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
		pprint(host["tags"])
		print('## host report_items')
		for item in host["report_items"]:
			print('### item %s' % item['plugin_name'])
			pprint(item)


if __name__ == '__main__':
	debug_parser()
