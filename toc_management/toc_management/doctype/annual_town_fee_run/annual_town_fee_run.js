// Copyright (c) 2025, martialmania19@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Annual Town Fee Run", {
	refresh(frm) {
		// Only show buttons after the document is submitted
		if (frm.doc.docstatus === 1 && frm.doc.name && frm.doc.start_date && frm.doc.end_date) {
			// Check if invoices exist and their status
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Sales Invoice",
					filters: {
						custom_annual_town_fee_run: frm.doc.name
					},
					fields: ["docstatus"]
				},
				callback: function(r) {
					let draft_count = 0;
					let submitted_count = 0;
					
					if (r.message && r.message.length > 0) {
						r.message.forEach(function(inv) {
							if (inv.docstatus === 0) {
								draft_count++;
							} else if (inv.docstatus === 1) {
								submitted_count++;
							}
						});
					}
					
					// Show Submit button if there are draft invoices
					if (draft_count > 0) {
						frm.add_custom_button(__("Submit Sales Invoices"), function() {
							frappe.confirm(
								__("This will submit {0} draft Sales Invoice(s). Continue?", [draft_count]),
								function() {
									frappe.call({
										method: "toc_management.toc_management.doctype.annual_town_fee_run.annual_town_fee_run.submit_sales_invoices_from_fee_run",
										args: {
											fee_run_name: frm.doc.name
										},
										callback: function(r) {
											if (r.message) {
												let message = r.message.message || __("Sales Invoices submitted successfully");
												
												if (r.message.errors && r.message.errors.length > 0) {
													message += "<br><br><b>Errors:</b><ul>";
													r.message.errors.forEach(function(error) {
														message += "<li>" + error + "</li>";
													});
													message += "</ul>";
												}
												
												frappe.msgprint({
													title: __("Success"),
													message: message,
													indicator: r.message.error_count > 0 ? "orange" : "green"
												});
												
												frappe.show_alert({
													message: __("Submitted {0} Sales Invoice(s)", [r.message.invoices_submitted || 0]),
													indicator: "green"
												}, 5);
												
												frm.reload_doc();
											}
										},
										freeze: true,
										freeze_message: __("Submitting Sales Invoices...")
									});
								},
								function() {}
							);
						}, __("Actions"));
					}
					
					// Show Create button if no invoices exist or if all are submitted
					if (draft_count === 0 && submitted_count === 0) {
						frm.add_custom_button(__("Create Sales Invoices"), function() {
							frappe.confirm(
								__("This will create Sales Invoices for all Fees Schedule Assignment records that fall within the date range ({0} to {1}). Continue?", 
									[frm.doc.start_date, frm.doc.end_date]),
								function() {
									frappe.call({
										method: "toc_management.toc_management.doctype.annual_town_fee_run.annual_town_fee_run.create_sales_invoices_from_fee_run",
										args: {
											fee_run_name: frm.doc.name
										},
										callback: function(r) {
											if (r.message) {
												let message = r.message.message || __("Sales Invoices created successfully");
												
												if (r.message.errors && r.message.errors.length > 0) {
													message += "<br><br><b>Errors:</b><ul>";
													r.message.errors.forEach(function(error) {
														message += "<li>" + error + "</li>";
													});
													message += "</ul>";
												}
												
												frappe.msgprint({
													title: __("Success"),
													message: message,
													indicator: r.message.error_count > 0 ? "orange" : "green"
												});
												
												frappe.show_alert({
													message: __("Created {0} Sales Invoice(s)", [r.message.invoices_created || 0]),
													indicator: "green"
												}, 5);
												
												frm.reload_doc();
											}
										},
										freeze: true,
										freeze_message: __("Creating Sales Invoices...")
									});
								},
								function() {}
							);
						}, __("Actions"));
					}
				}
			});
		}
	}
});

