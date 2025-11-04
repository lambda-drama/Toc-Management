// Copyright (c) 2025, martialmania19@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Property Ownership", {
	refresh(frm) {
		// Add button to copy main customer to child table if table is empty
		if (frm.doc.customer && 
			(!frm.doc.ownership_customers || frm.doc.ownership_customers.length === 0)) {
			frm.add_custom_button(__("Add Customer"), function() {
				// Add customer from main doctype to child table
				let child = frm.add_child("ownership_customers");
				child.customer = frm.doc.customer;
				child.customer_name = frm.doc.customer_name || frm.doc.customer;
				if (frm.doc.contract_type) {
					child.contract_type = frm.doc.contract_type;
				}
				frm.refresh_field("ownership_customers");
				frappe.show_alert({
					message: __("Customer added to Ownership Customers table"),
					indicator: "green"
				});
			}, __("Actions"));
		}
	},
	
	before_save(frm) {
		// Update customer, customer_name, and contract_type from ownership_customers table on save
		// This ensures the parent fields are always updated when saving
		if (frm.doc.ownership_customers && frm.doc.ownership_customers.length > 0) {
			// Get the last added customer (newest row)
			const lastCustomer = frm.doc.ownership_customers[frm.doc.ownership_customers.length - 1];
			if (lastCustomer.customer) {
				frm.set_value('customer', lastCustomer.customer);
				frm.set_value('customer_name', lastCustomer.customer_name);
			}
			if (lastCustomer.contract_type) {
				frm.set_value('contract_type', lastCustomer.contract_type);
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
		if (row.contract_type) {
			frm.set_value('contract_type', row.contract_type);
		}
	},
	
	contract_type(frm, cdt, cdn) {
		// When contract_type field changes in the table, update parent
		let row = locals[cdt][cdn];
		if (row.contract_type) {
			frm.set_value('contract_type', row.contract_type);
		}
	}
});
