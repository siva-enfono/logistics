import frappe

@frappe.whitelist()
def get_available_drivers(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""
        SELECT d.name, d.full_name
        FROM `tabDriver` d
        LEFT JOIN `tabEmployee` e ON e.name = d.employee
        WHERE d.is_available = 1
          AND e.status = 'Active'
          AND (d.name LIKE %(txt)s OR d.full_name LIKE %(txt)s)
        ORDER BY d.full_name
        LIMIT 20
    """, {"txt": f"%{txt}%"})
