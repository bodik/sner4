"""controller profile"""

from flask import Blueprint, redirect, render_template, url_for
from sner_web.extensions import db
from sner_web.forms import ProfileForm, GenericButtonForm
from sner_web.models import Profile


blueprint = Blueprint('profile', __name__) # pylint: disable=invalid-name


@blueprint.route('/list')
def list_route():
	"""list profiles"""

	profiles = Profile.query.all()
	return render_template('profile/list.html', profiles=profiles, generic_button_form=GenericButtonForm())


@blueprint.route('/add', methods=['GET', 'POST'])
def add_route():
	"""add profile"""

	form = ProfileForm()
	if form.validate_on_submit():
		profile = Profile()
		form.populate_obj(profile)
		db.session.add(profile)
		db.session.commit()
		return redirect(url_for('profile.list_route'))
	return render_template('profile/addedit.html', form=form, form_url=url_for('profile.add_route'))


@blueprint.route('/edit/<profile_id>', methods=['GET', 'POST'])
def edit_route(profile_id):
	"""edit profile"""

	profile = Profile.query.get(profile_id)
	form = ProfileForm(obj=profile)
	if form.validate_on_submit():
		form.populate_obj(profile)
		db.session.commit()
		return redirect(url_for('profile.list_route'))
	return render_template('profile/addedit.html', form=form, form_url=url_for('profile.edit_route', profile_id=profile_id))


@blueprint.route("/delete/<profile_id>", methods=['GET', 'POST'])
def delete_route(profile_id):
	"""delete profile"""

	profile = Profile.query.get(profile_id)
	form = GenericButtonForm()
	if form.validate_on_submit():
		db.session.delete(profile)
		db.session.commit()
		return redirect(url_for('profile.list_route'))
	return render_template('button_delete.html', form=form, form_url=url_for('profile.delete_route', profile_id=profile_id))
