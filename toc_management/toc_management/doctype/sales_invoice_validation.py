# Copyright (c) 2025, martialmania19@gmail.com and contributors
# For license information, please see license.txt

import frappe


def validate_fees_schedule_assignment(doc, method=None):
	"""
	Validate that only one Sales Invoice exists per Fees Schedule Assignment.
	Prevents duplicate invoices for the same ownership and duration.
	"""
	if not doc.custom_fees_schedule:
		return
	
	# Check if another invoice exists with the same fees schedule assignment
	# Exclude the current document and cancelled invoices
	filters = {
		"custom_fees_schedule": doc.custom_fees_schedule,
		"docstatus": ["<", 2],  # Draft (0) or Submitted (1), exclude Cancelled (2)
		"name": ["!=", doc.name]  # Exclude current document
	}
	
	existing_invoice = frappe.db.exists("Sales Invoice", filters)
	
	if existing_invoice:
		frappe.throw(
			f"An invoice already exists for this Fees Schedule Assignment. "
			f"Please use the existing invoice: {existing_invoice}",
			title="Duplicate Invoice"
		)

