// Copyright (c) 2026, Yash Karpe and contributors
// For license information, please see license.txt

frappe.query_reports["3-Way Match Variance Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier",
        },
        {
            fieldname: "match_status",
            label: __("3-Way Match Status"),
            fieldtype: "Select",
            options: "\nMatched\nWithin Tolerance\nException Hold\nPending",
        },
    ],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        if (column.fieldname === "match_status") {
            const colorMap = {
                "Matched": "green",
                "Within Tolerance": "orange",
                "Exception Hold": "red",
                "Pending": "gray",
            };
            const color = colorMap[data.match_status] || "gray";
            return `<span class="indicator-pill ${color}">${value}</span>`;
        }

        if (column.fieldname === "row_variance_amount" && flt(data.row_variance_amount) > 0) {
            return `<b style="color: #e03131;">${value}</b>`;
        }

        return value;
    },
};
