from frappe import _

def get_data():
    return {
        "fieldname": "job_records",
        "transactions": [
            {
                "label": _("Trips"),
                "items": ["Trip Details"]
            }
        ]
    }
