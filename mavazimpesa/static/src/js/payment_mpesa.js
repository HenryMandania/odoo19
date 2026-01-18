/** @odoo-module **/
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.mpesaPollInterval = null;

        onWillUnmount(() => {
            this._stopMpesaPolling();
        });
    },

    // Override the method that handles payment selection
    async selectPaymentMethod(method) {
        super.selectPaymentMethod(method);
        
        // If the selected method is Mpesa, start polling
        if (method.name.includes("Mpesa") || method.name.includes("Lipa")) {
            this._startMpesaPolling();
        } else {
            this._stopMpesaPolling();
        }
    },

    _startMpesaPolling() {
        if (this.mpesaPollInterval) return;

        console.log("Mpesa Polling Started...");
        this.mpesaPollInterval = setInterval(async () => {
            const selectedLine = this.currentOrder.get_paymentlines().find(
                (line) => line.payment_method_id.name.includes("Mpesa")
            );

            if (selectedLine) {
                const result = await this.rpc("/pos/mpesa/poll_payment", {
                    amount: selectedLine.get_amount()
                });

                if (result) {
                    this._stopMpesaPolling();
                    
                    // 1. Mark the transaction as consumed in the backend
                    await this.rpc("/web/dataset/call_kw/mpesa.transaction/action_consume_from_pos", {
                        model: 'mpesa.transaction',
                        method: 'action_consume_from_pos',
                        args: [result.id, this.pos.config.id],
                        kwargs: {},
                    });

                    // 2. Notify and Auto-Validate
                    this.env.services.notification.add(
                        `Mpesa Verified: ${result.name}`, 
                        { type: "success" }
                    );
                    
                    // Trigger the final validation (simulates hitting Enter/Validate)
                    this.validateOrder();
                }
            }
        }, 1000); // 1 Second interval
    },

    _stopMpesaPolling() {
        if (this.mpesaPollInterval) {
            clearInterval(this.mpesaPollInterval);
            this.mpesaPollInterval = null;
            console.log("Mpesa Polling Stopped.");
        }
    }
});