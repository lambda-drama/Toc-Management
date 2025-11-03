// Copyright (c) 2025, martialmania19@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Fee Schedule Assignment", {
	refresh(frm) {
		// Show "Get Customers" button only if start_date, end_date, and contract_type are filled
		// and document is saved
		if (frm.doc.start_date && frm.doc.end_date && frm.doc.contract_type && !frm.is_new()) {
			frm.add_custom_button(__("Get Customers"), function() {
				frappe.call({
					method: "toc_management.toc_management.doctype.bulk_fee_schedule_assignment.bulk_fee_schedule_assignment.get_customers",
					args: {
						contract_type: frm.doc.contract_type,
						town: frm.doc.town || null
					},
					callback: function(r) {
						if (r.message) {
							frm.clear_table("ownership_customers");
							if (r.message.length > 0) {
								r.message.forEach(function(row) {
									let child = frm.add_child("ownership_customers");
									child.customer = row.customer;
									child.customer_name = row.customer_name;
									child.property = row.property;
									child.unit_type = row.unit_type;
								});
								frm.refresh_field("ownership_customers");
								frappe.show_alert({
									message: __("Fetched {0} customers", [r.message.length]),
									indicator: "green"
								});
							} else {
								frappe.show_alert({
									message: __("No customers found matching the criteria"),
									indicator: "orange"
								});
							}
						}
					}
				});
			}, __("Actions"));
		}

		// Show "Bulk Assignment" button only if annual_town_fee_schedule is filled
		// and ownership_customers table has rows
		if (frm.doc.annual_town_fee_schedule && 
			frm.doc.ownership_customers && 
			frm.doc.ownership_customers.length > 0) {
			frm.add_custom_button(__("Bulk Assignment"), function() {
				frappe.confirm(
					__("Are you sure you want to create Fees Schedule Assignment for {0} customers?", 
						[frm.doc.ownership_customers.length]),
					function() {
						// Yes
						frappe.call({
							method: "toc_management.toc_management.doctype.bulk_fee_schedule_assignment.bulk_fee_schedule_assignment.bulk_assignment",
							args: {
								start_date: frm.doc.start_date,
								end_date: frm.doc.end_date,
								annual_town_fee_schedule: frm.doc.annual_town_fee_schedule,
								ownership_customers: frm.doc.ownership_customers
							},
							callback: function(r) {
								if (r.message) {
									frappe.show_alert({
										message: __("Created {0} Fees Schedule Assignment records", [r.message]),
										indicator: "green"
									});
									frm.reload_doc();
								}
							}
						});
					},
					function() {
						// No
					}
				);
			}, __("Actions"));
		}
	}
});
