/* This file is part of sner4 project governed by MIT license, see the LICENSE.txt file. */
'use strict';

class SnerStorageComponent extends SnerComponentBase {
	constructor() {
		super();

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
				var colors = {'todo': 'badge-warning', 'report': 'badge-danger', 'report:data': 'badge-danger'};
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
			},
			/* generate filter url with properly encoded vuln.name */
			'vuln_list_route_filter_name': function(name) {
				return Flask.url_for(
					"storage.vuln_list_route",
					{"filter": "Vuln.name==" + Sner.storage.encodeRFC3986URIComponent(JSON.stringify(name))}
				);
			},
			/* generate filter url with properly encoded ILIKE pattern */
			'service_list_route_filter_info': function(info) {
				if (info == null) {
					var filter_value = 'Service.info is_null ""';
				} else {
					var filter_value = 'Service.info ilike ' + Sner.storage.encodeRFC3986URIComponent(JSON.stringify(info.replace(/\\/g, '\\\\')  + '%'));
				}
				return Flask.url_for('storage.service_list_route', {'filter': filter_value});
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
				<a href="{{service_list_route_filter_info info}}">
				{{#if info}}
					{{info}}
				{{else}}
					<em>null</em> <i class="fas fa-exclamation-circle text-warning"></i>
				{{/if}}
				</a>`,
			'service_endpoint_dropdown': `
				{{#if value}}
					<div class="dropdown d-flex">
						<a class="flex-fill" data-toggle="dropdown">{{value}}</a>
						<div class="dropdown-menu">
							<h6 class="dropdown-header">Service endpoint URIs</h6>
							{{#links_for_service host_address host_hostname service_proto service_port}}
								<span class="dropdown-item">
								<i 
									class="far fa-clipboard"
									onclick="Sner.storage.action_service_endpoint_clipboard(event)"
									data="{{url}}"
									title="Copy to clipboard"
								></i> 
								<a rel="noreferrer" href="{{url}}">{{url}}</a>
								</span>
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
					<a class="btn btn-outline-secondary" href="{{> storage.vuln_multicopy_route vuln_id=id}}" title="Multicopy"><i class="far fa-copy"></i></a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_delete" data-url="{{> storage.vuln_delete_route vuln_id=id}}" title="Delete"><i class="fas fa-trash text-danger"></i></a>
				</div>`,
			'vuln_list_filter_name_link': `<a href="{{vuln_list_route_filter_name name}}">{{name}}</a>`,

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
			'modal_freetag_multiid': `
				<form>
					<div class="form-group row">
						<div class="col-sm"><textarea class="form-control tageditor" name="tags" placeholder="Tags"></textarea></div>
					</div>
					<div class="form-group row">
						<div class="col-sm"><input class="btn btn-primary" name="submit" type="submit" value="Save"></div>
					</div>
				</form>`,
		};

		super.setup();
	}

	/**
	 * percent encode string as much as possible fo use within URI
	 * ref: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/encodeURIComponent#encoding_for_rfc3986
	 */
	encodeRFC3986URIComponent(str) {
		const reservedChars = /[!'()*]/g;
		return encodeURIComponent(str).replace(reservedChars, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
	}

	/**
	 * tag multiple items
	 *
	 * @param {object} event jquery event. data required: {'dt': datatable instance, 'tag': string, 'action': string}
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
	 * free-form tag multiple items with multiple tags
	 *
	 * @param {object} event jquery event. data required: {'dt': datatable instance, 'tag': string, 'action': string}
	 */
	action_freetag_multiid(event) {
		var data = Sner.dt.selected_ids_form_data(event.data.dt);
		if ($.isEmptyObject(data)) {
			toastr.warning('No items selected');
			return Promise.resolve();
		}

		var action_text = event.data.action == 'set' ? 'Tag' : 'Untag';
		Sner.modal(`${action_text} multiple items`, Sner.storage.hbs.modal_freetag_multiid);
		$('#modal-global .tageditor').tagEditor({'delimiter': '\n'});

		$('#modal-global form').on('submit', function(event_submit) {
			data['tag'] = this.elements["tags"].value;
			data['action'] = event.data.action;
			Sner.submit_form(Flask.url_for(event.data.route_name), data)
				.done(function() {
					event.data.dt.draw();
				})
				.always(function() {
					$('#modal-global').modal('toggle');
				});
			event_submit.preventDefault();
		});
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

	/**
	 * copy service endpoint string from element data
	 *
	 * @param {object} event jquery event
	 */
	action_service_endpoint_clipboard(event) {
		navigator.clipboard.writeText(event.target.getAttribute("data"));
		toastr.warning('Copied to clipboard.');
		event.preventDefault();
	}
}
