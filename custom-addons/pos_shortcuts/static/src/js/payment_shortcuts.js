import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useExternalListener } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);

        useExternalListener(window, "keydown", (ev) => {
            // F12 for Cash
            if (ev.key === "F12") {
                ev.preventDefault();
                const cashMethod = this.payment_methods_from_config.find(m => m.type === "cash");
                if (cashMethod) {
                    this.addNewPaymentLine(cashMethod);
                }
            }

            // F9 for Card
            if (ev.key === "F9") {
                ev.preventDefault();
                const cardMethod = this.payment_methods_from_config.find(
                    m => m.type !== "cash" && m.type !== "pay_later" && m.name.toLowerCase().includes("card")
                );
                if (cardMethod) {
                    this.addNewPaymentLine(cardMethod);
                }
            }

            // F11 for M-PesaTill
            if (ev.key === "F11") {
                ev.preventDefault();
                const tillMethod = this.payment_methods_from_config.find(
                    m => m.name === "M-PesaTill"
                );
                if (tillMethod) {
                    this.addNewPaymentLine(tillMethod);
                }
            }

            // F10 for M-PesaSTK
            if (ev.key === "F10") {
                ev.preventDefault();
                const stkMethod = this.payment_methods_from_config.find(
                    m => m.name === "M-PesaSTK"
                );
                if (stkMethod) {
                    this.addNewPaymentLine(stkMethod);
                }
            }

            // Enter for Validate
            if (ev.key === "Enter") {
                if (this.currentOrder?.isPaid()) {
                    this.validateOrder();
                }
            }
        });
    },
});
