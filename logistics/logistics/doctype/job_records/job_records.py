# Copyright (c) 2025, siva and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class JobRecords(Document):

    def validate(self):
        self.ensure_driver_vehicle_consistency()
        self.prevent_duplicate_assignments()
        self.restore_removed_driver_availability()

    def on_update(self):
        if self.status in ["Pending", "In Progress"]:
            self.set_driver_availability(available=False)
        elif self.status == "Completed":
            self.set_driver_availability(available=True)

    def set_driver_availability(self, available=True):
        """Set availability for drivers in current assignment list."""
        for row in self.assignments:
            if row.driver:
                frappe.db.set_value("Driver", row.driver, "is_available", int(available))

    def restore_removed_driver_availability(self):
        """Mark removed drivers as available if they were previously assigned to this job."""
        if self.get("__islocal"):
            return  

        old_drivers = set(
            d.driver for d in frappe.get_all(
                "Job Assignment",
                filters={"parent": self.name, "parenttype": self.doctype},
                fields=["driver"]
            ) if d.driver
        )

        current_drivers = set(row.driver for row in self.assignments if row.driver)

        removed_drivers = old_drivers - current_drivers

        for driver in removed_drivers:
            frappe.db.set_value("Driver", driver, "is_available", 1)

    def ensure_driver_vehicle_consistency(self):
        """Ensure vehicle is assigned to the selected driver's employee."""
        for row in self.assignments:
            if row.driver and row.vehicle:
                driver_employee = frappe.db.get_value("Driver", row.driver, "employee")
                assigned_driver = frappe.db.get_value("Vehicle", row.vehicle, "employee")
                if assigned_driver != driver_employee:
                    frappe.throw(
                        f"Vehicle {row.vehicle} is not assigned to the driver {row.driver}."
                    )

    def prevent_duplicate_assignments(self):
        """Ensure driver and vehicle are not assigned to other active jobs."""
        active_statuses = ["Pending", "In Progress"]

        for row in self.assignments:
            if row.driver:
                exists = frappe.db.sql("""
                    SELECT ja.name
                    FROM `tabJob Assignment` ja
                    INNER JOIN `tabJob Records` jr ON ja.parent = jr.name
                    WHERE jr.name != %s
                      AND ja.driver = %s
                      AND jr.status IN %s
                """, (self.name, row.driver, tuple(active_statuses)))
                if exists:
                    frappe.throw(f"Driver {row.driver} is already assigned to an active job.")

            if row.vehicle:
                exists = frappe.db.sql("""
                    SELECT ja.name
                    FROM `tabJob Assignment` ja
                    INNER JOIN `tabJob Records` jr ON ja.parent = jr.name
                    WHERE jr.name != %s
                      AND ja.vehicle = %s
                      AND jr.status IN %s
                """, (self.name, row.vehicle, tuple(active_statuses)))
                if exists:
                    frappe.throw(f"Vehicle {row.vehicle} is already assigned to an active job.")
