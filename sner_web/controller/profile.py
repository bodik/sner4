"""profile entity controller"""

from flask import Blueprint, redirect, render_template, url_for
from sner_web.extensions import db
from sner_web.forms import ProfileForm, DeleteButtonForm
from sner_web.models import Profile



blueprint = Blueprint("profile", __name__) # pylint: disable=invalid-name



@blueprint.route("/list")
def list_route():
	"""list profiles"""

	profiles = Profile.query.all()
	return render_template("profile/list.html", profiles=profiles, profile_delete_form=DeleteButtonForm())



@blueprint.route("/add", methods=['GET', 'POST'])
def add_route():
	"""add profile"""

	form = ProfileForm()
	if form.validate_on_submit():
		profile = Profile()
		form.populate_obj(profile)
		db.session.add(profile)
		db.session.commit()
		return redirect(url_for("profile.list_route"))
	return render_template("profile/addedit.html", form=form, form_url=url_for("profile.add_route"))



@blueprint.route("/edit/<id>", methods=['GET', 'POST'])
def edit_route(id): # pylint: disable=redefined-builtin
	"""edit profile"""

	profile = Profile.query.get(id)
	form = ProfileForm(obj=profile)
	if form.validate_on_submit():
		form.populate_obj(profile)
		db.session.commit()
		return redirect(url_for("profile.list_route"))
	return render_template("profile/addedit.html", form=form, form_url=url_for("profile.edit_route", id=id))



@blueprint.route("/delete/<id>", methods=['GET', 'POST'])
def delete_route(id): # pylint: disable=redefined-builtin
	"""delete profile"""

	profile = Profile.query.get(id)
	form = DeleteButtonForm()
	if form.validate_on_submit():
		db.session.delete(profile)
		db.session.commit()
		return redirect(url_for("profile.list_route"))
	return render_template("deletebutton.html", form=form, form_url=url_for("profile.delete_route", id=id))
