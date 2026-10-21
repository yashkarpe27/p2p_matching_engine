# ERPNext Automated P2P 3-Way Matching Engine

A custom Frappe/ERPNext application that automates **Procure-to-Pay (P2P) 3-Way Matching** across Purchase Orders, Purchase Receipts, and Purchase Invoices to prevent vendor overbilling and unauthorized inventory discrepancies.

## Business Problem Solved
Standard ERPNext rate validation (`Maintain Same Rate Throughout Purchase Cycle`) enforces a rigid zero-tolerance check that blocks invoices over minor rounding variances. When companies disable this to avoid friction, they expose themselves to price inflation and unreceived quantity billing. 

This app solves this by introducing **configurable tolerance thresholds**, an **automated Exception Hold Workflow**, and an **Executive Variance Script Report**.

## Technical Architecture & Implementation

* **Upgrade-Safe Architecture (Fixtures):** Built entirely as a custom app without modifying core ERPNext files. Custom fields, audit statuses, and role-based workflows are version-controlled via `hooks.py` fixtures.
* **Dynamic Settings (Single DocType):** Features a dedicated `P2P Matching Settings` Single DocType, allowing finance teams to toggle the engine and adjust the allowed price variance percentage without touching the codebase.
* **Backend Validation Engine (`frappe.qb` & `doc_events`):** Intercepts the `Purchase Invoice` on the `validate` event. Uses Frappe Query Builder (`frappe.qb`) with `Sum` and `Coalesce` aggregations to fetch linked Purchase Order and Receipt item data.
* **Split-Invoice Loophole Protection:** The Python backend dynamically calculates previously billed quantities across multiple submitted invoices, ensuring vendors cannot bypass limits by splitting shipments into multiple smaller invoices.
* **Real-Time Frontend UI (`doctype_js`):** Injects a custom JavaScript controller using `frm.set_intro` to render real-time Green, Orange, or Red audit banners based on live variance calculations.
* **Executive Analytics:** Includes a custom Script Report featuring complex multi-table joins, four executive KPI summary cards, and a dynamic bar chart tracking supplier overbilling variances.
