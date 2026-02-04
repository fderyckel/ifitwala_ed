// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/assessment/doctype/task/task.js

frappe.ui.form.on("Task", {
	setup(frm) {
		set_learning_unit_query(frm);
		set_lesson_query(frm);
	},

	refresh(frm) {
		set_learning_unit_query(frm);
		set_lesson_query(frm);
	},

	course(frm) {
		reset_curriculum_fields(frm);
	},

	default_course(frm) {
		reset_curriculum_fields(frm);
	},

	learning_unit(frm) {
		reset_lesson_field(frm);
	},

	default_delivery_mode(frm) {
		enforce_delivery_mode_defaults(frm);
	}
});

function get_course_value(frm) {
	return (frm.doc.course || frm.doc.default_course || "").trim();
}

function set_learning_unit_query(frm) {
	frm.set_query("learning_unit", () => {
		const course = get_course_value(frm);
		if (!course) {
			return {};
		}
		return { filters: { course } };
	});
}

function set_lesson_query(frm) {
	frm.set_query("lesson", () => {
		const learning_unit = (frm.doc.learning_unit || "").trim();
		if (learning_unit) {
			return { filters: { learning_unit } };
		}

		const course = get_course_value(frm);
		if (course) {
			return { filters: { course } };
		}
		return {};
	});
}

function reset_curriculum_fields(frm) {
	if (frm.doc.learning_unit) {
		frm.set_value("learning_unit", null);
	}
	if (frm.doc.lesson) {
		frm.set_value("lesson", null);
	}
	set_learning_unit_query(frm);
	set_lesson_query(frm);
}

function reset_lesson_field(frm) {
	if (frm.doc.lesson) {
		frm.set_value("lesson", null);
	}
	set_lesson_query(frm);
}

function enforce_delivery_mode_defaults(frm) {
	if (frm.doc.default_delivery_mode && frm.doc.default_delivery_mode !== "Assess") {
		if (frm.doc.default_grading_mode !== "None") {
			frm.set_value("default_grading_mode", "None");
		}
		clear_grading_defaults(frm);
	}
}

function clear_grading_defaults(frm) {
	const fields = ["default_max_points", "default_grade_scale", "default_rubric_scoring_strategy"];
	for (const field of fields) {
		if (frm.doc[field]) {
			frm.set_value(field, null);
		}
	}
}
