# Copyright (c) 2025, siva and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class JobRecords(Document):

    def validate(self):
        self.ensure_driver_vehicle_consistency()
        self.prevent_time_conflicts()
        self.create_trip_details_for_assignments()
        self.cleanup_trip_details()

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

    def prevent_time_conflicts(self):
        """Ensure driver and vehicle are not double-booked during overlapping times."""
        for row in self.assignments:
            if row.driver:
                conflict = frappe.db.sql("""
                    SELECT jr.name
                    FROM `tabJob Assignment` ja
                    INNER JOIN `tabJob Records` jr ON ja.parent = jr.name
                    WHERE jr.name != %s
                      AND ja.driver = %s
                      AND (
                            (jr.start_datetime <= %s AND jr.end_datetime >= %s) OR
                            (jr.start_datetime <= %s AND jr.end_datetime >= %s) OR
                            (jr.start_datetime >= %s AND jr.end_datetime <= %s)
                          )
                      AND jr.status IN ('Pending', 'In Progress')
                """, (
                    self.name,
                    row.driver,
                    self.start_datetime, self.start_datetime,
                    self.end_datetime, self.end_datetime,
                    self.start_datetime, self.end_datetime
                ))
                if conflict:
                    frappe.throw(
                        f"Driver {row.driver} is already booked for another job in this time range."
                    )

            if row.vehicle:
                conflict = frappe.db.sql("""
                    SELECT jr.name
                    FROM `tabJob Assignment` ja
                    INNER JOIN `tabJob Records` jr ON ja.parent = jr.name
                    WHERE jr.name != %s
                      AND ja.vehicle = %s
                      AND (
                            (jr.start_datetime <= %s AND jr.end_datetime >= %s) OR
                            (jr.start_datetime <= %s AND jr.end_datetime >= %s) OR
                            (jr.start_datetime >= %s AND jr.end_datetime <= %s)
                          )
                      AND jr.status IN ('Pending', 'In Progress')
                """, (
                    self.name,
                    row.vehicle,
                    self.start_datetime, self.start_datetime,
                    self.end_datetime, self.end_datetime,
                    self.start_datetime, self.end_datetime
                ))
                if conflict:
                    frappe.throw(
                        f"Vehicle {row.vehicle} is already booked for another job in this time range."
                    )

    def create_trip_details_for_assignments(self):
        """Create a Trip Details document whenever a driver is assigned."""
        for row in self.assignments:
            if row.driver:
                existing_trip = frappe.db.exists(
                    "Trip Details",
                    {"job_records": self.name, "driver": row.driver}
                )
                if not existing_trip:
                    trip = frappe.new_doc("Trip Details")
                    trip.job_records = self.name
                    trip.driver = row.driver
                    trip.vehicle = row.vehicle
                    trip.start_datetime = self.start_datetime
                    trip.end_datetime = self.end_datetime
                    trip.pickup_date_time = self.pickup_date_time
                    trip.delivery_date_time = self.delivery_date_time
                    trip.loading_place = self.loading_place
                    trip.unloading_place = self.unloading_place
                    trip.status = "Pending"
                    trip.insert(ignore_permissions=True)
                    frappe.msgprint(f"Trip created for Driver {row.driver}")

    def cleanup_trip_details(self):
        """Delete Trip Details if their assignment row was removed from Job Records."""
        active_driver_ids = [row.driver for row in self.assignments if row.driver]

        trips = frappe.get_all(
            "Trip Details",
            filters={"job_records": self.name},
            fields=["name", "driver", "status"]
        )

        for trip in trips:
            if trip.driver not in active_driver_ids and trip.status == "Pending":
                frappe.delete_doc("Trip Details", trip.name, force=True)
