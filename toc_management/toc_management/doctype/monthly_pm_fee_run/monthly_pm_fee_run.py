# Copyright (c) 2025, martialmania19@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, add_days, getdate, flt


class MonthlyPMFeeRun(Document):
	pass


def get_or_create_monthly_fee_item():
	"""
	Check if 'Monthly Fee' item exists, if not create it.
	Returns item code.
	"""
	item_name = "Monthly Fee"
	
	# Check if item already exists (by item_code or item_name)
	item_code = frappe.db.get_value("Item", {"item_code": item_name}, "name")
	
	if not item_code:
		item_code = frappe.db.get_value("Item", {"item_name": item_name}, "name")
	
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
		"item_code": item_name,
		"item_name": item_name,
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
			message=f"Error creating item {item_name}: {str(e)}",
			title="Create Item Error"
		)
		frappe.throw(f"Error creating item {item_name}: {str(e)}")


@frappe.whitelist()
def create_sales_invoices_from_pm_fee_run(fee_run_name):
	"""
	Create Sales Invoices from Monthly PM Fee Run.
	Processes all Property Management records where is_active = 1.
	"""
	try:
		# Get the Monthly PM Fee Run document
		fee_run = frappe.get_doc("Monthly PM Fee Run", fee_run_name)
		
		if not fee_run.start_date or not fee_run.end_date:
			frappe.throw("Start Date and End Date are required for Monthly PM Fee Run")
		
		# Get all active Property Management records
		property_managements = frappe.get_all(
			"Property Management",
			filters={
				"is_active": 1
			},
			fields=["name", "customer", "customer_name", "unit_type", "property_id"]
		)
		
		if not property_managements:
			return {
				"status": "success",
				"message": "No active Property Management records found",
				"invoices_created": 0
			}
		
		# Get or create Monthly Fee item
		monthly_fee_item = get_or_create_monthly_fee_item()
		
		# Get company and default currency
		company = frappe.defaults.get_user_default("Company")
		if not company:
			frappe.throw("Please set a default Company")
		
		default_currency = frappe.db.get_value("Company", company, "default_currency")
		if not default_currency:
			frappe.throw("Please set default currency for company")
		
		invoices_created = 0
		errors = []
		
		for pm in property_managements:
			try:
				# Validation: Check if invoice already exists for this customer and fee run
				# We check by customer to avoid duplicates for the same property management
				existing_invoice = frappe.db.exists(
					"Sales Invoice",
					{
						"custom_monthly_pm_fee_run": fee_run_name,
						"customer": pm.customer,
						"docstatus": ["<", 2]  # Draft (0) or Submitted (1), exclude Cancelled (2)
					}
				)
				
				if existing_invoice:
					# Skip creating duplicate invoice
					continue
				
				if not pm.customer:
					errors.append(f"Property Management {pm.name} has no customer")
					continue
				
				if not pm.unit_type:
					errors.append(f"Property Management {pm.name} has no unit type")
					continue
				
				# Get latest Management Fees Assignment for this unit_type
				latest_assignment = frappe.db.sql("""
					SELECT monthly_rate, currency, cost_center
					FROM `tabManagement Fees Assignment`
					WHERE unit_type = %s
					ORDER BY creation DESC
					LIMIT 1
				""", (pm.unit_type,), as_dict=True)
				
				if not latest_assignment:
					errors.append(f"No Management Fees Assignment found for unit type {pm.unit_type} in Property Management {pm.name}")
					continue
				
				monthly_rate = latest_assignment[0].get('monthly_rate') or 0
				if monthly_rate == 0:
					errors.append(f"Monthly rate is 0 for unit type {pm.unit_type} in Property Management {pm.name}")
					continue
				
				# Get currency from assignment or use company default
				currency = latest_assignment[0].get('currency') or default_currency
				cost_center = latest_assignment[0].get('cost_center')
				
				# Set posting date to today and due date to 30 days from today
				posting_date = today()
				due_date = add_days(today(), 30)
				
				# Create Sales Invoice in draft
				sales_invoice = frappe.get_doc({
					"doctype": "Sales Invoice",
					"customer": pm.customer,
					"posting_date": posting_date,
					"due_date": due_date,
					"currency": currency,
					"custom_monthly_pm_fee_run": fee_run_name,
					"items": [{
						"item_code": monthly_fee_item,
						"qty": 1,
						"rate": monthly_rate
					}]
				})
				
				# Add cost center if available
				if cost_center:
					sales_invoice.cost_center = cost_center
					for item in sales_invoice.items:
						item.cost_center = cost_center
				
				sales_invoice.insert(ignore_permissions=True)
				invoices_created += 1
				
			except Exception as e:
				error_msg = f"Error creating invoice for Property Management {pm.name}: {str(e)}"
				errors.append(error_msg)
				frappe.log_error(
					message=f"{error_msg}\n{frappe.get_traceback()}",
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
			message=f"Error in create_sales_invoices_from_pm_fee_run: {str(e)}\n{frappe.get_traceback()}",
			title="Create Sales Invoice Error"
		)
		frappe.throw(f"Error creating Sales Invoices: {str(e)}")


@frappe.whitelist()
def submit_sales_invoices_from_pm_fee_run(fee_run_name):
	"""
	Submit all Sales Invoices linked to this Monthly PM Fee Run.
	"""
	try:
		# Get all draft Sales Invoices linked to this fee run
		invoices = frappe.get_all(
			"Sales Invoice",
			filters={
				"custom_monthly_pm_fee_run": fee_run_name,
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
			message=f"Error in submit_sales_invoices_from_pm_fee_run: {str(e)}\n{frappe.get_traceback()}",
			title="Submit Sales Invoice Error"
		)
		frappe.throw(f"Error submitting Sales Invoices: {str(e)}")
