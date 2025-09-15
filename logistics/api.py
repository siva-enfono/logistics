import frappe, requests, json

@frappe.whitelist(allow_guest=True)
def login_and_get_keys(username: str, password: str):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(username, password)
        login_manager.post_login()

        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)

        # Ensure API keys are generated
        if not user_doc.api_key:
            user_doc.api_key = frappe.generate_hash(length=15)
        if not user_doc.api_secret:
            user_doc.api_secret = frappe.generate_hash(length=15)
            user_doc.save(ignore_permissions=True)

        key = user_doc.api_key
        secret = get_decrypted_password("User", user, "api_secret")

        # frappe.local.login_manager.logout()

        frappe.local.response.update({
            "data": {
                "message": "Login successful",
                "api_key": key,
                "api_secret": secret
            },
            "home_page": "/login",
            "full_name": user_doc.full_name
        })

        return 
    except frappe.AuthenticationError:
        frappe.local.response.http_status_code = 401
        return {"error": "Invalid username or password"}
    
    except Exception as e:
        frappe.local.response.http_status_code = 401
        return {"error": str(e)}







@frappe.whitelist()
def get_available_drivers(doctype, txt, searchfield, start, page_len, filters=None):
    """Return available drivers who are not double-booked in the given time range."""

    start_time = None
    end_time = None

    if filters:
        start_time = filters.get("start_datetime")
        end_time = filters.get("end_datetime")

    if not (start_time and end_time):
        return frappe.db.sql("""
            SELECT d.name, d.full_name
            FROM `tabDriver` d
            LEFT JOIN `tabEmployee` e ON e.name = d.employee
            WHERE e.status = 'Active'
              AND (d.name LIKE %(txt)s OR d.full_name LIKE %(txt)s)
            ORDER BY d.full_name
            LIMIT 20
        """, {"txt": f"%{txt}%"})

    return frappe.db.sql("""
        SELECT d.name, d.full_name
        FROM `tabDriver` d
        LEFT JOIN `tabEmployee` e ON e.name = d.employee
        WHERE e.status = 'Active'
          AND (d.name LIKE %(txt)s OR d.full_name LIKE %(txt)s)
          AND d.name NOT IN (
              SELECT ja.driver
              FROM `tabJob Assignment` ja
              INNER JOIN `tabJob Records` jr ON ja.parent = jr.name
              WHERE jr.status IN ('Pending', 'In Progress')
                AND (
                    (jr.start_datetime <= %(start)s AND jr.end_datetime >= %(start)s) OR
                    (jr.start_datetime <= %(end)s AND jr.end_datetime >= %(end)s) OR
                    (jr.start_datetime >= %(start)s AND jr.end_datetime <= %(end)s)
                )
          )
        ORDER BY d.full_name
        LIMIT 20
    """, {"txt": f"%{txt}%", "start": start_time, "end": end_time})




##Geolocation



def reverse_geocode(lat, lon):
    """Reverse geocode latitude and longitude using Nominatim (OpenStreetMap)."""
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "json", "lat": lat, "lon": lon},
            headers={"User-Agent": "frappe-app"}
        )
        if response.status_code == 200:
            return response.json().get("display_name")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Reverse Geocoding Failed")
    return ""



@frappe.whitelist()
def add_trip_location(trip_id, latitude, longitude):
    """
    Append a new location to Trip Details for the assigned driver.
    Works like the 'Add Current Location' button in the form.
    """
    import json
    try:
        if frappe.session.user == "Guest":
            return {"status_code": 401, "message": "Unauthorized"}

        if not frappe.db.exists("Trip Details", trip_id):
            return {"status_code": 404, "message": "Trip not found"}

        trip = frappe.get_doc("Trip Details", trip_id)


        employee = frappe.get_doc("Employee", {"user_id": frappe.session.user})
        driver = frappe.get_value("Driver", {"employee": employee.name}, "name")
        if trip.driver != driver:
            return {"status_code": 403, "message": "You are not authorized to update this trip"}

        if trip.status in ["Trip Completed", "Cancelled"]:
            return {"status_code": 400, "message": "Trip is already completed or cancelled. Cannot add location."}

        if not latitude or not longitude:
            return {"status_code": 400, "message": "Latitude and Longitude required"}

        location_text = reverse_geocode(latitude, longitude) or "Unknown Location"

        geolocation = json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(longitude), float(latitude)]
                }
            }]
        })

        trip.append("trip_location_log", {
            "latitude": latitude,
            "longitude": longitude,
            "location": f"Location: {location_text}",
            "geolocation": geolocation
        })

        if trip.status == "Trip Started":
            trip.status = "In Progress"

        trip.save(ignore_permissions=True)
        frappe.db.commit()

        latest_logs = [
            {
                "latitude": log.latitude,
                "longitude": log.longitude,
                "location": log.location
            } for log in trip.trip_location_log
        ]

        return {
            "status_code": 200,
            "message": f"Location updated Successfully",
            "trip": trip.name,
            "status": trip.status,
            "employee_name": employee.employee_name,
            "latest_logs": latest_logs,
            "latitude": latitude,
            "longitude": longitude,
            "location": location_text,
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Add Trip Location Error")
        return {"status_code": 500, "message": "Internal Server Error"}



### Trip Details List

@frappe.whitelist()
def get_driver_trips():
    """
    Return trips assigned to the logged-in driver (Employee linked to user),
    along with total count and employee name.
    """
    try:
        employee = frappe.get_doc("Employee", {"user_id": frappe.session.user})
        if not employee:
            return {"status_code": 401, "message": "No employee linked to current user"}

        driver = frappe.get_value("Driver", {"employee": employee.name}, "name")
        if not driver:
            return {"status_code": 401, "message": "No driver assigned to this employee"}

        trips = frappe.get_all(
            "Trip Details",
            filters={"driver": driver},
            fields=[
                "name",
                "status",
                "start_datetime",
                "end_datetime",
                "pickup_date_time",
                "delivery_date_time",
                "loading_place",
                "unloading_place"
            ]
        )

        trips_with_employee = []
        for trip in trips:
            trip_dict = trip.copy()
            trip_dict["employee_name"] = employee.employee_name  
            trips_with_employee.append(trip_dict)

        total_count = len(trips_with_employee)

        return {
            "status_code": 200,
            "total_count": total_count,
            "trips": trips_with_employee
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Get Driver Trips Error")
        return {"status_code": 500, "message": "Internal Server Error"}



@frappe.whitelist()
def update_trip_status(trip_id, status):
    trip = frappe.get_doc("Trip Details", trip_id)
    employee = frappe.get_value("Employee", {"user_id": frappe.session.user}, "name")
    driver = frappe.get_value("Driver", {"employee": employee}, "name")
    if trip.driver != driver:
        return {"status_code": 403, "message": "Not authorized"}

    if status not in ["Trip Started", "In Progress", "Trip Completed", "Cancelled"]:
        return {"status_code": 400, "message": "Invalid status"}

    trip.status = status
    trip.save(ignore_permissions=True)
    frappe.db.commit()

    return {"status_code": 200, "message": f"Trip status updated to {status}"}
