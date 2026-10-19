import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import flt


def validate_3_way_match(doc, method=None):
    """
    Executes on Purchase Invoice `validate`.
    Compares each Purchase Invoice Item against its linked Purchase Order Item (Rate)
    and Purchase Receipt Item (Accepted Qty & Already Billed Qty) using frappe.qb.
    """
    enable_match = frappe.db.get_single_value("P2P Matching Settings", "enable_3_way_match")
    if not enable_match:
        return

    tolerance_pct = flt(
        frappe.db.get_single_value("P2P Matching Settings", "price_variance_tolerance")
    )

    exceptions = []
    total_variance_amount = 0.0
    has_tolerance_warning = False

    for row in doc.items:
        row_price_variance_pct = 0.0
        row_qty_variance = 0.0

        # --- CHECK A: Rate Validation against Purchase Order Item ---
        if row.po_detail:
            po_item = frappe.qb.DocType("Purchase Order Item")
            po_data = (
                frappe.qb.from_(po_item)
                .select(po_item.rate, po_item.qty)
                .where(po_item.name == row.po_detail)
                .run(as_dict=True)
            )

            if po_data:
                po_rate = flt(po_data[0].rate)
                if po_rate > 0:
                    rate_diff = flt(row.rate) - po_rate
                    row_price_variance_pct = (rate_diff / po_rate) * 100.0

                    if rate_diff > 0:
                        total_variance_amount += rate_diff * flt(row.qty)

                    if row_price_variance_pct > tolerance_pct:
                        exceptions.append(
                            _(
                                "Row #{0} ({1}): Billed Rate ({2}) exceeds PO Rate ({3}) by {4:.2f}% (Allowed: {5:.2f}%)."
                            ).format(
                                row.idx,
                                row.item_code,
                                flt(row.rate),
                                po_rate,
                                row_price_variance_pct,
                                tolerance_pct,
                            )
                        )
                    elif row_price_variance_pct > 0:
                        has_tolerance_warning = True
        else:
            exceptions.append(
                _("Row #{0} ({1}): Missing linked Purchase Order.").format(
                    row.idx, row.item_code
                )
            )

        # --- CHECK B: Quantity Validation against Purchase Receipt Item ---
        if row.pr_detail:
            pr_item = frappe.qb.DocType("Purchase Receipt Item")
            pr_data = (
                frappe.qb.from_(pr_item)
                .select(pr_item.qty)
                .where(pr_item.name == row.pr_detail)
                .run(as_dict=True)
            )

            if pr_data:
                received_qty = flt(pr_data[0].qty)

                pi_item = frappe.qb.DocType("Purchase Invoice Item")
                already_billed_res = (
                    frappe.qb.from_(pi_item)
                    .select(Coalesce(Sum(pi_item.qty), 0.0).as_("billed_qty"))
                    .where(
                        (pi_item.pr_detail == row.pr_detail)
                        & (pi_item.docstatus == 1)
                        & (pi_item.parent != doc.name)
                    )
                    .run(as_dict=True)
                )
                already_billed_qty = (
                    flt(already_billed_res[0].billed_qty) if already_billed_res else 0.0
                )
                remaining_billable_qty = received_qty - already_billed_qty

                if flt(row.qty) > remaining_billable_qty:
                    row_qty_variance = flt(row.qty) - remaining_billable_qty
                    total_variance_amount += row_qty_variance * flt(row.rate)
                    exceptions.append(
                        _(
                            "Row #{0} ({1}): Billed Qty ({2}) exceeds remaining received Qty ({3}) on Purchase Receipt {4}."
                        ).format(
                            row.idx,
                            row.item_code,
                            flt(row.qty),
                            remaining_billable_qty,
                            row.purchase_receipt,
                        )
                    )
        elif not doc.update_stock:
            row_qty_variance = flt(row.qty)
            exceptions.append(
                _(
                    "Row #{0} ({1}): Missing linked Purchase Receipt (0 units verified in warehouse)."
                ).format(row.idx, row.item_code)
            )

        # Matches your exact MariaDB column names:
        row.custom_price_variance_ = flt(row_price_variance_pct, 2)
        row.custom_qty_variance = flt(row_qty_variance, 3)

    # Set Header-Level 3-Way Match Verdict using `custom_3way_match_status`
    doc.custom_total_variance_amount = flt(total_variance_amount, 2)

    if exceptions:
        doc.custom_3way_match_status = "Exception Hold"
        doc.custom_match_exception_summary = "\n".join(exceptions)
    elif has_tolerance_warning:
        doc.custom_3way_match_status = "Within Tolerance"
        doc.custom_match_exception_summary = _(
            "Passed within allowed price tolerance ({0}%)."
        ).format(tolerance_pct)
    else:
        doc.custom_3way_match_status = "Matched"
        doc.custom_match_exception_summary = _(
            "100% 3-Way Match verified across PO, PR, and PI."
        )
