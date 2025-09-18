frappe.pages['trip-dashboard'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Trip Dashboard',
        single_column: true
    });

    $(frappe.render_template("trip_dashboard", {})).appendTo(page.body);

    let map = L.map('map').setView([23.0, 80.0], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    let tripLayer = L.layerGroup().addTo(map);

    setTimeout(() => { map.invalidateSize(); }, 300);
    $(window).on("resize", function() { map.invalidateSize(); });

    frappe.db.get_list('Driver', { fields: ['name', 'employee'] }).then(async drivers => {
        let sel = $("#filter-driver");
        sel.empty().append(`<option value="">All</option>`);
    
        for (let d of drivers) {
            let display_name = d.name;
    
            if (d.employee) {
                let emp = await frappe.db.get_value("Employee", d.employee, "employee_name");
                if (emp && emp.employee_name) {
                    display_name += ` (${emp.employee_name})`;
                }
            }
    
            sel.append(`<option value="${d.name}">${display_name}</option>`);
        }
    });
    
    $("#apply-filters").on("click", function() {
        loadTrips();
    });

    function getStatusBadge(status) {
        let cls = "";
        switch(status) {
            case "Pending": cls = "status-pending"; break;
            case "Trip Started": cls = "status-started"; break;
            case "In Progress": cls = "status-progress"; break;
            case "Trip Completed": cls = "status-completed"; break;
            case "Cancelled": cls = "status-cancelled"; break;
        }
        return `<span class="status-badge ${cls}">${status}</span>`;
    }

    function loadTrips() {
        frappe.call({
            method: "logistics.api.get_all_trips",
            args: {
                driver: $("#filter-driver").val(),
                status: $("#filter-status").val(),
                start_date: $("#filter-start").val(),
                end_date: $("#filter-end").val()
            },
            callback: function(r) {
                let list = $("#trip-list");
                list.empty();
                tripLayer.clearLayers();

                if (r.message && r.message.length) {
                    r.message.forEach(trip => {
                        list.append(`
    <a href="#" class="list-group-item list-group-item-action" data-trip="${trip.name}">
        <span><b>${trip.name}</b> | ${trip.driver_name || "No Driver"} ${trip.employee_name ? "(" + trip.employee_name + ")" : ""}</span>
        ${getStatusBadge(trip.status)}
    </a>
`);

                    });
                } else {
                    list.append(`<p class="text-muted">No trips found for the selected filters</p>`);
                }
            }
        });
    }

    $("#trip-list").on("click", "a", function() {
        let tripId = $(this).data("trip");

        frappe.show_alert({message: "Loading trip details...", indicator: "blue"});

        frappe.call({
            method: "logistics.api.get_trip_details",
            args: { trip_id: tripId },
            callback: function(r) {
                if (r.message.status_code === 200) {
                    let trip = r.message.trip;
                    tripLayer.clearLayers();

                    if (trip.logs && trip.logs.length) {
                        let lastLog = trip.logs[trip.logs.length - 1];
                        let lat = parseFloat(lastLog.latitude);
                        let lon = parseFloat(lastLog.longitude);

                        let marker = L.marker([lat, lon]).addTo(tripLayer);
                        marker.bindPopup(`
                            <b>${trip.name}</b><br>
                            Status: ${trip.status}<br>
                            ${lastLog.location || ""}
                        `).openPopup();

                        map.setView([lat, lon], 13);
                        map.invalidateSize();
                    } else {
                        frappe.show_alert({message: "No location logs for this trip", indicator: "orange"});
                    }
                } else {
                    frappe.show_alert({message: "Failed to fetch trip details", indicator: "red"});
                }
            }
        });
    });

    loadTrips();
};
