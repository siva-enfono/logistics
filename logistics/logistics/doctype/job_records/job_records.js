// Copyright (c) 2025, siva and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Records', {
    setup(frm) {
        frm.fields_dict.assignments.grid.get_field('driver').get_query = function(doc, cdt, cdn) {
            return {
                query: "logistics.api.get_available_drivers",
                filters: {
                    start_datetime: frm.doc.start_datetime,
                    end_datetime: frm.doc.end_datetime
                }
            };
        };
    },

  refresh(frm) {
      frm.events.set_financial_indicators(frm);
  },

  set_financial_indicators: function(frm) {
      function process_invoices(invoices, includeOutstanding = false) {
          var totals = {
              grandTotal: 0,
              baseTotal: 0,
              outstandingTotal: 0
          };
          if (invoices && invoices.length > 0) {
              invoices.forEach(function(invoice) {
                  totals.grandTotal += invoice.base_grand_total || 0;
                  totals.baseTotal += invoice.base_total || 0;
                  if (includeOutstanding) {
                      totals.outstandingTotal += invoice.outstanding_amount || 0;
                  }
              });
          }
          return totals;
      }

      function process_journal_entries(entries) {
          var totalDebit = 0;
          if (entries && entries.length > 0) {
              entries.forEach(function(entry) {
                  totalDebit += entry.total_debit || 0;
              });
          }
          return totalDebit;
      }

      frappe.call({
          method: 'frappe.client.get_list',
          args: {
              doctype: 'Sales Invoice',
              filters: {
                  custom_job_record: frm.doc.name,
                  docstatus: 1
              },
              fields: ['base_grand_total', 'base_total', 'outstanding_amount']
          },
          callback: function(response) {
              var salesInvoiceTotals = process_invoices(response.message, true);

              frappe.call({
                  method: 'frappe.client.get_list',
                  args: {
                      doctype: 'Purchase Invoice',
                      filters: {
                          custom_job_record: frm.doc.name,
                          docstatus: 1
                      },
                      fields: ['base_grand_total', 'base_total', 'outstanding_amount']
                  },
                  callback: function(response) {
                      var purchaseInvoiceTotals = process_invoices(response.message, true);

                      frappe.call({
                          method: 'frappe.client.get_list',
                          args: {
                              doctype: 'Journal Entry',
                              filters: {
                                  custom_job_record: frm.doc.name,
                                  docstatus: 1
                              },
                              fields: ['total_debit']
                          },
                          callback: function(response) {
                              var journalEntryTotalDebit = process_journal_entries(response.message);

                              var totalExpenses = purchaseInvoiceTotals.baseTotal + journalEntryTotalDebit;
                              var profitAndLoss = salesInvoiceTotals.baseTotal - totalExpenses;

                              frm.dashboard.add_indicator(
                                  __('Sales Invoice (W/O VAT): {0}', [format_currency(salesInvoiceTotals.baseTotal, frm.doc.currency)]),
                                  'blue'
                              );

                              frm.dashboard.add_indicator(
                                  __('Purchase Invoice (W/O VAT): {0}', [format_currency(purchaseInvoiceTotals.baseTotal, frm.doc.currency)]),
                                  'orange'
                              );

                              frm.dashboard.add_indicator(
                                  __('Journal Entries: {0}', [format_currency(journalEntryTotalDebit, frm.doc.currency)]),
                                  'purple'
                              );

                              frm.dashboard.add_indicator(
                                  __('P&L: {0}', [format_currency(profitAndLoss, frm.doc.currency)]),
                                  profitAndLoss >= 0 ? 'green' : 'red'
                              );
                          }
                      });
                  }
              });
          }
      });
  }
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


frappe.ui.form.on("Job Records", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('View Trips'), function() {
                frappe.set_route("List", "Trip Details", { job_records: frm.doc.name });
            }, __("View"));
        }
    }
});
