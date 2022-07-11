/* This file is part of sner4 project governed by MIT license, see the LICENSE.txt file. */
'use strict';

class SnerStorageComponent extends SnerComponentBase {
	constructor() {
		super();

		this.partials = {
			'storage.service_list_route_filter_info': ['storage.service_list_route', {'filter': 'Service.info ilike "{{filter_value}}%"'}],
			'storage.service_list_route_filter_info_null': ['storage.service_list_route', {'filter': 'Service.info is_null ""'}],
			'storage.vuln_list_route_filter_name': ['storage.vuln_list_route', {'filter': 'Vuln.name=="{{filter_value}}"'}]
		};

		this.helpers = {
			/* generate url for ref; python version used during export must remain in sync */
			'url_for_ref': function(ref) {
				var refgen = {
					'URL': (d) => d,
					'CVE': (d) => 'https://cvedetails.com/cve/CVE-' + d,
					'NSS': (d) => 'https://www.tenable.com/plugins/nessus/' + d,
					'BID': (d) => 'https://www.securityfocus.com/bid/' + d,
					'CERT': (d) => 'https://www.kb.cert.org/vuls/id/' + d,
					'EDB': (d) => 'https://www.exploit-db.com/exploits/' + d.replace('ID-', ''),
					'MSF': (d) => 'https://www.rapid7.com/db/?q=' + d,
					'MSFT': (d) => 'https://technet.microsoft.com/en-us/security/bulletin/' + d,
					'MSKB': (d) => 'https://support.microsoft.com/en-us/help/' + d,
					'SN': (d) => Flask.url_for('storage.note_view_route', {'note_id': d})
				};
				try {
					var matched = ref.match(/(.*?)\-(.*)/);
					return refgen[matched[1]](matched[2])
				} catch (err) {
					//pass
				}
				return '#';
			},
			/* generate text for ref */
			'text_for_ref': function(ref) {
				if (ref.startsWith('URL-')) { return 'URL'; }
				if (ref.startsWith('MSF-')) { return 'MSF'; }
				return ref;
			},
			/* get class for severity label */
			'color_for_severity': function(item) {
				var colors = {
					'unknown': 'badge-secondary',
					'info': 'badge-light',
					'low': 'badge-info',
					'medium': 'badge-primary',
					'high': 'badge-warning',
					'critical': 'badge-danger'
				};
				return (item in colors) ? colors[item] : 'badge-secondary';
			},
			/* get class for tag label */
			'color_for_tag': function(item) {
				var colors = {'todo': 'badge-warning', 'report': 'badge-danger'};
				return (item in colors) ? colors[item] : 'badge-secondary';
			},
			/* simple each helper with sort for flat array-like contexts */
			'each_sorted': function(context, options) {
				return context.sort().map(function(x) { return options.fn(x); }).join('');
			},
			/* generate http links for service with a block helper */
			'links_for_service': function(host_address, host_hostname, service_proto, service_port, options) {
				var ret = '';
				var urls = [];

				if ((service_proto !== null) && (service_port !== null)) {
					urls.push(service_proto + '://' + host_address + ':' + service_port);
					if (host_hostname !== null) {
						urls.push(service_proto + '://' + host_hostname + ':' + service_port);
					}

					if (service_proto === 'tcp') {
						urls.push('http://' + host_address + ':' + service_port);
						urls.push('https://' + host_address + ':' + service_port);
						if (host_hostname !== null) {
							urls.push('http://' + host_hostname + ':' + service_port);
							urls.push('https://' + host_hostname + ':' + service_port);
						}
					}
				}

				urls.forEach((url) => { ret += options.fn({'url': url}); });
				return ret;
			}
		};

		this.hbs_source = {
			'tag_labels': `{{#each_sorted tags}}<span class="badge {{color_for_tag this}} tag-badge">{{this}}</span> {{/each_sorted}}`,

			'host_link': `<a href="{{> storage.host_view_route host_id=host_id}}">{{host_address}}</a>`,
			'host_controls': `
				<div class="btn-group btn-group-sm">
					<div class="btn-group btn-group-sm dropdown dropleft">
						<a class="btn btn-outline-secondary font-weight-bold" data-toggle="dropdown" href="#" title="Show more data"><i class="fa fa-binoculars"></i></a>
						<div class="dropdown-menu">
							<h6 class="dropdown-header">More data</h6>
							<a class="dropdown-item disabled">created: {{this.created}}</a>
							<a class="dropdown-item disabled">modified: {{this.modified}}</a>
							<a class="dropdown-item disabled">rescan_time: {{this.rescan_time}}</a>
						</div>
					</div>
					<a class="btn btn-outline-secondary font-weight-bold" href="{{> storage.service_add_route host_id=id}}" title="Add service">+S</a>
					<a class="btn btn-outline-secondary font-weight-bold" href="{{> storage.vuln_add_route model_name='host' model_id=id}}" title="Add vuln">+V</a>
					<a class="btn btn-outline-secondary font-weight-bold" href="{{> storage.note_add_route model_name='host' model_id=id}}" title="Add note">+N</a>
					<a class="btn btn-outline-secondary" href="{{> storage.host_edit_route host_id=id}}" title="Edit"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_delete" data-url="{{> storage.host_delete_route host_id=id}}" title="Delete"><i class="fas fa-trash text-danger"></i></a>
				</div>`,

			'service_controls': `
				<div class="btn-group btn-group-sm">
					<div class="btn-group btn-group-sm dropdown dropleft">
						<a class="btn btn-outline-secondary font-weight-bold" data-toggle="dropdown" href="#" title="Show more data"><i class="fa fa-binoculars"></i></a>
						<div class="dropdown-menu">
							<h6 class="dropdown-header">More data</h6>
							<a class="dropdown-item disabled">created: {{this.created}}</a>
							<a class="dropdown-item disabled">modified: {{this.modified}}</a>
							<a class="dropdown-item disabled">rescan_time: {{this.rescan_time}}</a>
							<a class="dropdown-item disabled">import_time: {{this.import_time}}</a>
						</div>
					</div>
					<a class="btn btn-outline-secondary font-weight-bold" href="{{> storage.vuln_add_route model_name='service' model_id=id}}" title="Add vuln">+V</a>
					<a class="btn btn-outline-secondary font-weight-bold" href="{{> storage.note_add_route model_name='service' model_id=id}}" title="Add note">+N</a>
					<a class="btn btn-outline-secondary" href="{{> storage.service_edit_route service_id=id}}" title="Edit"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_delete" data-url="{{> storage.service_delete_route service_id=id}}" title="Delete"><i class="fas fa-trash text-danger"></i></a>
				</div>`,
			'service_list_filter_info_link': `
				{{#if info}}
					<a href='{{> storage.service_list_route_filter_info filter_value=info_encoded}}'>{{info}}</a>
				{{else}}
					<em>null</em> <a href='{{> storage.service_list_route_filter_info_null}}'><span class="fas fa-list"></span></a>
				{{/if}}`,
			'service_endpoint_dropdown': `
				{{#if value}}
					<div class="dropdown d-flex">
						<a class="flex-fill" data-toggle="dropdown">{{value}}</a>
						<div class="dropdown-menu">
							<h6 class="dropdown-header">Service endpoint URIs</h6>
							{{#links_for_service host_address host_hostname service_proto service_port}}
								<a class="dropdown-item" rel="noreferrer" href="{{url}}"><i class="fas fa-external-link-alt text-secondary"></i> {{url}}</a>
							{{/links_for_service}}
						</div>
					</div>
				{{/if}}`,

			'vuln_link': `<a href="{{> storage.vuln_view_route vuln_id=id}}">{{name}}</a>`,
			'severity_label': `<span class="badge {{color_for_severity severity}}">{{severity}}</span>`,
			'vuln_refs': `{{#each refs}}<a rel="noreferrer" href="{{url_for_ref this}}">{{text_for_ref this}}</a> {{/each}}`,
			'vuln_controls': `
				<div class="btn-group btn-group-sm">
					<div class="btn-group btn-group-sm dropdown dropleft">
						<a class="btn btn-outline-secondary font-weight-bold" data-toggle="dropdown" href="#" title="Show more data"><i class="fa fa-binoculars"></i></a>
						<div class="dropdown-menu">
							<h6 class="dropdown-header">More data</h6>
							<a class="dropdown-item disabled">created: {{this.created}}</a>
							<a class="dropdown-item disabled">modified: {{this.modified}}</a>
							<a class="dropdown-item disabled">rescan_time: {{this.rescan_time}}</a>
							<a class="dropdown-item disabled">import_time: {{this.import_time}}</a>
						</div>
					</div>
					<a class="btn btn-outline-secondary" href="{{> storage.vuln_edit_route vuln_id=id}}" title="Edit"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_delete" data-url="{{> storage.vuln_delete_route vuln_id=id}}" title="Delete"><i class="fas fa-trash text-danger"></i></a>
				</div>`,
			'vuln_list_filter_name_link': `<a href='{{> storage.vuln_list_route_filter_name filter_value=name_encoded}}'>{{name}}</a>`,

			'note_controls': `
				<div class="btn-group btn-group-sm">
					<div class="btn-group btn-group-sm dropdown dropleft">
						<a class="btn btn-outline-secondary font-weight-bold" data-toggle="dropdown" href="#" title="Show more data"><i class="fa fa-binoculars"></i></a>
						<div class="dropdown-menu">
							<h6 class="dropdown-header">More data</h6>
							<a class="dropdown-item disabled">created: {{this.created}}</a>
							<a class="dropdown-item disabled">modified: {{this.modified}}</a>
							<a class="dropdown-item disabled">import_time: {{this.import_time}}</a>
						</div>
					</div>
					<a class="btn btn-outline-secondary" href="{{> storage.note_view_route note_id=id}}" title="View"><i class="fas fa-eye"></i></a>
					<a class="btn btn-outline-secondary" href="{{> storage.note_edit_route note_id=id}}" title="Edit"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_delete" data-url="{{> storage.note_delete_route note_id=id}}" title="Delete"><i class="fas fa-trash text-danger"></i></a>
				</div>`,
		};

		super.setup();
	}

	/**
	 * tag multiple items
	 *
	 * @param {object} event jquery event. data required: {'dt': datatable instance, 'tag': string}
	 */
	action_tag_multiid(event) {
		var data = Sner.dt.selected_ids_form_data(event.data.dt);
		if ($.isEmptyObject(data)) {
			toastr.warning('No items selected');
			return Promise.resolve();
		}
		data['tag'] = event.target.getAttribute('data-tag');
		data['action'] = event.data.action;
		Sner.submit_form(Flask.url_for(event.data.route_name), data)
			.done(function() { event.data.dt.draw(); });
	}

	/**
	 * delete multiple items
	 *
	 * @param {object} event jquery event. data required {'dt': datatable instance}
	 */
	action_delete_multiid(event) {
		if (!confirm('Really delete?')) { return; }

		var data = Sner.dt.selected_ids_form_data(event.data.dt);
		if ($.isEmptyObject(data)) {
			toastr.warning('No items selected');
			return Promise.resolve();
		}
		Sner.submit_form(Flask.url_for(event.data.route_name), data)
			.done(function() { event.data.dt.draw(); });
	}

	/**
	 * tag item. called from model/view page
	 *
	 * @param {object} event jquery event. data attributes required data-tag_route, data-tag_data
	 */
	action_tag_view(event) {
		var elem = event.target.closest('a');
		var route_name = elem.getAttribute('data-tag_route');
		var data = JSON.parse(elem.getAttribute('data-tag_data'));
		Sner.submit_form(Flask.url_for(route_name), data)
			.done(function() { window.location.reload(); });
	}

	/**
	 * annotate model using modal dialogue, called from datatable context
	 *
	 * @param {object} event jquery event. data required {'dt': datatable instance, 'route_name': annotation route name}
	 */
	action_annotate_dt(event) {
		Sner.storage._action_annotate(
			event.data.route_name,
			event.data.dt.row($(this).parents('tr')).data()['id'],
			function() { event.data.dt.draw('page'); }
		);
	}

	/**
	 * annotate model using modal dialogue, called from model/view page
	 *
	 * @param {object} event jquery event. data required {'dt': datatable instance, 'route_name': annotation route name}
	 */
	action_annotate_view(event) {
		Sner.storage._action_annotate(
			$(this).attr('data-annotate_route'),
			$(this).attr('data-model_id'),
			function() { window.location.reload(); }
		);
	}

	/**
	 * annotate model using modal dialogue implementation
	 *
	 * @param {string}   route_name      annotate route name
	 * @param {string}   model_id        annotated model id
	 * @param {function} after_update_cb content reload callback
	 */
	_action_annotate(route_name, model_id, after_update_cb) {
		$.ajax(Flask.url_for(route_name, {'model_id': model_id}))
			.done(function(data, textStatus, jqXHR) {
				Sner.modal('Annotate', data);
				$('#modal-global .tageditor').tagEditor({'delimiter': '\n'});
				$('#modal-global form').on('submit', function(event) {
					Sner.submit_form($(this).attr('action'), $(this).serializeArray())
						.done(function() {
							after_update_cb();
						})
						.always(function() {
							$('#modal-global').modal('toggle');
						});
					event.preventDefault();
				});
			});
	}
}
