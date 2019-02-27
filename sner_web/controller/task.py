"""controller task"""

from flask import Blueprint, redirect, render_template, url_for
from sner_web.extensions import db
from sner_web.forms import DeleteButtonForm, GenericButtonForm, TaskForm
from sner_web.models import Profile, Task



blueprint = Blueprint("task", __name__) # pylint: disable=invalid-name



@blueprint.route("/list")
def list_route():
	"""list tasks"""

	tasks = Task.query.all()
	return render_template("task/list.html", tasks=tasks, generic_button_form=GenericButtonForm())



@blueprint.route("/add", methods=['GET', 'POST'])
@blueprint.route("/add/<profile_id>", methods=['GET', 'POST'])
def add_route(profile_id=None):
	"""add task"""

	form = TaskForm(profile=Profile.query.filter(Profile.id==profile_id).one_or_none())

	if form.validate_on_submit():
		task = Task()
		form.populate_obj(task)
		db.session.add(task)
		db.session.commit()
		return redirect(url_for("task.list_route"))

	return render_template("task/addedit.html", form=form, form_url=url_for("task.add_route"))



@blueprint.route("/edit/<id>", methods=['GET', 'POST'])
def edit_route(id): # pylint: disable=redefined-builtin
	"""edit task"""

	task = Task.query.get(id)
	form = TaskForm(obj=task)

	if form.validate_on_submit():
		form.populate_obj(task)
		db.session.commit()
		return redirect(url_for("task.list_route"))

	return render_template("task/addedit.html", form=form, form_url=url_for("task.edit_route", id=id))



@blueprint.route("/delete/<id>", methods=['GET', 'POST'])
def delete_route(id): # pylint: disable=redefined-builtin
	"""delete task"""

	task = Task.query.get(id)
	form = GenericButtonForm()

	if form.validate_on_submit():
		db.session.delete(task)
		db.session.commit()
		return redirect(url_for("task.list_route"))

	return render_template("button_delete.html", form=form, form_url=url_for("task.delete_route", id=id))
