// Copyright (c) 2025, siva and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Records', {
    setup(frm) {
      frm.fields_dict.assignments.grid.get_field('driver').get_query = () => {
        return {
          query: "logistics.api.get_available_drivers"
        };
      };
    },
  
  
  
    
  });
  
  
  frappe.ui.form.on('Job Assignment', {
    driver: function(frm, cdt, cdn) {
      const row = locals[cdt][cdn];
  
      if (row.driver) {
        frappe.db.get_value('Driver', row.driver, 'employee').then(driver_res => {
          const employee_id = driver_res.message.employee;
  
          if (employee_id) {
            frappe.db.get_list('Vehicle', {
              filters: {
                employee: employee_id
              },
              fields: ['name'],
              limit: 1
            }).then(vehicle_res => {
              if (vehicle_res.length) {
                frappe.model.set_value(cdt, cdn, 'vehicle', vehicle_res[0].name);
              } else {
                frappe.model.set_value(cdt, cdn, 'vehicle', '');
                frappe.msgprint(__('No vehicle is assigned to the driver\'s employee record.'));
              }
            });
          } else {
            frappe.model.set_value(cdt, cdn, 'vehicle', '');
            frappe.msgprint(__('Selected driver does not have an employee linked.'));
          }
        });
      } else {
        frappe.model.set_value(cdt, cdn, 'vehicle', '');
      }
    }
  });
  