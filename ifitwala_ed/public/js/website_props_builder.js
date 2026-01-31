// ifitwala_ed/public/js/website_props_builder.js

(() => {
	if (!window.frappe) return;

	const DEFAULTS_BY_BLOCK = {
		hero: {
			autoplay: true,
			interval: 5000,
			variant: "default"
		},
		admissions_overview: {
			max_width: "normal"
		},
		admissions_steps: {
			layout: "horizontal"
		},
		admission_cta: {
			style: "primary",
			label_override: null,
			icon: null,
			tracking_id: null
		},
		faq: {
			enable_schema: true,
			collapsed_by_default: true
		},
		rich_text: {
			max_width: "normal"
		},
		content_snippet: {
			allow_override: false
		},
		program_list: {
			school_scope: "current",
			show_intro: false,
			card_style: "standard",
			limit: 6
		},
		program_intro: {
			cta_intent: null
		},
		leadership: {
			limit: 4,
			roles: []
		}
	};

	function toLabel(name) {
		if (!name) return "";
		return name
			.replace(/_/g, " ")
			.replace(/\b\w/g, (m) => m.toUpperCase());
	}

	function deepClone(value) {
		return JSON.parse(JSON.stringify(value || {}));
	}

	function parseJson(text) {
		if (!text || !text.trim()) {
			return { value: {}, error: null };
		}
		try {
			return { value: JSON.parse(text), error: null };
		} catch (err) {
			return { value: {}, error: err };
		}
	}

	function normalizeSchemaType(schema) {
		const raw = schema && schema.type ? schema.type : "string";
		const types = Array.isArray(raw) ? raw : [raw];
		const nullable = types.includes("null");
		const primary = types.find((t) => t !== "null") || types[0];
		return { primary, nullable };
	}

	function isMultiline(fieldname) {
		const lower = (fieldname || "").toLowerCase();
		return (
			lower.includes("content") ||
			lower.includes("html") ||
			lower.includes("description") ||
			lower.includes("bio") ||
			lower.includes("text")
		);
	}

	function applyDefaults(schema, values, blockType) {
		const output = {};
		const incoming = values || {};
		const props = (schema && schema.properties) || {};
		const required = new Set(schema && schema.required ? schema.required : []);
		const defaults = DEFAULTS_BY_BLOCK[blockType] || {};

		Object.keys(props).forEach((key) => {
			if (incoming[key] !== undefined) {
				output[key] = deepClone(incoming[key]);
				return;
			}
			if (output[key] !== undefined) {
				return;
			}
			const propSchema = props[key] || {};
			const { primary } = normalizeSchemaType(propSchema);

			if (Object.prototype.hasOwnProperty.call(defaults, key)) {
				output[key] = deepClone(defaults[key]);
				return;
			}
			if (propSchema.default !== undefined) {
				output[key] = deepClone(propSchema.default);
				return;
			}
			if (Array.isArray(propSchema.enum) && propSchema.enum.length) {
				output[key] = propSchema.enum[0];
				return;
			}
			if (primary === "boolean") {
				output[key] = false;
				return;
			}
			if (primary === "array") {
				output[key] = [];
				return;
			}
			if (primary === "string" && required.has(key)) {
				output[key] = "";
				return;
			}
		});

		return output;
	}

	function buildDefaultObject(schema) {
		const props = (schema && schema.properties) || {};
		const required = new Set(schema && schema.required ? schema.required : []);
		const output = {};
		Object.keys(props).forEach((key) => {
			const propSchema = props[key] || {};
			const { primary } = normalizeSchemaType(propSchema);
			if (propSchema.default !== undefined) {
				output[key] = deepClone(propSchema.default);
				return;
			}
			if (Array.isArray(propSchema.enum) && propSchema.enum.length) {
				output[key] = propSchema.enum[0];
				return;
			}
			if (primary === "boolean") {
				output[key] = false;
				return;
			}
			if (primary === "array") {
				output[key] = [];
				return;
			}
			if (primary === "string" && required.has(key)) {
				output[key] = "";
				return;
			}
		});
		return output;
	}

	function validateAgainstSchema(schema, data) {
		const errors = [];
		if (!schema || schema.type !== "object") {
			return errors;
		}

		const props = schema.properties || {};
		const required = new Set(schema.required || []);
		const allowExtra = schema.additionalProperties !== false;

		Object.keys(data || {}).forEach((key) => {
			if (!props[key] && !allowExtra) {
				errors.push(`Unexpected property: ${key}`);
			}
		});

		Object.keys(props).forEach((key) => {
			const propSchema = props[key] || {};
			const value = data ? data[key] : undefined;
			const { primary } = normalizeSchemaType(propSchema);

			if (required.has(key) && (value === undefined || value === null || value === "")) {
				errors.push(`Missing required field: ${key}`);
				return;
			}
			if (value === undefined || value === null || value === "") {
				return;
			}
			if (primary === "integer" && Number.isNaN(Number(value))) {
				errors.push(`Field ${key} must be a number.`);
			}
			if (Array.isArray(propSchema.enum) && !propSchema.enum.includes(value)) {
				errors.push(`Field ${key} must be one of: ${propSchema.enum.join(", ")}`);
			}
			if (primary === "array" && Array.isArray(value)) {
				if (propSchema.minItems && value.length < propSchema.minItems) {
					errors.push(`Field ${key} must have at least ${propSchema.minItems} items.`);
				}
				if (propSchema.items && propSchema.items.type === "object") {
					const itemProps = propSchema.items.properties || {};
					const itemRequired = new Set(propSchema.items.required || []);
					const itemAllowExtra = propSchema.items.additionalProperties !== false;
					value.forEach((item, idx) => {
						Object.keys(item || {}).forEach((itemKey) => {
							if (!itemProps[itemKey] && !itemAllowExtra) {
								errors.push(`Field ${key}[${idx}] has unexpected property: ${itemKey}`);
							}
						});
						itemRequired.forEach((itemKey) => {
							const itemValue = item ? item[itemKey] : undefined;
							if (itemValue === undefined || itemValue === null || itemValue === "") {
								errors.push(`Field ${key}[${idx}] missing required: ${itemKey}`);
							}
						});
					});
				}
			}
		});

		return errors;
	}

	function createInput({ label, value, type, options, required, nullable }) {
		const wrapper = document.createElement("div");
		wrapper.className = "form-group";

		const labelEl = document.createElement("label");
		labelEl.className = "control-label";
		labelEl.textContent = label + (required ? " *" : "");
		wrapper.appendChild(labelEl);

		let input;
		if (type === "select") {
			input = document.createElement("select");
			input.className = "form-control";
			if (nullable) {
				const option = document.createElement("option");
				option.value = "";
				option.textContent = __("None");
				input.appendChild(option);
			}
			(options || []).forEach((opt) => {
				const option = document.createElement("option");
				option.value = opt;
				option.textContent = opt;
				input.appendChild(option);
			});
			if (value !== undefined && value !== null) {
				input.value = value;
			}
		} else if (type === "checkbox") {
			input = document.createElement("input");
			input.type = "checkbox";
			input.className = "form-check-input";
			input.checked = Boolean(value);
			labelEl.className = "form-check-label";
			wrapper.className = "form-group form-check";
		} else if (type === "textarea") {
			input = document.createElement("textarea");
			input.className = "form-control";
			input.rows = 4;
			input.value = value || "";
		} else {
			input = document.createElement("input");
			input.type = type === "number" ? "number" : "text";
			input.className = "form-control";
			if (value !== undefined && value !== null) {
				input.value = value;
			}
		}

		wrapper.appendChild(input);
		return { wrapper, input };
	}

	function openPropsBuilder({ frm, cdt, cdn, blockType }) {
		if (!blockType) {
			frappe.msgprint(__("Select a block type first."));
			return;
		}
		frappe.db
			.get_value("Website Block Definition", { block_type: blockType }, ["props_schema", "label"])
			.then((res) => {
				const data = res && res.message ? res.message : {};
				const schemaText = data.props_schema || "{}";
				const parsedSchema = parseJson(schemaText);
				if (parsedSchema.error) {
					frappe.msgprint(__("Block schema is invalid JSON."));
					return;
				}

				const row = locals[cdt][cdn];
				const parsedProps = parseJson(row.props);
				const schema = parsedSchema.value || {};
				const propsKeys = schema.properties ? Object.keys(schema.properties) : [];
				const extraKeys = Object.keys(parsedProps.value || {}).filter(
					(key) => !propsKeys.includes(key)
				);
				if (extraKeys.length && schema.additionalProperties === false) {
					frappe.msgprint(
						__(
							"Some props are not supported and will be ignored: {0}"
						).format(extraKeys.join(", "))
					);
				}
				const initial = applyDefaults(schema, parsedProps.value || {}, blockType);
				const dialog = buildDialog({
					blockType,
					blockLabel: data.label || blockType,
					schema,
					initial,
					rawText: row.props || ""
				});

				if (parsedProps.error) {
					dialog.set_value("use_raw", 1);
					dialog.get_field("raw_json").set_value(row.props || "");
					frappe.msgprint(
						__(
							"Existing props are invalid JSON. Fix them in the JSON editor, then save."
						)
					);
				}

				dialog.set_primary_action(__("Save Props"), () => {
					const useRaw = dialog.get_value("use_raw");
					const schema = parsedSchema.value || {};
					let payload;

					if (useRaw) {
						const raw = dialog.get_value("raw_json") || "";
						const parsed = parseJson(raw);
						if (parsed.error) {
							frappe.msgprint(__("Invalid JSON. Please fix it before saving."));
							return;
						}
						payload = parsed.value || {};
					} else {
						payload = dialog.__builder.getValue();
					}

					const errors = validateAgainstSchema(schema, payload);
					if (errors.length) {
						frappe.msgprint({
							message: __("Props validation failed:<br>{0}").format(errors.join("<br>")),
							indicator: "red"
						});
						return;
					}

					frappe.model.set_value(cdt, cdn, "props", JSON.stringify(payload, null, 2));
					dialog.hide();
				});

				dialog.show();
			});
	}

	function buildDialog({ blockType, blockLabel, schema, initial, rawText }) {
		const dialog = new frappe.ui.Dialog({
			title: __("Props Builder: {0}").format(blockLabel || blockType),
			fields: [
				{ fieldname: "builder", fieldtype: "HTML" },
				{
					fieldname: "use_raw",
					fieldtype: "Check",
					label: __("Edit JSON manually"),
					default: 0
				},
				{
					fieldname: "raw_json",
					fieldtype: "Code",
					label: __("Props (JSON)"),
					options: "JSON"
				}
			]
		});

		const rawField = dialog.get_field("raw_json");
		rawField.set_value(rawText || JSON.stringify(initial || {}, null, 2));
		rawField.$wrapper.hide();

		const builder = createBuilder({
			container: dialog.get_field("builder").$wrapper.get(0),
			schema,
			initial
		});
		dialog.__builder = builder;

		const toggleRaw = () => {
			const useRaw = dialog.get_value("use_raw");
			if (useRaw) {
				rawField.$wrapper.show();
				rawField.set_value(JSON.stringify(builder.getValue(), null, 2));
				builder.setDisabled(true);
			} else {
				const parsed = parseJson(rawField.get_value());
				if (parsed.error) {
					frappe.msgprint(__("Invalid JSON. Please fix it before switching back."));
					dialog.set_value("use_raw", 1);
					return;
				}
				builder.setValue(parsed.value || {});
				rawField.$wrapper.hide();
				builder.setDisabled(false);
			}
		};

		dialog.get_field("use_raw").$input.on("change", toggleRaw);
		builder.onChange((value) => {
			if (!dialog.get_value("use_raw")) {
				rawField.set_value(JSON.stringify(value || {}, null, 2));
			}
		});

		return dialog;
	}

	function createBuilder({ container, schema, initial }) {
		const wrapper = document.createElement("div");
		wrapper.className = "iw-props-builder";
		container.innerHTML = "";
		container.appendChild(wrapper);

		const state = deepClone(initial || {});
		const properties = schema.properties || {};
		const required = new Set(schema.required || []);
		const changeHandlers = [];
		let isDisabled = false;

		const notify = () => {
			changeHandlers.forEach((handler) => handler(deepClone(state)));
		};

		const setDisabled = (disabled) => {
			isDisabled = disabled;
			const inputs = wrapper.querySelectorAll("input, textarea, select, button");
			inputs.forEach((input) => {
				if (input.classList.contains("iw-array-add") || input.classList.contains("iw-array-remove")) {
					input.disabled = disabled;
					return;
				}
				input.disabled = disabled;
			});
		};

		const renderPrimitiveField = (propName, propSchema) => {
			const { primary, nullable } = normalizeSchemaType(propSchema);
			const label = toLabel(propName);
			const isRequired = required.has(propName);
			const value = state[propName];
			let fieldType = "text";
			let options = null;

			if (Array.isArray(propSchema.enum)) {
				fieldType = "select";
				options = propSchema.enum.filter((item) => item !== null);
			} else if (primary === "integer") {
				fieldType = "number";
			} else if (primary === "boolean") {
				fieldType = "checkbox";
			} else if (primary === "string" && isMultiline(propName)) {
				fieldType = "textarea";
			}

			const { wrapper: fieldWrap, input } = createInput({
				label,
				value,
				type: fieldType,
				options,
				required: isRequired,
				nullable
			});

			input.addEventListener("input", () => {
				if (isDisabled) return;
				let nextValue;
				if (fieldType === "checkbox") {
					nextValue = input.checked;
				} else if (fieldType === "number") {
					nextValue = input.value === "" ? (nullable ? null : "") : Number(input.value);
				} else {
					nextValue = input.value;
					if (nullable && nextValue === "") {
						nextValue = null;
					}
				}
				state[propName] = nextValue;
				notify();
			});

			wrapper.appendChild(fieldWrap);
		};

		const renderArrayField = (propName, propSchema) => {
			const { primary } = normalizeSchemaType(propSchema);
			if (primary !== "array") {
				return;
			}

			const label = toLabel(propName);
			const section = document.createElement("div");
			section.className = "iw-array-section";

			const header = document.createElement("div");
			header.className = "iw-array-header";
			const title = document.createElement("label");
			title.className = "control-label";
			title.textContent = label;
			header.appendChild(title);

			const addButton = document.createElement("button");
			addButton.type = "button";
			addButton.className = "btn btn-xs btn-default iw-array-add";
			addButton.textContent = __("Add item");
			header.appendChild(addButton);
			section.appendChild(header);

			const list = document.createElement("div");
			list.className = "iw-array-list";
			section.appendChild(list);
			wrapper.appendChild(section);

			const itemSchema = propSchema.items || {};
			const itemType = normalizeSchemaType(itemSchema).primary || "string";

			const renderList = () => {
				list.innerHTML = "";
				const items = Array.isArray(state[propName]) ? state[propName] : [];
				items.forEach((item, index) => {
					const row = document.createElement("div");
					row.className = "iw-array-item";

					const removeBtn = document.createElement("button");
					removeBtn.type = "button";
					removeBtn.className = "btn btn-xs btn-default iw-array-remove";
					removeBtn.textContent = __("Remove");
					removeBtn.addEventListener("click", () => {
						if (isDisabled) return;
						items.splice(index, 1);
						state[propName] = items;
						renderList();
						notify();
					});

					if (itemType === "object") {
						const itemBox = document.createElement("div");
						itemBox.className = "iw-array-item-box";
						const itemProps = itemSchema.properties || {};
						const itemRequired = new Set(itemSchema.required || []);
						Object.keys(itemProps).forEach((itemKey) => {
							const fieldSchema = itemProps[itemKey] || {};
							const fieldLabel = toLabel(itemKey);
							const typeInfo = normalizeSchemaType(fieldSchema);
							const fieldType = typeInfo.primary;
							const fieldNullable = typeInfo.nullable;
							const fieldEnum = Array.isArray(fieldSchema.enum) ? fieldSchema.enum : null;
							let inputType = "text";
							let options = null;
							if (fieldEnum) {
								inputType = "select";
								options = fieldEnum.filter((opt) => opt !== null);
							} else if (fieldType === "integer") {
								inputType = "number";
							} else if (fieldType === "boolean") {
								inputType = "checkbox";
							} else if (fieldType === "string" && isMultiline(itemKey)) {
								inputType = "textarea";
							}

							const { wrapper: fieldWrap, input } = createInput({
								label: fieldLabel,
								value: item[itemKey],
								type: inputType,
								options,
								required: itemRequired.has(itemKey),
								nullable: fieldNullable
							});

							input.addEventListener("input", () => {
								if (isDisabled) return;
								let nextValue;
								if (inputType === "checkbox") {
									nextValue = input.checked;
								} else if (inputType === "number") {
									nextValue = input.value === "" ? "" : Number(input.value);
								} else {
									nextValue = input.value;
									if (fieldNullable && nextValue === "") {
										nextValue = null;
									}
								}
								item[itemKey] = nextValue;
								state[propName][index] = item;
								notify();
							});

							itemBox.appendChild(fieldWrap);
						});
						itemBox.appendChild(removeBtn);
						row.appendChild(itemBox);
					} else {
						const { wrapper: fieldWrap, input } = createInput({
							label: toLabel(propName),
							value: item,
							type: itemType === "integer" ? "number" : "text",
							required: false
						});
						input.addEventListener("input", () => {
							if (isDisabled) return;
							let nextValue = input.value;
							if (itemType === "integer") {
								nextValue = input.value === "" ? "" : Number(input.value);
							}
							items[index] = nextValue;
							state[propName] = items;
							notify();
						});
						row.appendChild(fieldWrap);
						row.appendChild(removeBtn);
					}
					list.appendChild(row);
				});
			};

			addButton.addEventListener("click", () => {
				if (isDisabled) return;
				const items = Array.isArray(state[propName]) ? state[propName] : [];
				if (itemType === "object") {
					items.push(buildDefaultObject(itemSchema));
				} else if (itemType === "integer") {
					items.push(0);
				} else {
					items.push("");
				}
				state[propName] = items;
				renderList();
				notify();
			});

			renderList();
		};

		Object.keys(properties).forEach((propName) => {
			const propSchema = properties[propName] || {};
			const { primary } = normalizeSchemaType(propSchema);
			if (primary === "array") {
				renderArrayField(propName, propSchema);
			} else {
				renderPrimitiveField(propName, propSchema);
			}
		});

		return {
			getValue: () => deepClone(state),
			setValue: (value) => {
				Object.keys(state).forEach((key) => delete state[key]);
				Object.assign(state, deepClone(value || {}));
				wrapper.innerHTML = "";
				Object.keys(properties).forEach((propName) => {
					const propSchema = properties[propName] || {};
					const { primary } = normalizeSchemaType(propSchema);
					if (primary === "array") {
						renderArrayField(propName, propSchema);
					} else {
						renderPrimitiveField(propName, propSchema);
					}
				});
				notify();
			},
			onChange: (handler) => changeHandlers.push(handler),
			setDisabled
		};
	}

	window.ifitwalaEd = window.ifitwalaEd || {};
	window.ifitwalaEd.websitePropsBuilder = { open: openPropsBuilder };
})();
