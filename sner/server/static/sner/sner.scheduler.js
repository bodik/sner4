/* This file is part of sner4 project governed by MIT license, see the LICENSE.txt file. */
'use strict;'

class SnerSchedulerComponent extends SnerComponentBase {
	constructor() {
		super();

		this.hbs_source = {
			'excl_controls': `
				<div class="btn-group btn-group-sm">
					<a class="btn btn-outline-secondary" href="{{> scheduler.excl_edit_route excl_id=id}}"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-danger abutton_submit_dataurl_delete" data-url="{{> scheduler.excl_delete_route excl_id=id}}"><i class="fas fa-trash text-danger"></i></a>
				</div>`,

			'task_controls': `
				<div class="btn-group btn-group-sm">
					<a class="btn btn-outline-secondary" href="{{> scheduler.task_edit_route task_id=id}}"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-secondary" href="{{> scheduler.queue_add_route__task_id task_id=id}}">Add queue</a>
					<a class="btn btn-outline-danger abutton_submit_dataurl_delete" data-url="{{> scheduler.task_delete_route task_id=id}}"><i class="fas fa-trash text-danger"></i></a>
				</div>`,

			'queue_controls': `
				<div class="btn-group btn-group-sm">
					<a class="btn btn-outline-secondary" href="{{> scheduler.queue_edit_route queue_id=id}}"><i class="fas fa-edit"></i></a>
					<a class="btn btn-outline-secondary" href="{{> scheduler.queue_enqueue_route queue_id=id}}" title="Put targets to queue">Enqueue</a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_queueflush" href="#" data-url="{{> scheduler.queue_flush_route queue_id=id}}" title="Flush all targets from queue">Flush</a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_queueprune" href="#" data-url="{{> scheduler.queue_prune_route queue_id=id}}" title="Delete all jobs associated with queue">Prune</a>
					<a class="btn btn-outline-secondary abutton_submit_dataurl_delete" data-url="{{> scheduler.queue_delete_route queue_id=id}}"><i class="fas fa-trash text-danger"></i></a>
				</div>`,

			'job_controls': `
				<div class="btn-group btn-group-sm">
					<a class="btn btn-outline-secondary abutton_submit_dataurl_delete" data-url="{{> scheduler.job_delete_route job_id=id}}"><i class="fas fa-trash text-danger"></i></a>
				</div>`,
		};

		super.setup();
	}
}
