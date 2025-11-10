// Copyright (c) 2025, martialmania19@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Property Management", {
	agreement_date(frm) {
		// When agreement_date is entered, set is_active to 1
		if (frm.doc.agreement_date && !frm.doc.handback_date) {
			frm.set_value("is_active", 1);
		}
	},
	
	handback_date(frm) {
		// When handback_date is entered, set is_active to 0
		if (frm.doc.handback_date) {
			frm.set_value("is_active", 0);
		} else if (frm.doc.agreement_date) {
			// If handback_date is cleared and agreement_date exists, set is_active to 1
			frm.set_value("is_active", 1);
		}
	},
	
	is_active(frm) {
		// If user tries to set is_active to 1 but handback_date exists, force it to 0
		if (frm.doc.is_active && frm.doc.handback_date) {
			frappe.msgprint(__("Cannot set Is Active to 1 when Handback Date is set."));
			frm.set_value("is_active", 0);
		}
	}
});
