/* This file is part of sner4 project governed by MIT license, see the LICENSE.txt file. */
'use strict;'

class SnerVisualsComponent extends SnerComponentBase {
	/**
	 * modify link preserving other arguments. jQuery each callback.
	 *
	 * @param {integer} index array index
	 * @param {object}  elem  DOM element
	 */
	action_modify_link(index, elem) {
		if (typeof window.url_params === 'undefined') {
			window.url_params = new URLSearchParams(window.location.search);
		}

		var new_params = new URLSearchParams(url_params);
		var [key, val] = elem.getAttribute('data-args').split(':');
		if (val) {
			new_params.set(key, val);
			if (window.url_params.get(key) == val) { $(elem).addClass('active'); }
		} else {
			new_params.delete(key);
			if (!url_params.has(key)) { $(elem).addClass('active'); }
		}
		elem.href = '?' + new_params.toString();
	}
}
