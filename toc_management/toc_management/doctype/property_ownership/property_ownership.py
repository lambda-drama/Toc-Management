# Copyright (c) 2025, martialmania19@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PropertyOwnership(Document):
	pass


@frappe.whitelist()
def update_property_ownership_from_main_fields():
	"""
	One-time migration: Update ownership_customers child table for Property Ownership records
	that have customer data in main doctype but empty child table.
	"""
	try:
		# Get all Property Ownership records that have customer
		property_ownerships = frappe.get_all(
			"Property Ownership",
			filters={
				"customer": ["!=", ""]
			},
			fields=["name", "customer", "customer_name", "contract_type"]
		)
		
		if not property_ownerships:
			return {
				"status": "success",
				"message": "No records found that need updating",
				"updated_count": 0
			}
		
		updated_count = 0
		skipped_count = 0
		
		for po in property_ownerships:
			try:
				doc = frappe.get_doc("Property Ownership", po.name)
				
				# Check if child table is empty
				if not doc.ownership_customers or len(doc.ownership_customers) == 0:
					# Add customer from main doctype to child table
					child_row = doc.append("ownership_customers", {})
					child_row.customer = po.customer
					child_row.customer_name = po.customer_name or po.customer
					if po.contract_type:
						child_row.contract_type = po.contract_type
					
					doc.save(ignore_permissions=True)
					updated_count += 1
				else:
					skipped_count += 1
					
			except Exception as e:
				frappe.log_error(
					message=f"Error updating Property Ownership {po.name}: {str(e)}",
					title="Update Property Ownership Error"
				)
				continue
		
		frappe.db.commit()
		
		return {
			"status": "success",
			"message": f"Successfully updated {updated_count} Property Ownership record(s). Skipped {skipped_count} record(s) that already have child table data.",
			"updated_count": updated_count,
			"skipped_count": skipped_count
		}
		
	except Exception as e:
		frappe.log_error(
			message=f"Error in update_property_ownership_from_main_fields: {str(e)}",
			title="Update Property Ownership Error"
		)
		frappe.throw(f"Error updating Property Ownership records: {str(e)}")
