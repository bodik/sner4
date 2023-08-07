/* This file is part of sner4 project governed by MIT license, see the LICENSE.txt file. */
'use strict';

/*
 * sner ui function bundled to simple modules
 *
 * NOTE: While the functions are groupped to ES6 classes, it turns out that the concept of classes 
 * is not very sound in javascript. The main issue might arise when using `this` which is very
 * soft concept here. On the first occurence of troubles (datatables callback this(dt instance)
 * vs. event callbacks this(event element) we should fall back to Revealing Module Pattern immediatelly.
 */


class SnerComponentBase {
	constructor() {
		this.partials = {};
		this.helpers = {};
		this.hbs = {};
	}

	setup() {
		/* register partial routes */
		for (var [name, params] of Object.entries(this.partials)) {
			Handlebars.registerPartial(name, Flask.url_for(...params));
		};
		/* register helpers */
		for (var [name, impl] of Object.entries(this.helpers)) {
			Handlebars.registerHelper(name, impl);
		};
		/* compile templates */
		for (var [name, src] of Object.entries(this.hbs_source)) {
			this.hbs[name] = Handlebars.compile(src);
		};
	}
}

class SnerDatatablesModule {
	constructor() {
		/**
		 * default ajaxed datatables options
		 */
		this.ajax_options = {
			// general settings
			'serverSide': true,
			'processing': true,

			// visuals
			'dom': '<"row"<"col-sm-6"l><"col-sm-6"f>> <"row"<"col-sm-12"p>> <"row"<"col-sm-12"rt>> <"row"<"col-sm-6"i><"col-sm-6"p>>',
			'info': true,
			'paging': true,
			'pageLength': 200,
			'lengthMenu': [ 10, 50, 100, 200, 500, 1000 ],

			// behaviors
			'drawCallback': function (settings) {
				// note this holds a datatable instance here
				Sner.dt.toggle_pagination(this.api());
				this.find('td a.abutton_submit_dataurl_delete').on('click', {'dt': this.api(), 'confirmation': 'Really delete?'}, Sner.action_submit_dataurl);
			},
			'stateSave': true,
			// paging might get broken when transiting from high page of non-filtered table to filtered one with few row, state key must reflect the filter
			'stateSaveCallback': function(settings,data) {
				sessionStorage.setItem('DataTables_'+settings.sInstance+'_'+window.location.pathname+'_'+window.location.search, JSON.stringify(data));
			},
			'stateLoadCallback': function(settings) {
				return JSON.parse(sessionStorage.getItem('DataTables_'+settings.sInstance+'_'+window.location.pathname+'_'+window.location.search));
			}
		};

		/**
		 * default static datatables options
		 */
		this.static_options = {
			'columnDefs': [ {
				'targets': 'no-sort',
				'orderable': false,
			} ],
			'order': [[0, 'asc']],
			'paging': false,
			'info': false
		};
	}

	/**
	 * generate object with default column options and non-html rendering
	 *
	 * @param {string} d - column name
	 * @param {object} extra - extra data to inject into column definition
	 */
	column(d, extra={}) {
		return $.extend({'name': d, 'title': d, 'data': d, 'render': $.fn.dataTable.render.text()}, extra);
	}

	/**
	 * generate _select column definition
	 */
	column_select() {
		return {'name': '_select', 'title': '', 'data': null, 'defaultContent': '', 'orderable': false, 'className': 'select-checkbox'};
	}

	/**
	 * generate _select column definition
	 * @param {callback} render - function to render cell, typically compiled hbs template
	 */
	column_buttons(render_callback=null, extra={}) {
		return $.extend(
			{
				'name': '_buttons',
				'title': '_buttons',
				'data': '_buttons',
				'orderable': false,
				'className': 'dt-nowrap',
				'render': function(data, type, row, meta) { return render_callback(row); }
			},
			extra
		);
	}

	/**
	 * Initializes datatable with additional sorting on 'id' column
	 *
	 * @param {string} selector jQuery selector for table element
	 * @param {Object} options datatable custom options object
	 */
	init_datatable(selector, options) {
		return $(selector)
			.on('preXhr.dt', function (event, settings, data) {
				var id_column = settings.aoColumns.find(function(item) { return item.name === 'id'; });
				if (id_column) {
					data['order'].push({'column': id_column.idx, 'dir': 'asc'});
				}
			})
			.DataTable($.extend({}, Sner.dt.ajax_options, options));
	}

	/**
	 * Select all from table
	 *
	 * @param {Object} event jquery event, event.data.dt datatable instance reference required
	 */
	selectall(event) {
		event.data.dt.rows(null, {'page': 'current'}).select();
	}

	/**
	 * Select none from table
	 *
	 * @param {Object} event jquery event, event.data.dt datatable instance reference required
	 */
	selectnone(event) {
		event.data.dt.rows(null, {'page': 'current'}).deselect();
	}

	/**
	 * toggles pagination if needed
	 *
	 * @param {object} dt - datatable instance
	 */
	toggle_pagination(dt) {
		var pagination = $('#'+dt.table().node().id+'_wrapper .dataTables_paginate');
		if (dt.page.info().pages <= 1) {
			pagination.hide();
		} else {
			pagination.show();
		}
	}

	/**
	 * returns selected row ids as form data
	 *
	 * @param {object} dt - datatable instance
	 */
	selected_ids_form_data(dt) {
		var data = {};
		var i = 0;
		dt.rows({'selected': true}).data().each(function(item) {
			data['ids-'+i] = item['id'];
			i++;
		});
		return data;
	}

	/**
	 * toggle via_target column view in current session via sessionStorage
	 *
	 */
	toggle_viatarget_column_visibility() {
		if (!confirm('Toggle will remove any datatable states and reaload the page. Are you sure?')) { return; }

		sessionStorage.setItem(
			'dt_viatarget_column_visible',
			JSON.stringify(!JSON.parse(sessionStorage.getItem('dt_viatarget_column_visible')))
		);

		/* the saved states must be removed, the save state has precedence over dt initialization values */
		Object.keys(sessionStorage).forEach(function(key) {
			if (key.startsWith('DataTables_')) {
				sessionStorage.removeItem(key);
			}
		});

		location.reload();
	}
}


class SnerModule {
	constructor() {
		/* register all flask-jsglue routes as partials */
		for (var [index, [route_name, route_parts, route_args]] of Object.entries(Flask._endpoints)) {
			var template_context = {};
			route_args.forEach((item) => {
				template_context[item] = `{{${item}}}`;
			});
			Handlebars.registerPartial(route_name, Flask.url_for(route_name, template_context));
		};

		/* create all compound modules and components */
		this.dt = new SnerDatatablesModule();
		this.auth = new SnerAuthComponent();
		this.scheduler = new SnerSchedulerComponent();
		this.storage = new SnerStorageComponent();
		this.visuals = new SnerVisualsComponent();

		/* hook app components startup */
		$(document).ready(function() {
			var dt_static_options = $.extend({}, Sner.dt.static_options, (typeof dt_static_custom !== 'undefined' ? dt_static_custom : {}));
			$('.dt_static').DataTable(dt_static_options);

			$('.tageditor').tagEditor({'delimiter': '\n'});
			$('.render_hbs').each(function(index, elem) { Sner.render_hbs(elem); });

			$('#storage_quickjump_form input[name="quickjump"]').autocomplete({
				'source': Flask.url_for('storage.quickjump_autocomplete_route')
			});
			$('#storage_quickjump_form').on('submit', (event) => {
				event.preventDefault();
				var formdata = {};
				$.each($('#'+event.target.id).serializeArray(), (idx, val) => { formdata[val.name] = val.value; });
				Sner.submit_form(Flask.url_for('storage.quickjump_route'), formdata)
					.done(function(data, textStatus, jqXHR) {
						location.href = data['url'];
					});
			});
		});
	}


	/* WEBAUTHN UTILS */

	/**
	 * encode ArrayBuffer to base64
	 *
	 * @param  {ArrayBuffer} buffer buffer to encode
	 * @return {string}             encoded buffer
	 */
	array_buffer_to_base64(buffer) {
		return btoa(new Uint8Array(buffer).reduce((data, byte) => data + String.fromCharCode(byte), ''));
	}

	/**
	 * decode base64 data to ArrayBuffer
	 *
	 * @param  {string}      data data to decode
	 * @return {ArrayBuffer}      decoded data
	 */
	base64_to_array_buffer(data) {
		return Uint8Array.from(atob(data), c => c.charCodeAt(0)).buffer;
	}


	/* GENERAL UI HELPERS */

	/**
	 * Show global/shared modal with title and bodya
	 *
	 * @param {string} title title html fragment
	 * @param {string} body  body html fragment
	 */
	modal(title, body) {
		$('#modal-global .modal-title').html(title);
		$('#modal-global .modal-body').html(body);
		$('#modal-global').modal();
	}


	/**
	 * Will rerender hbs with context taken from data-hbs attributes.
	 * The element must contain 'data-hbs' attribute (hbs compiled template name) and 'data-hbs_context' attribute (context data encoded in json)
	 *
	 * @param {DOMElement} elem data and output enclosing element reference
	 */
	render_hbs(elem) {
		/**
		 * function resolver helper
		 * https://stackoverflow.com/a/43849204/8326867
		 */
		function _function_by_path(object, path, defaultValue=console.error) { return path.split('.').reduce((o, p) => o ? o[p] : defaultValue, object); };

		var hbs = elem.getAttribute('data-hbs');
		var context = JSON.parse(elem.getAttribute('data-hbs_context'));
		elem.innerHTML = _function_by_path(Sner, hbs)(context);
	}

	/**
	 * Submit form, POST data to url managing csrf token in the process.
	 *
	 * @param {string} url  target url
	 * @param {Object} data object containing data to submit
	 */
	submit_form(url, data={}) {
		data['csrf_token'] = $('meta[name="csrf-token"]').attr('content');
		return $.ajax({"url": url,"type": "POST", "data": data})
			.fail(function(xhr, status, exception) {
				toastr.error(xhr.hasOwnProperty('responseJSON') ? xhr.responseJSON['error']['message'] : 'Request failed');
			});
	}


	/* ACTION FUNCTIONS, BUTTON EVENT HANDLERS */

	/**
	 * submit form to data-url of an A element with confirmation dialogue
	 *
	 * @param {object} event jquery event. data required {'dt': datatable instance, 'confirmation': string}
	 */
	action_submit_dataurl(event) {
		var confirmation = event.data.hasOwnProperty('confirmation') ? event.data.confirmation : 'Are you sure?';
		if (!confirm(confirmation)) { return; }

		Sner.submit_form(event.target.closest('a').getAttribute('data-url'))
			.always(function() { event.data.dt.draw(); });
	}
}
