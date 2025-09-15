// Copyright (c) 2025, siva and contributors
// For license information, please see license.txt

frappe.ui.form.on("Trip Details", {
    refresh(frm) {
        if (frm.doc.status === "Trip Started" || frm.doc.status === "In Progress") {
            frm.add_custom_button(__('Add Current Location'), function() {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(function(pos) {
                        frappe.call({
                            method: "logistics.api.add_trip_location",
                            args: {
                                trip_id: frm.doc.name,
                                latitude: pos.coords.latitude,
                                longitude: pos.coords.longitude
                            },
                            callback: function(r) {
                                if (r.message.status_code === 200) {
                                    frappe.show_alert({
                                        message: __("Location updated: " + r.message.location),
                                        indicator: "green"
                                    });
                                    frm.reload_doc();
                                } else {
                                    frappe.msgprint(r.message.message);
                                }
                            }
                        });
                    });
                } else {
                    frappe.msgprint("Geolocation not supported in this browser.");
                }
            });
        }
    }
});
