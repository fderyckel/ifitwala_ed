// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Employee"] = {
	add_fields: ["employment_status", "department", "designation", "employee_image"],
	onload(listview) {
		if (listview.__employee_image_cache) return;
		listview.__employee_image_cache = Object.create(null);
	},
	refresh(listview) {
		const rows = Array.isArray(listview.data) ? listview.data : [];
		const cache = listview.__employee_image_cache || (listview.__employee_image_cache = Object.create(null));
		const visibleNames = rows
			.map((row) => String(row?.name || "").trim())
			.filter(Boolean);
		const missingNames = visibleNames.filter((name) => !(name in cache));

		const applyResolvedImages = () => {
			rows.forEach((row) => {
				const resolved = cache[row.name];
				if (resolved) {
					row.employee_image = resolved;
				}
			});

			const $result = listview.$result;
			if (!$result?.length) return;

			setTimeout(() => {
				$result.find(".list-row-container").each(function () {
					const $row = $(this);
					const docname = ($row.attr("data-name") || "").trim();
					const resolved = cache[docname];
					if (!resolved) return;

					const img = $row.find("img").get(0);
					if (!img) return;
					if (img.getAttribute("src") === resolved) return;
					img.setAttribute("src", resolved);
				});
			}, 0);
		};

		if (!missingNames.length) {
			applyResolvedImages();
			return;
		}

		frappe.call({
			method: "ifitwala_ed.utilities.governed_uploads.get_employee_image_display_map",
			args: { employees: missingNames },
			callback: (r) => {
				Object.assign(cache, r?.message || {});
				applyResolvedImages();
			},
		});
	},
	get_indicator: function (doc) {
		var indicator = [
			__(doc.employment_status),
			frappe.utils.guess_colour(doc.employment_status),
			"employment_status,=," + doc.employment_status,
		];
		indicator[1] = { Active: "green", Inactive: "red", Left: "gray", Suspended: "orange" }[
			doc.employment_status
		];
		return indicator;
	},
};
