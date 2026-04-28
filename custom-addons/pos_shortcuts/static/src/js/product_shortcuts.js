import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useExternalListener } from "@odoo/owl";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        
        useExternalListener(window, "keydown", (ev) => {
            if (ev.key === "F12") {
                ev.preventDefault();
                if (!this.currentOrder?.isEmpty()) {
                    this.pos.pay();
                }
            }
        });
    },
});