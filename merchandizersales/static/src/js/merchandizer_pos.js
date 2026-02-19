/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

console.log("✅ Merchandizer Sales Module Loaded");

// 1️⃣ Patch Order and Orderline
patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        this.merchandizer_id = this.merchandizer_id || null;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.merchandizer_id = this.merchandizer_id || false;
        return json;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.merchandizer_id = json.merchandizer_id || null;
    },
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        data.merchandizer_id = this.merchandizer_id || false;
        return data;
    },
});

patch(PosOrderline.prototype, {
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.merchandizer_id = this.merchandizer_id || false;
        return json;
    },
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        data.merchandizer_id = this.merchandizer_id || false;
        return data;
    },
});

// 2️⃣ Patch ProductScreen
patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.pos = useService("pos");

        this._onSalesStaffKeydown = (ev) => {
            if (ev.key === "F10") {
                ev.preventDefault();
                this.onClickSalesStaff();
            }
        };

        onMounted(() => {
            window.addEventListener("keydown", this._onSalesStaffKeydown);
            console.log("🛠️ Merchandizer Listener Ready (F10)");
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this._onSalesStaffKeydown);
        });
    },

    async onClickSalesStaff() {
        await this._showStaffCodeDialog();
    },

    async _validateAndAssignStaff(code) {
        try {
            const result = await this.orm.searchRead(
                "x_merchandizer.sales",
                [["code", "=", code]],
                ["id", "name", "code"],
                { limit: 1 }
            );

            if (!result.length) {
                this.notification.add(_t("Merchandizer not Found: %s", code), { type: "danger" });
                return;
            }

            const staff = result[0];
            
            // SECOND POPUP: Confirm the Name
            const confirmed = window.confirm(`Assign order to: ${staff.name}?`);
            
            if (confirmed) {
                const order = this.currentOrder;
                if (!order) {
                    this.notification.add(_t("No active order found"), { type: "danger" });
                    return;
                }

                order.merchandizer_id = staff.id;
                (order.lines || []).forEach(line => {
                    line.merchandizer_id = staff.id;
                });

                this.notification.add(_t("Assigned: %s", staff.name), { type: "success" });
            }
        } catch (err) {
            console.error("❌ UI Error:", err);
            this.notification.add(_t("Error: %s", err.message), { type: "danger" });
        }
    },

    async _showStaffCodeDialog() {
        if (document.querySelector(".sales-staff-dialog")) return;

        const overlay = document.createElement("div");
        overlay.className = "sales-staff-dialog-overlay";

        const dialog = document.createElement("div");
        dialog.className = "sales-staff-dialog";
        dialog.innerHTML = `
            <div class="sales-staff-dialog-content">
                <h3 style="margin-top:0">Merchandizer ID</h3>
                <input type="text" id="staff-code-input" placeholder="Enter Code..." autocomplete="off">
                <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:10px;">
                    <button class="cancel">Cancel</button>
                    <button class="confirm" style="background:#714B67; color:white; border:none; padding:5px 15px; border-radius:3px;">Confirm</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        document.body.appendChild(dialog);

        const input = dialog.querySelector("#staff-code-input");
        const confirmBtn = dialog.querySelector(".confirm");

        const closeDialog = () => {
            overlay.remove();
            dialog.remove();
        };

        const handleConfirm = async () => {
            if (input.value) {
                const code = input.value;
                closeDialog();
                await this._validateAndAssignStaff(code);
            }
        };

        // FIX: stopPropagation prevents the first digit from jumping to POS search
        input.addEventListener("keydown", (e) => { 
            e.stopPropagation(); 
            if (e.key === "Enter") handleConfirm(); 
        });
        
        input.addEventListener("keyup", (e) => e.stopPropagation());

        confirmBtn.addEventListener("click", handleConfirm);
        dialog.querySelector(".cancel").addEventListener("click", closeDialog);
        
        setTimeout(() => input.focus(), 150);

        // Ensure styles are present
        if (!document.getElementById("sales-staff-style")) {
            const style = document.createElement("style");
            style.id = "sales-staff-style";
            style.textContent = `
                .sales-staff-dialog { position: fixed; top: 40%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); z-index: 10001; min-width: 250px; }
                .sales-staff-dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 10000; }
                .sales-staff-dialog input { width: 100%; padding: 10px; margin: 15px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 16px; color: black; }
                .sales-staff-dialog button { padding: 5px 15px; cursor: pointer; }
            `;
            document.head.appendChild(style);
        }
    },
});