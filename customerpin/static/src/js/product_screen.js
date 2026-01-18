/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(ProductScreen.prototype, {
    setup() {
        // Attempt to load services. 
        // We wrap them so the component doesn't crash if one is missing.
        try {
            this.popup = useService("popup");
            this.orm = useService("orm");
            this.notification = useService("notification");
        } catch (err) {
            console.warn("SalesStaff Module: Some services were not available during setup.", err);
        }

        super.setup(...arguments);

        this._onSalesStaffKeydown = (ev) => {
            if (ev.key === "F10") {
                ev.preventDefault();
                this.onClickSalesStaff();
            }
        };

        onMounted(() => window.addEventListener("keydown", this._onSalesStaffKeydown));
        onWillUnmount(() => window.removeEventListener("keydown", this._onSalesStaffKeydown));
    },

    async onClickSalesStaff() {
        // 1. Safety Check: Check if the popup service is actually available
        if (!this.popup) {
            console.error("Popup service is not initialized.");
            // Fallback to a standard browser alert if the Odoo popup fails
            alert(_t("The POS Popup system is currently unavailable. Please refresh."));
            return;
        }

        // 2. Normal Popup Logic
        try {
            const { confirmed, payload: code } = await this.popup.add("TextInputPopup", {
                title: _t("Sales Staff Code"),
                body: _t("Enter staff code:"),
            });

            if (confirmed && code) {
                const staff = await this.orm.searchRead(
                    "sales.staff",
                    [["code", "=", code.trim()], ["active", "=", true]],
                    ["id", "name"],
                    { limit: 1 }
                );

                if (staff.length > 0) {
                    const order = this.pos.get_order();
                    if (order) {
                        order.sales_staff_id = staff[0].id;
                        this.notification.add(_t("Assigned: %s", staff[0].name), { type: "success" });
                    }
                } else {
                    this.popup.add("ErrorPopup", {
                        title: _t("Not Found"),
                        body: _t("Invalid staff code."),
                    });
                }
            }
        } catch (error) {
            console.error("An error occurred in onClickSalesStaff:", error);
        }
    }
});