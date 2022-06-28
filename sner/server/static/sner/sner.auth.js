/* This file is part of sner4 project governed by MIT license, see the LICENSE.txt file. */
'use strict;'

class SnerAuthComponent extends SnerComponentBase {
	constructor() {
		super();

		this.helpers = {
			'capitalize': function (data) {
				return data.charAt(0).toUpperCase() + data.slice(1).toLowerCase();
			},
		};

		this.hbs_source = {
			'user_controls': `
				<div class="btn-group btn-group-sm">
					<a class="btn btn-outline-secondary" href="{{> auth.user_edit_route user_id=id}}"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_delete" data-url="{{> auth.user_delete_route user_id=id}}"><i class="fas fa-trash text-danger"></i></a>
				</div>`,
			'user_apikey_controls': `{{apikey}} <a class="btn btn-outline-secondary btn-sm abutton_userapikey" data-url="{{> auth.user_apikey_route user_id=user_id action=action}}">{{capitalize action}}</a>`,

			'profile_webauthn_controls': `
				<div class="btn-group btn-group-sm">
					<a class="btn btn-outline-secondary" href="{{> auth.profile_webauthn_edit_route webauthn_id=id}}"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-secondary abutton_sbumit_dataurl_delete" data-url="{{> auth.profile_webauthn_delete_route webauthn_id=id}}"><i class="fas fa-trash text-danger"></i></a>
				</div>`,
		};

		super.setup();
	}
}
