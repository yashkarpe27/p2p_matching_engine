frappe.ui.form.on("Purchase Invoice", {
    refresh(frm) {
        if (frm.is_new() || !frm.doc.custom_3way_match_status) {
            return;
        }

        frm.set_intro(null);

        const status = frm.doc.custom_3way_match_status;
        const summary = frm.doc.custom_match_exception_summary || "";
        const varianceAmt = format_currency(
            frm.doc.custom_total_variance_amount || 0,
            frm.doc.currency
        );

        if (status === "Matched") {
            frm.set_intro(
                `<b>3-Way Match Passed:</b> All quantities and rates match the Purchase Order and Purchase Receipt.`,
                "green"
            );
        } else if (status === "Within Tolerance") {
            frm.set_intro(
                `<b>3-Way Match (Within Tolerance):</b> Minor price variance (${varianceAmt}) is within allowed limits.`,
                "orange"
            );
        } else if (status === "Exception Hold") {
            frm.set_intro(
                `<b>3-Way Match Exception Hold (Variance: ${varianceAmt}):</b><br>${summary.replace(/\n/g, "<br>")}`,
                "red"
            );
        }
    }
});
