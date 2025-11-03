// Copyright (c) 2025, martialmania19@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Property Ownership", {
	refresh(frm) {

	},
	
	before_save(frm) {
		// Update customer and customer_name from ownership_customers table on save
		// This ensures the parent customer is always updated when saving
		if (frm.doc.ownership_customers && frm.doc.ownership_customers.length > 0) {
			// Get the last added customer (newest row)
			const lastCustomer = frm.doc.ownership_customers[frm.doc.ownership_customers.length - 1];
			if (lastCustomer.customer) {
				frm.set_value('customer', lastCustomer.customer);
				frm.set_value('customer_name', lastCustomer.customer_name);
			}
		}
	}
});

// Listen to changes in ownership_customers table
frappe.ui.form.on("Ownership Customers", {
	customer(frm, cdt, cdn) {
		// When customer field changes in the table, update parent
		let row = locals[cdt][cdn];
		if (row.customer) {
			frm.set_value('customer', row.customer);
			frm.set_value('customer_name', row.customer_name);
		}
	}
});
