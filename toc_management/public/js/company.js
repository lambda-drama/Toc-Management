// Copyright (c) 2025, martialmania19@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Company", {
	refresh(frm) {
		// Add button to update Property Ownership records
		frm.add_custom_button(__("Update Property Ownership"), function() {
			frappe.confirm(
				__("This will update all Property Ownership records that have customer data in the main doctype but empty child table. This is a one-time migration. Continue?"),
				function() {
					// Yes button
					frappe.call({
						method: "toc_management.toc_management.doctype.property_ownership.property_ownership.update_property_ownership_from_main_fields",
						callback: function(r) {
							if (r.message) {
								frappe.show_alert({
									message: r.message.message || __("Update completed successfully"),
									indicator: "green"
								}, 5);
								
								if (r.message.updated_count > 0) {
									frappe.msgprint({
										title: __("Success"),
										message: __("Updated {0} Property Ownership record(s)", [r.message.updated_count]),
										indicator: "green"
									});
								}
							}
						},
						freeze: true,
						freeze_message: __("Updating Property Ownership records...")
					});
				},
				function() {
					// No button - do nothing
				}
			);
		}, __("Actions"));
	}
});

