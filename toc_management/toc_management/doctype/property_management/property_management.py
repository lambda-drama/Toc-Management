# Copyright (c) 2025, martialmania19@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PropertyManagement(Document):
	def validate(self):
		# If handback_date exists, is_active must be 0
		if self.handback_date:
			self.is_active = 0
	
	def before_save(self):
		# When agreement_date is entered, set is_active to 1
		if self.agreement_date and not self.handback_date:
			self.is_active = 1
		
		# When handback_date is entered, set is_active to 0
		if self.handback_date:
			self.is_active = 0
