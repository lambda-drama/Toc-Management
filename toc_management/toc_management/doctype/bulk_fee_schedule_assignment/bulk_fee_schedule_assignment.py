# Copyright (c) 2025, martialmania19@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BulkFeeScheduleAssignment(Document):
	pass


@frappe.whitelist()
def get_customers(contract_type, town=None):
	"""Get customers from Property Ownership based on contract_type and optional town filter"""
	filters = {
		"contract_type": contract_type,
		# "is_active": 1,
		"customer": ["!=", ""]
	}
	
	if town:
		filters["town"] = town
	
	properties = frappe.get_all(
		"Property Ownership",
		filters=filters,
		fields=["name", "customer", "customer_name", "unit_type", "contract_type"],
		order_by="name"
	)
	
	result = []
	for prop in properties:
		if not prop.customer_name and prop.customer:
			customer_name = frappe.db.get_value("Customer", prop.customer, "customer_name")
			prop.customer_name = customer_name
		
		result.append({
			"property": prop.name,
			"customer": prop.customer,
			"customer_name": prop.customer_name or prop.customer,
			"unit_type": prop.unit_type
		})
	
	return result


@frappe.whitelist()
def bulk_assignment(start_date, end_date, annual_town_fee_schedule, ownership_customers):
	"""Create Fees Schedule Assignment for each customer in ownership_customers table"""
	if isinstance(ownership_customers, str):
		ownership_customers = frappe.parse_json(ownership_customers)
	
	created_count = 0
	errors = []
	
	for row in ownership_customers:
		try:
			# Get row data - handle both dict and object
			if isinstance(row, dict):
				property_name = row.get('property')
				customer = row.get('customer')
				customer_name = row.get('customer_name')
				unit_type = row.get('unit_type')
			else:
				property_name = row.property
				customer = row.customer
				customer_name = row.customer_name
				unit_type = row.unit_type
			
			if not property_name:
				errors.append("Property is missing in row data")
				continue
			
			# Check if Fees Schedule Assignment already exists for this property and date range
			existing = frappe.db.exists(
				"Fees Schedule Assignmet",
				{
					"property": property_name,
					"start_date": start_date,
					"end_year": end_date,
					"annual_fee_schedule": annual_town_fee_schedule
				}
			)
			
			if existing:
				errors.append(f"Assignment already exists for property {property_name}")
				continue
			
			# Get contract_type from Property Ownership
			contract_type = frappe.db.get_value("Property Ownership", property_name, "contract_type")
			
			# Create new Fees Schedule Assignment
			doc = frappe.get_doc({
				"doctype": "Fees Schedule Assignmet",
				"customer": customer,
				"customer_name": customer_name,
				"property": property_name,
				"unit_type": unit_type,
				"contract_type": contract_type,
				"start_date": start_date,
				"end_year": end_date,
				"annual_fee_schedule": annual_town_fee_schedule
			})
			
			doc.insert(ignore_permissions=True)
			created_count += 1
			
		except Exception as e:
			# Safely get property name for error message
			try:
				if isinstance(row, dict):
					property_name = row.get('property', 'Unknown')
				else:
					property_name = getattr(row, 'property', 'Unknown')
			except:
				property_name = 'Unknown'
			
			error_msg = f"Error creating assignment for property {property_name}: {str(e)}"
			errors.append(error_msg)
			frappe.log_error(frappe.get_traceback(), "Bulk Assignment Error")
	
	if errors:
		frappe.msgprint(
			msg=f"Created {created_count} assignments. Errors: {len(errors)}",
			title="Bulk Assignment",
			indicator="orange"
		)
		if len(errors) <= 10:
			frappe.msgprint("<br>".join(errors))
	
	return created_count
