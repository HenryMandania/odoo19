import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useExternalListener } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);

        useExternalListener(window, "keydown", (ev) => {
            if (ev.key === "Enter") {               
                if (ev.target.tagName === "INPUT" || ev.target.tagName === "TEXTAREA") {
                    return;
                }

                ev.preventDefault();               
                if (this.currentOrder) {
                    this.pos.orderDone(this.currentOrder);
                }
            }
        });
    },
});