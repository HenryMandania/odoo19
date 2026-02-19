/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

console.log("✅ Customer PIN Module Loaded - Odoo 19");

// ------------------------------------
// 1️⃣ Patch PosOrder (Reactivity & Persistence)
// ------------------------------------
patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        this.customer_pin_id = this.customer_pin_id || null;
        this.kra_qrcode = this.kra_qrcode || null;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.customer_pin_id = this.customer_pin_id || false;
        json.kra_qrcode = this.kra_qrcode || false;
        return json;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.customer_pin_id = json.customer_pin_id || null;
        this.kra_qrcode = json.kra_qrcode || null;
    },
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        data.customer_pin_id = this.customer_pin_id || false;
        data.kra_qrcode = this.kra_qrcode || false;
        return data;
    },
});

// ------------------------------------
// 2️⃣ Patch ProductScreen (F9 dialog)
// ------------------------------------
patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.pos = useService("pos");

        this._onCustomerPinKeydown = (ev) => {
            if (ev.key === "F9") {
                ev.preventDefault();
                this.onClickCustomerPin();
            }
        };

        onMounted(() => {
            window.addEventListener("keydown", this._onCustomerPinKeydown);
            console.log("🛠️ Customer PIN Listener Ready (F9)");
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this._onCustomerPinKeydown);
        });
    },

    async onClickCustomerPin() {
        await this._showCustomerPinDialog();
    },

    async _validateAndAssignCustomer(mobile) {
        try {
            const result = await this.orm.searchRead(
                "customer.pin.register",
                [["mobile", "=", mobile.trim()]],
                ["id", "name", "kra_pin"],
                { limit: 1 }
            );

            if (!result.length) {
                this.notification.add(_t("Customer not found for Mobile: %s", mobile), { type: "danger" });
                return;
            }

            const customer = result[0];
            
            // SECOND POPUP: Confirm Customer Name and PIN
            const confirmed = window.confirm(`Assign order to: ${customer.name}\nKRA PIN: ${customer.kra_pin}?`);
            
            if (confirmed) {
                const order = this.currentOrder;
                if (!order) {
                    this.notification.add(_t("No active order found"), { type: "danger" });
                    return;
                }

                order.customer_pin_id = customer.id;
                order.kra_qrcode = customer.kra_pin;

                this.notification.add(_t("Customer Assigned: %s", customer.name), { type: "success" });
            }

        } catch (err) {
            console.error("❌ UI Error:", err);
            this.notification.add(_t("Error: %s", err.message), { type: "danger" });
        }
    },

    async _showCustomerPinDialog() {
        if (document.querySelector(".customer-pin-dialog")) return;

        const overlay = document.createElement("div");
        overlay.className = "customer-pin-dialog-overlay";

        const dialog = document.createElement("div");
        dialog.className = "customer-pin-dialog";
        dialog.innerHTML = `
            <div class="customer-pin-dialog-content">
                <h3 style="margin-top:0">Customer Mobile</h3>
                <input type="text" id="customer-pin-input" placeholder="Enter Mobile..." autocomplete="off">
                <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:10px;">
                    <button class="cancel" style="padding: 5px 15px; cursor: pointer;">Cancel</button>
                    <button class="confirm" style="background:#28a745; color:white; border:none; padding:5px 15px; border-radius:3px; cursor: pointer;">Confirm</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        document.body.appendChild(dialog);

        const input = dialog.querySelector("#customer-pin-input");
        const confirmBtn = dialog.querySelector(".confirm");

        const closeDialog = () => {
            overlay.remove();
            dialog.remove();
        };

        const handleConfirm = async () => {
            if (input.value) {
                const mobile = input.value;
                closeDialog();
                await this._validateAndAssignCustomer(mobile);
            }
        };

        // STOP PROPAGATION: Prevents typing from leaking to the background search bar
        input.addEventListener("keydown", (e) => { 
            e.stopPropagation(); 
            if (e.key === "Enter") handleConfirm(); 
        });
        input.addEventListener("keyup", (e) => e.stopPropagation());
        input.addEventListener("keypress", (e) => e.stopPropagation());

        confirmBtn.addEventListener("click", handleConfirm);
        dialog.querySelector(".cancel").addEventListener("click", closeDialog);
        
        setTimeout(() => input.focus(), 150);

        if (!document.getElementById("customer-pin-style")) {
            const style = document.createElement("style");
            style.id = "customer-pin-style";
            style.textContent = `
                .customer-pin-dialog { position: fixed; top: 40%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); z-index: 10001; min-width: 250px; }
                .customer-pin-dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 10000; }
                .customer-pin-dialog input { width: 100%; padding: 10px; margin: 15px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 16px; color: black !important; }
            `;
            document.head.appendChild(style);
        }
    },
});