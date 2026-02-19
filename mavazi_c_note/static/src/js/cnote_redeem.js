/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

console.log("✅ POS Refund → C-Note Module Loaded (Odoo 19)");

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.pos = useService("pos");            
        this.orm = useService("orm");           
        this.notification = useService("notification");  
    },

    /* ----------------------------------------------------------
     * ENABLE VALIDATE BUTTON FOR REFUNDS WITHOUT PAYMENTS
     * ---------------------------------------------------------- */
    get isValidateButtonEnabled() {
        const order = this.pos.selectedOrder;
        if (order && order.amount_total < 0) {
            return true;  
        }
        return super.isValidateButtonEnabled;
    },
   

    /* ----------------------------------------------------------
     * HIDE PAYMENT METHODS FOR REFUNDS
     * ---------------------------------------------------------- */
    get paymentMethods() {
        const order = this.pos.selectedOrder;
        if (order && order.amount_total < 0) {
            return []; // refunds never show payment methods
        }
        return super.paymentMethods;
    },

    /* ----------------------------------------------------------
     * FORCE C-NOTE ON REFUND VALIDATION
     * ---------------------------------------------------------- */
    async validateOrder(isForceValidate) {
        const order = this.pos.selectedOrder;

        if (!order) {
            return await super.validateOrder(isForceValidate);
        }

        // ✅ REFUND DETECTION
        if (order.amount_total < 0) {
            if (order.cnote_issued) return;

            // Absolute safety: no payment lines allowed
            if (order.payment_ids && order.payment_ids.length > 0) {
                this.notification.add(
                    "Refunds cannot be validated using payment methods.",
                    { type: "danger" }
                );
                return;
            }

            const refundAmount = Math.abs(order.amount_total);

            // Create C-Note via backend RPC
            const result = await this.orm.call(
                "pos.c.note",
                "create_from_pos",
                [{
                    original_amount: refundAmount,
                    remaining_amount: refundAmount,
                    currency_id: this.pos.currency.id,
                    customer_id: order.partner_id || false,
                    source_order_id: order.backendId || false,
                }]
            );

            order.cnote_issued = true;

            this.notification.add(
                `Store Credit Issued — C-Note Code: ${result.name}, Value: ${refundAmount.toFixed(2)}`,
                { type: "success" }
            );

            // Close order WITHOUT payments
            order.finalized = true;
            await this.pos.push_single_order(order);
            this.pos.showScreen("ProductScreen");
            return;
        }

        // Normal sales
        return await super.validateOrder(isForceValidate);
    },
});
