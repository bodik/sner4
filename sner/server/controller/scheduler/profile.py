"""controller profile"""

from flask import redirect, render_template, url_for
from sner.server.controller.scheduler import blueprint
from sner.server.extensions import db
from sner.server.form import GenericButtonForm
from sner.server.form.scheduler import ProfileForm
from sner.server.model.scheduler import Profile


@blueprint.route('/profile/list')
def profile_list_route():
	"""list profiles"""

	profiles = Profile.query.all()
	return render_template('scheduler/profile/list.html', profiles=profiles, generic_button_form=GenericButtonForm())


@blueprint.route('/profile/add', methods=['GET', 'POST'])
def profile_add_route():
	"""add profile"""

	form = ProfileForm()
	if form.validate_on_submit():
		profile = Profile()
		form.populate_obj(profile)
		db.session.add(profile)
		db.session.commit()
		return redirect(url_for('scheduler.profile_list_route'))
	return render_template('scheduler/profile/addedit.html', form=form, form_url=url_for('scheduler.profile_add_route'))


@blueprint.route('/profile/edit/<profile_id>', methods=['GET', 'POST'])
def profile_edit_route(profile_id):
	"""edit profile"""

	profile = Profile.query.get(profile_id)
	form = ProfileForm(obj=profile)
	if form.validate_on_submit():
		form.populate_obj(profile)
		db.session.commit()
		return redirect(url_for('scheduler.profile_list_route'))
	return render_template('scheduler/profile/addedit.html', form=form, form_url=url_for('scheduler.profile_edit_route', profile_id=profile_id))


@blueprint.route('/profile/delete/<profile_id>', methods=['GET', 'POST'])
def profile_delete_route(profile_id):
	"""delete profile"""

	profile = Profile.query.get(profile_id)
	form = GenericButtonForm()
	if form.validate_on_submit():
		db.session.delete(profile)
		db.session.commit()
		return redirect(url_for('scheduler.profile_list_route'))
	return render_template('button_delete.html', form=form, form_url=url_for('scheduler.profile_delete_route', profile_id=profile_id))
