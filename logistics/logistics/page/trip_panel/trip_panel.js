frappe.pages['trip-panel'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Driver Trip Panel',
        single_column: true
    });

    $(frappe.render_template("trip_panel", {})).appendTo(page.body);

    // Init map
    let map = L.map('map').setView([28.6, 77.2], 7); // Default center India
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    // Load assigned trips
    frappe.call({
        method: "logistics.api.get_driver_trips",
        callback: function(r) {
            if (r.message && r.message.length) {
                let tripSelect = document.getElementById("trip-select");
                r.message.forEach(trip => {
                    let option = document.createElement("option");
                    option.value = trip.trip_id;
                    option.text = trip.trip_id + " (" + trip.status + ")";
                    tripSelect.add(option);
                });
            }
        }
    });

    // On trip change → load trip details
    $("#trip-select").on("change", function() {
        let tripId = this.value;
        frappe.call({
            method: "logistics.api.get_trip_details",
            args: { trip_id: tripId },
            callback: function(r) {
                if (r.message.status_code === 200) {
                    let trip = r.message.trip;

                    $("#pickup").val(trip.pickup_location || "N/A");
                    $("#destination").val(trip.delivery_location || "N/A");
                    $("#trip-status").text(trip.status);

                    // Draw route
                    let coords = trip.logs.map(l => [l.latitude, l.longitude]);
                    if (coords.length) {
                        let polyline = L.polyline(coords, {color: 'blue'}).addTo(map);
                        map.fitBounds(polyline.getBounds());
                    }
                }
            }
        });
    });

    // Start trip
    $("#start-trip").on("click", function() {
        let tripId = $("#trip-select").val();
        frappe.call({
            method: "logistics.api.update_trip_status",
            args: {
                trip_id: tripId,
                status: "Trip Started",
                pickup_date_time: frappe.datetime.now_datetime()
            },
            callback: function(r) {
                frappe.show_alert({message: r.message.message, indicator: "green"});
            }
        });
    });

    // End trip
    $("#end-trip").on("click", function() {
        let tripId = $("#trip-select").val();
        frappe.call({
            method: "logistics.api.update_trip_status",
            args: {
                trip_id: tripId,
                status: "Trip Completed",
                delivery_date_time: frappe.datetime.now_datetime()
            },
            callback: function(r) {
                frappe.show_alert({message: r.message.message, indicator: "red"});
            }
        });
    });
};
