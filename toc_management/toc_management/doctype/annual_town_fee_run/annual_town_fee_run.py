# Copyright (c) 2025, martialmania19@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate


class AnnualTownFeeRun(Document):
	pass


def get_or_create_item_from_component(component_name):
	"""
	Check if item exists with component_name, if not create it.
	Returns item code.
	"""
	# Check if item already exists (by item_code or item_name)
	item_code = frappe.db.get_value("Item", {"item_code": component_name}, "name")
	
	if not item_code:
		item_code = frappe.db.get_value("Item", {"item_name": component_name}, "name")
	
	if item_code:
		return item_code
	
	# Get or create Services item group
	item_group = "Services"
	if not frappe.db.exists("Item Group", item_group):
		# Try alternative names
		if frappe.db.exists("Item Group", "Service"):
			item_group = "Service"
		else:
			# Use default item group
			item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
			if not item_group:
				frappe.throw("No Item Group found. Please create a Services Item Group.")
	
	# Create new item
	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": component_name,
		"item_name": component_name,
		"item_group": item_group,
		"is_stock_item": 0,
		"stock_uom": "Nos"
	})
	
	try:
		item.insert(ignore_permissions=True)
		frappe.db.commit()
		return item.name
	except Exception as e:
		frappe.log_error(
			message=f"Error creating item {component_name}: {str(e)}",
			title="Create Item Error"
		)
		frappe.throw(f"Error creating item {component_name}: {str(e)}")


@frappe.whitelist()
def create_sales_invoices_from_fee_run(fee_run_name):
	"""
	Create Sales Invoices from Annual Town Fee Run.
	Processes all Fees Schedule Assignment records that fall within the fee run date range.
	"""
	try:
		# Get the Annual Town Fee Run document
		fee_run = frappe.get_doc("Annual Town Fee Run", fee_run_name)
		
		if not fee_run.start_date or not fee_run.end_date:
			frappe.throw("Start Date and End Date are required for Annual Town Fee Run")
		
		# Get all Fees Schedule Assignment records that overlap with the fee run date range
		assignments = frappe.get_all(
			"Fees Schedule Assignmet",
			filters={
				"start_date": ["<=", fee_run.end_date],
				"end_year": [">=", fee_run.start_date]
			},
			fields=["name", "customer", "customer_name", "property", "annual_fee_schedule", "size_m2"]
		)
		
		if not assignments:
			return {
				"status": "success",
				"message": "No Fees Schedule Assignment records found for the selected date range",
				"invoices_created": 0
			}
		
		invoices_created = 0
		errors = []
		
		for assignment in assignments:
			try:
				# Get the Annual Town Fee Schedule
				if not assignment.annual_fee_schedule:
					errors.append(f"Assignment {assignment.name} has no Annual Fee Schedule")
					continue
				
				fee_schedule = frappe.get_doc("Annual Town Fee Schedule", assignment.annual_fee_schedule)
				
				# Get fee components from the schedule (child table: table_yhrr)
				if not fee_schedule.table_yhrr or len(fee_schedule.table_yhrr) == 0:
					errors.append(f"Fee Schedule {assignment.annual_fee_schedule} has no fee components")
					continue
				
				# Get size_m2 from property ownership
				size_m2 = flt(assignment.size_m2) or 0
				if size_m2 == 0:
					# Try to get from property ownership
					size_m2 = flt(frappe.db.get_value("Property Ownership", assignment.property, "size_m2")) or 0
				
				# Get currency from fee schedule, default to company currency
				currency = fee_schedule.currency
				if not currency:
					currency = frappe.db.get_value("Company", frappe.defaults.get_user_default("Company"), "default_currency")
				
				# Create Sales Invoice in draft
				sales_invoice = frappe.get_doc({
					"doctype": "Sales Invoice",
					"customer": assignment.customer,
					"posting_date": fee_run.start_date,
					"due_date": fee_run.end_date,
					"currency": currency,
					"custom_annual_town_fee_run": fee_run_name,
					"items": []
				})
				
				# Add items from fee components
				for component_detail in fee_schedule.table_yhrr:
					# Get component name
					component_name = frappe.db.get_value(
						"Annual Fee Components",
						component_detail.fee_component,
						"component_name"
					)
					
					if not component_name:
						errors.append(f"Component {component_detail.fee_component} not found")
						continue
					
					# Get or create item
					item_code = get_or_create_item_from_component(component_name)
					
					# Determine quantity
					if component_detail.per_square_meter:
						quantity = size_m2
					else:
						quantity = 1
					
					# Get rate (base_amount)
					rate = flt(component_detail.base_amount) or 0
					
					# Add item to invoice
					sales_invoice.append("items", {
						"item_code": item_code,
						"qty": quantity,
						"rate": rate,
						"description": f"{component_name} - {assignment.property}"
					})
				
				# Only create invoice if there are items
				if len(sales_invoice.items) > 0:
					sales_invoice.insert(ignore_permissions=True)
					# Don't submit - keep in draft
					invoices_created += 1
				else:
					errors.append(f"No items added for assignment {assignment.name}")
					
			except Exception as e:
				error_msg = f"Error processing assignment {assignment.name}: {str(e)}"
				errors.append(error_msg)
				frappe.log_error(
					message=error_msg,
					title="Create Sales Invoice Error"
				)
				continue
		
		frappe.db.commit()
		
		result = {
			"status": "success",
			"message": f"Successfully created {invoices_created} Sales Invoice(s)",
			"invoices_created": invoices_created
		}
		
		if errors:
			result["errors"] = errors
			result["error_count"] = len(errors)
		
		return result
		
	except Exception as e:
		frappe.log_error(
			message=f"Error in create_sales_invoices_from_fee_run: {str(e)}",
			title="Create Sales Invoice Error"
		)
		frappe.throw(f"Error creating Sales Invoices: {str(e)}")


@frappe.whitelist()
def submit_sales_invoices_from_fee_run(fee_run_name):
	"""
	Submit all Sales Invoices linked to this Annual Town Fee Run.
	"""
	try:
		# Get all draft Sales Invoices linked to this fee run
		invoices = frappe.get_all(
			"Sales Invoice",
			filters={
				"custom_annual_town_fee_run": fee_run_name,
				"docstatus": 0  # Draft
			},
			fields=["name"]
		)
		
		if not invoices:
			return {
				"status": "success",
				"message": "No draft Sales Invoices found for this fee run",
				"invoices_submitted": 0
			}
		
		invoices_submitted = 0
		errors = []
		
		for invoice in invoices:
			try:
				si_doc = frappe.get_doc("Sales Invoice", invoice.name)
				si_doc.submit()
				invoices_submitted += 1
			except Exception as e:
				error_msg = f"Error submitting invoice {invoice.name}: {str(e)}"
				errors.append(error_msg)
				frappe.log_error(
					message=error_msg,
					title="Submit Sales Invoice Error"
				)
				continue
		
		frappe.db.commit()
		
		result = {
			"status": "success",
			"message": f"Successfully submitted {invoices_submitted} Sales Invoice(s)",
			"invoices_submitted": invoices_submitted
		}
		
		if errors:
			result["errors"] = errors
			result["error_count"] = len(errors)
		
		return result
		
	except Exception as e:
		frappe.log_error(
			message=f"Error in submit_sales_invoices_from_fee_run: {str(e)}",
			title="Submit Sales Invoice Error"
		)
		frappe.throw(f"Error submitting Sales Invoices: {str(e)}")

