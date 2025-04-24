// registration_of_interest.js
console.log("≡ RoI script LOADED");

function populate_academic_years() {
    const ddl = document.querySelector(
        '[data-fieldname="proposed_academic_year"] select'
    );
    if (!ddl) return console.warn("DDL not yet in DOM");

    frappe.call({
        type: 'GET',                                          // guests ⇒ GET
        method: 'ifitwala_ed.admission.web_form.registration_of_interest.registration_of_interest.get_valid_academic_years',
        callback: ({ message }) => {
            const opts = (message || [])
                .map(r => `<option value="${r.name}">${r.name}</option>`)
                .join('');
            ddl.innerHTML = `<option value="">Select…</option>${opts}`;
        }
    });
}

/* Life-cycle:
   website.js finished     →  trigger_ready() done
   webform_script.js       →  renders form → triggers frappe.web_form.events.after_load
*/
frappe.ready(() => {
    frappe.web_form.events.on('after_load', populate_academic_years);
});
