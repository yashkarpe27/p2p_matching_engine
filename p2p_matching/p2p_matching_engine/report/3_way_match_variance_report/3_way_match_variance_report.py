# Copyright (c) 2026, Yash Karpe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    report_summary = get_report_summary(data)
    chart = get_chart_data(data)

    return columns, data, None, chart, report_summary


def get_columns():
    return [
        {
            "label": _("Purchase Invoice"),
            "fieldname": "purchase_invoice",
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 170,
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 170,
        },
        {
            "label": _("3-Way Match Status"),
            "fieldname": "match_status",
            "fieldtype": "Data",
            "width": 145,
        },
        {
            "label": _("Workflow State"),
            "fieldname": "workflow_state",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 130,
        },
        {
            "label": _("Purchase Order"),
            "fieldname": "purchase_order",
            "fieldtype": "Link",
            "options": "Purchase Order",
            "width": 155,
        },
        {
            "label": _("PO Rate"),
            "fieldname": "po_rate",
            "fieldtype": "Currency",
            "width": 105,
        },
        {
            "label": _("Billed Rate"),
            "fieldname": "billed_rate",
            "fieldtype": "Currency",
            "width": 105,
        },
        {
            "label": _("Price Var (%)"),
            "fieldname": "price_variance_pct",
            "fieldtype": "Percent",
            "width": 110,
        },
        {
            "label": _("Purchase Receipt"),
            "fieldname": "purchase_receipt",
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "width": 155,
        },
        {
            "label": _("PR Qty"),
            "fieldname": "pr_qty",
            "fieldtype": "Float",
            "width": 90,
        },
        {
            "label": _("Billed Qty"),
            "fieldname": "billed_qty",
            "fieldtype": "Float",
            "width": 95,
        },
        {
            "label": _("Qty Variance"),
            "fieldname": "qty_variance",
            "fieldtype": "Float",
            "width": 110,
        },
        {
            "label": _("Row Variance (₹)"),
            "fieldname": "row_variance_amount",
            "fieldtype": "Currency",
            "width": 135,
        },
    ]


def get_data(filters):
    pi = frappe.qb.DocType("Purchase Invoice")
    pii = frappe.qb.DocType("Purchase Invoice Item")
    poi = frappe.qb.DocType("Purchase Order Item")
    pri = frappe.qb.DocType("Purchase Receipt Item")

    query = (
        frappe.qb.from_(pi)
        .inner_join(pii)
        .on(pii.parent == pi.name)
        .left_join(poi)
        .on(poi.name == pii.po_detail)
        .left_join(pri)
        .on(pri.name == pii.pr_detail)
        .select(
            pi.name.as_("purchase_invoice"),
            pi.posting_date,
            pi.supplier,
            pi.custom_3way_match_status.as_("match_status"),
            pi.workflow_state,
            pii.item_code,
            pii.purchase_order,
            poi.rate.as_("po_rate"),
            pii.rate.as_("billed_rate"),
            pii.custom_price_variance_.as_("price_variance_pct"),
            pii.purchase_receipt,
            pri.qty.as_("pr_qty"),
            pii.qty.as_("billed_qty"),
            pii.custom_qty_variance.as_("qty_variance"),
        )
        .where(pi.docstatus < 2)
        .orderby(pi.posting_date, order=frappe.qb.desc)
    )

    if filters.get("company"):
        query = query.where(pi.company == filters["company"])
    if filters.get("from_date"):
        query = query.where(pi.posting_date >= filters["from_date"])
    if filters.get("to_date"):
        query = query.where(pi.posting_date <= filters["to_date"])
    if filters.get("supplier"):
        query = query.where(pi.supplier == filters["supplier"])
    if filters.get("match_status"):
        query = query.where(pi.custom_3way_match_status == filters["match_status"])

    rows = query.run(as_dict=True)

    for row in rows:
        rate_diff = max(0.0, flt(row.billed_rate) - flt(row.po_rate)) if row.po_rate else 0.0
        qty_diff = flt(row.qty_variance)
        row["row_variance_amount"] = flt(
            (rate_diff * flt(row.billed_qty)) + (qty_diff * flt(row.billed_rate)), 2
        )

    return rows


def get_report_summary(data):
    unique_invoices = {d["purchase_invoice"]: d["match_status"] for d in data}
    total_invoices = len(unique_invoices)
    matched_count = sum(1 for s in unique_invoices.values() if s == "Matched")
    exception_count = sum(1 for s in unique_invoices.values() if s == "Exception Hold")
    total_exposure = sum(flt(d.get("row_variance_amount")) for d in data)

    return [
        {
            "value": total_invoices,
            "label": _("Total Invoices Audited"),
            "datatype": "Int",
            "indicator": "Blue",
        },
        {
            "value": matched_count,
            "label": _("100% Matched Invoices"),
            "datatype": "Int",
            "indicator": "Green",
        },
        {
            "value": exception_count,
            "label": _("Invoices on Exception Hold"),
            "datatype": "Int",
            "indicator": "Red" if exception_count > 0 else "Green",
        },
        {
            "value": total_exposure,
            "label": _("Overbilling Variance Flagged"),
            "datatype": "Currency",
            "indicator": "Red" if total_exposure > 0 else "Green",
        },
    ]


def get_chart_data(data):
    if not data:
        return None

    supplier_totals = {}
    for row in data:
        supplier = row.get("supplier") or "Unknown"
        supplier_totals.setdefault(supplier, {"billed": 0.0, "variance": 0.0})
        supplier_totals[supplier]["billed"] += flt(row.get("billed_rate")) * flt(
            row.get("billed_qty")
        )
        supplier_totals[supplier]["variance"] += flt(row.get("row_variance_amount"))

    labels = list(supplier_totals.keys())
    billed_values = [flt(v["billed"], 2) for v in supplier_totals.values()]
    variance_values = [flt(v["variance"], 2) for v in supplier_totals.values()]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Total Billed Amount (₹)"), "values": billed_values},
                {"name": _("Flagged Variance Amount (₹)"), "values": variance_values},
            ],
        },
        "type": "bar",
        "colors": ["#3b82f6", "#ef4444"],
    }
