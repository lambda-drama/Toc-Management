// Copyright (c) 2025, martialmania19@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Update Management Fees Assignment", {
	refresh(frm) {
		// Add "Get Unit Type" button at the top
		if (frm.doc.start_date && frm.doc.end_date) {
			frm.add_custom_button(__("Get Unit Type"), function() {
				get_unit_types(frm);
			});
		}

		// Add "Bulk Assign" button at the top
		if (frm.doc.unit_type && frm.doc.unit_type.length > 0) {
			frm.add_custom_button(__("Bulk Assign"), function() {
				bulk_assign(frm);
			});
		}
	}
});

function get_unit_types(frm) {
	if (!frm.doc.start_date || !frm.doc.end_date) {
		frappe.msgprint(__("Please select Start Date and End Date first"));
		return;
	}

	frappe.call({
		method: "toc_management.toc_management.doctype.bulk_update_management_fees_assignment.bulk_update_management_fees_assignment.get_unit_types_from_town_property",
		callback: function(r) {
			if (r.message) {
				// Clear existing rows
				frm.clear_table("unit_type");

				// Add new rows
				r.message.forEach(function(unit_type_data) {
					let row = frm.add_child("unit_type");
					row.unity_type = unit_type_data.unity_type;
					row.parent_unit_type = unit_type_data.parent_unit_type;
					row.monthly_fees = unit_type_data.monthly_fees || 0;
				});

				frm.refresh_field("unit_type");
				frappe.show_alert({
					message: __("Fetched {0} unique unit types", [r.message.length]),
					indicator: 'green'
				});
			}
		}
	});
}

function bulk_assign(frm) {
	if (!frm.doc.start_date || !frm.doc.end_date) {
		frappe.msgprint(__("Please select Start Date and End Date"));
		return;
	}

	if (!frm.doc.cost_center) {
		frappe.msgprint(__("Please select Cost Center"));
		return;
	}

	if (!frm.doc.unit_type || frm.doc.unit_type.length === 0) {
		frappe.msgprint(__("Please fetch unit types first using 'Get Unit Type' button"));
		return;
	}

	// Confirm before proceeding
	frappe.confirm(
		__("This will create Management Fees Assignment records for each unit type. Continue?"),
		function() {
			// Yes
			frappe.call({
				method: "toc_management.toc_management.doctype.bulk_update_management_fees_assignment.bulk_update_management_fees_assignment.bulk_assign_management_fees",
				args: {
					start_date: frm.doc.start_date,
					end_date: frm.doc.end_date,
					unit_type_rows: frm.doc.unit_type,
					cost_center: frm.doc.cost_center,
					currency: frm.doc.currency
				},
				freeze: true,
				freeze_message: __("Creating Management Fees Assignments..."),
				callback: function(r) {
					if (r.message) {
						let message = __("Created: {0}, Skipped: {1}", [r.message.created, r.message.skipped]);

						if (r.message.errors && r.message.errors.length > 0) {
							message += "<br><br>" + __("Errors:") + "<br>" + r.message.errors.join("<br>");
							frappe.msgprint({
								title: __("Bulk Assign Complete"),
								message: message,
								indicator: 'orange'
							});
						} else {
							frappe.show_alert({
								message: message,
								indicator: 'green'
							});
						}

						// Refresh the form
						frm.reload_doc();
					}
				}
			});
		},
		function() {
			// No
		}
	);
}
