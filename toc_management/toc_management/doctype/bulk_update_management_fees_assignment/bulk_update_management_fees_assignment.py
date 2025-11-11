# Copyright (c) 2025, martialmania19@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BulkUpdateManagementFeesAssignment(Document):
	pass


@frappe.whitelist()
def get_unit_types_from_town_property():
	"""Fetch unique unit types from Town Property along with their parent unit types"""
	# Get unique unit types from Town Property
	unit_types = frappe.db.sql("""
		SELECT DISTINCT 
			tp.type as unit_type,
			tp.unit_type_parent as parent_unit_type
		FROM `tabTown Property` tp
		WHERE tp.type IS NOT NULL
		ORDER BY tp.type
	""", as_dict=True)
	
	result = []
	seen_unit_types = set()
	
	for ut in unit_types:
		unit_type = ut.get('unit_type')
		if unit_type and unit_type not in seen_unit_types:
			seen_unit_types.add(unit_type)
			
			# Get latest monthly_rate from Management Fees Assignment if exists
			# monthly_rate is a Currency field, so we use it directly as monthly_fees
			latest_assignment = frappe.db.sql("""
				SELECT monthly_rate
				FROM `tabManagement Fees Assignment`
				WHERE unit_type = %s
				ORDER BY creation DESC
				LIMIT 1
			""", (unit_type,), as_dict=True)
			
			monthly_fees = 0
			monthly_rate = None
			if latest_assignment:
				monthly_rate = latest_assignment[0].get('monthly_rate')
				# monthly_rate is a currency value, use it directly as monthly_fees
				monthly_fees = float(monthly_rate or 0)
			
			result.append({
				"unity_type": unit_type,
				"parent_unit_type": ut.get('parent_unit_type'),
				"monthly_fees": monthly_fees,
				"monthly_rate": monthly_rate
			})
	
	return result


@frappe.whitelist()
def bulk_assign_management_fees(start_date, end_date, unit_type_rows, cost_center=None, currency=None):
	"""Create Management Fees Assignment for each unit type in the child table"""
	if isinstance(unit_type_rows, str):
		unit_type_rows = frappe.parse_json(unit_type_rows)
	
	created_count = 0
	skipped_count = 0
	errors = []
	
	for row in unit_type_rows:
		unit_type = None
		try:
			# Get row data
			if isinstance(row, dict):
				unit_type = row.get('unity_type')
				parent_unit_type = row.get('parent_unit_type')
				monthly_fees = row.get('monthly_fees') or 0
			else:
				unit_type = row.unity_type
				parent_unit_type = row.parent_unit_type
				monthly_fees = getattr(row, 'monthly_fees', 0) or 0
			
			if not unit_type:
				errors.append("Unit Type is missing in row data")
				continue
			
			# Skip if monthly_fees is 0
			if monthly_fees == 0:
				skipped_count += 1
				continue
			
			# Use monthly_fees from child table as monthly_rate for new assignment
			monthly_rate = monthly_fees
			
			# Get latest monthly_rate from existing Management Fees Assignment for this unit_type
			latest_assignment = frappe.db.sql("""
				SELECT name, monthly_rate
				FROM `tabManagement Fees Assignment`
				WHERE unit_type = %s
				ORDER BY creation DESC
				LIMIT 1
			""", (unit_type,), as_dict=True)
			
			latest_monthly_rate = None
			if latest_assignment:
				latest_monthly_rate = latest_assignment[0].get('monthly_rate')
			
			# Check if Management Fees Assignment already exists for this unit_type and date range
			existing = frappe.db.exists(
				"Management Fees Assignment",
				{
					"unit_type": unit_type,
					"start_date": start_date,
					"end_date": end_date
				}
			)
			
			if existing:
				# Check if the rate is the same
				existing_doc = frappe.get_doc("Management Fees Assignment", existing)
				if existing_doc.monthly_rate == monthly_rate:
					skipped_count += 1
					continue
			
			# Check if rate is constant with latest assignment - if rate hasn't changed, don't create
			# This handles the case where we're creating a new assignment but the rate is the same
			if latest_monthly_rate and float(latest_monthly_rate or 0) == float(monthly_rate or 0):
				# Rate is constant, skip creation
				skipped_count += 1
				continue
			
			# Validate required fields
			if not cost_center:
				errors.append(f"Cost Center is required for unit type {unit_type}")
				continue
			
			# Create new Management Fees Assignment
			doc_data = {
				"doctype": "Management Fees Assignment",
				"unit_type": unit_type,
				"parent_unit_type": parent_unit_type,
				"start_date": start_date,
				"end_date": end_date,
				"cost_center": cost_center,
				"monthly_rate": monthly_rate,
				"currency": currency
			}
			
			doc = frappe.get_doc(doc_data)
			doc.insert(ignore_permissions=True)
			created_count += 1
			
		except Exception as e:
			error_msg = f"Error creating assignment for unit type {unit_type if unit_type else 'unknown'}: {str(e)}"
			errors.append(error_msg)
			frappe.log_error(frappe.get_traceback(), "Bulk Assign Management Fees Error")
	
	return {
		"created": created_count,
		"skipped": skipped_count,
		"errors": errors
	}
