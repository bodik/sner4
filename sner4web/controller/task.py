from flask import Blueprint, redirect, render_template, request, url_for
from sner4web.extensions import db
from sner4web.forms import TaskForm, DeleteButtonForm
from sner4web.models import Task


blueprint = Blueprint("task", __name__)



@blueprint.route("/list")
def list():
	tasks = Task.query.all()
	return render_template("task/list.html", tasks=tasks, task_delete_form=DeleteButtonForm())



@blueprint.route("/add", methods=['GET', 'POST'])
def add():
	form = TaskForm()
	if form.validate_on_submit():
		task = Task()
		form.populate_obj(task)
		db.session.add(task)
		db.session.commit()
		return redirect(url_for("task.list"))
	return render_template("task/addedit.html", form=form, form_url=url_for("task.add"))



@blueprint.route("/edit/<id>", methods=['GET', 'POST'])
def edit(id):
	task = Task.query.get(id)
	form = TaskForm(obj=task)
	if form.validate_on_submit():
		form.populate_obj(task)
		db.session.commit()
		return redirect(url_for("task.list"))
	return render_template("task/addedit.html", form=form, form_url=url_for("task.edit", id=id))



@blueprint.route("/delete/<id>", methods=['GET', 'POST'])
def delete(id):
	task = Task.query.get(id)
	form = DeleteButtonForm()
	if form.validate_on_submit():
		db.session.delete(task)
		db.session.commit()
		return redirect(url_for("task.list"))
	return render_template("deletebutton.html", form=form, form_url=url_for("task.delete", id=id))
