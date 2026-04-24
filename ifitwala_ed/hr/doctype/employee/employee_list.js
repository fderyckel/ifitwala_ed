// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

const DEFAULT_EMPLOYEE_AVATAR_DATA_URL = `data:image/svg+xml;utf8,${encodeURIComponent(
	'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" fill="none"><rect width="96" height="96" rx="48" fill="#E5E7EB"/><circle cx="48" cy="35" r="16" fill="#9CA3AF"/><path d="M20 78c6-16 18-24 28-24s22 8 28 24" fill="#9CA3AF"/></svg>',
)}`;
const EMPLOYEE_IMAGE_RETRY_MS = 5000;

frappe.listview_settings["Employee"] = {
	add_fields: ["employment_status", "department", "designation", "employee_image"],
	onload(listview) {
		if (listview.__employee_image_cache) return;
		listview.__employee_image_cache = Object.create(null);
	},
	refresh(listview) {
		const rows = Array.isArray(listview.data) ? listview.data : [];
		const cache = listview.__employee_image_cache || (listview.__employee_image_cache = Object.create(null));
		const now = Date.now();
		const getCacheEntry = (name) => {
			const entry = cache[name];
			if (!entry) return null;
			if (typeof entry === "string") {
				return { url: entry, retryAfter: 0 };
			}
			return entry;
		};
		const visibleNames = rows
			.map((row) => String(row?.name || "").trim())
			.filter(Boolean);
		const missingNames = visibleNames.filter((name) => {
			const entry = getCacheEntry(name);
			if (!entry) return true;
			if (entry.url) return false;
			return now >= Number(entry.retryAfter || 0);
		});

		const applyResolvedImages = () => {
			rows.forEach((row) => {
				const entry = getCacheEntry(row.name);
				if (entry) {
					row.employee_image = entry.url || DEFAULT_EMPLOYEE_AVATAR_DATA_URL;
				}
			});

			const $result = listview.$result;
			if (!$result?.length) return;

			setTimeout(() => {
				$result.find(".list-row-container").each(function () {
					const $row = $(this);
					const docname = ($row.attr("data-name") || "").trim();
					const entry = getCacheEntry(docname);
					if (!entry) return;
					const nextSrc = entry.url || DEFAULT_EMPLOYEE_AVATAR_DATA_URL;

					const img = $row.find("img").get(0);
					if (!img) return;
					if (img.getAttribute("src") === nextSrc) return;
					img.setAttribute("src", nextSrc);
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
				Object.entries(r?.message || {}).forEach(([name, url]) => {
					const resolvedUrl = String(url || "").trim();
					cache[name] = {
						url: resolvedUrl,
						retryAfter: resolvedUrl ? 0 : Date.now() + EMPLOYEE_IMAGE_RETRY_MS,
					};
				});
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
