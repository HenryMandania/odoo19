/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

console.log("✅ Merchandizer Sales Module Loaded");

// ------------------------------------
// 1️⃣ Patch Order and Orderline (Reactivity & Persistence)
// ------------------------------------
patch(PosOrder.prototype, { setup() { super.setup(...arguments); this.merchandizer_id = this.merchandizer_id || null; }, export_as_JSON() { const json = super.export_as_JSON(...arguments); json.merchandizer_id = this.merchandizer_id || false; console.log("🚀 SERIALIZING ORDER (export_as_JSON):", { name: this.name, uuid: this.uuid, merchandizer_id: json.merchandizer_id, lines: (this.lines || []).map(l => ({ product: l.product_id?.display_name, qty: l.getQuantity(), merchandizer_id: l.merchandizer_id || null, })) }); return json; }, init_from_JSON(json) { super.init_from_JSON(...arguments); this.merchandizer_id = json.merchandizer_id || null; }, serializeForORM(opts = {}) { const data = super.serializeForORM(opts); data.merchandizer_id = this.merchandizer_id || false; console.log("🚀 SERIALIZE FOR ORM:", { id: this.id, name: this.name, uuid: this.uuid, merchandizer_id: data.merchandizer_id, lines: (this.lines || []).map(l => ({ product: l.product_id?.display_name, qty: l.getQuantity(), merchandizer_id: l.merchandizer_id || null, })) }); return data; }, }); patch(PosOrderline.prototype, { export_as_JSON() { const json = super.export_as_JSON(...arguments); json.merchandizer_id = this.merchandizer_id || false; console.log("📝 SERIALIZING LINE (export_as_JSON):", { product: this.product_id?.display_name, qty: this.getQuantity(), merchandizer_id: json.merchandizer_id }); return json; }, serializeForORM(opts = {}) { const data = super.serializeForORM(opts); data.merchandizer_id = this.merchandizer_id || false; console.log("📝 LINE SERIALIZE FOR ORM:", { product: this.product_id?.display_name, qty: this.getQuantity(), merchandizer_id: data.merchandizer_id }); return data; }, });

// ------------------------------------
// 2️⃣ Patch ProductScreen
// ------------------------------------
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
            this._injectStyles();
            console.log("🛠️ Merchandizer Listener Ready (F10)");
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this._onSalesStaffKeydown);
        });
    },

    async onClickSalesStaff() {
        await this._showStaffCodeDialogFallback();
    },

    async _validateAndAssignStaff(code) {
        try {
            // 🔎 Query against the string "code" field, not integer id
            const result = await this.orm.searchRead(
                "x_merchandizer.sales",
                [["code", "=", code]],   // exact string match
                ["id", "name", "code"],
                { limit: 1 }
            );
    
            if (!result.length) {
                this.notification.add(_t("Merchandizer not Found: %s", code), { type: "danger" });
                console.warn("❌ Merchandizer not found for code:", code);
                return;
            }
    
            const staff = result[0];
            const order = this.currentOrder;
    
            if (!order) {
                this.notification.add(_t("No active order found"), { type: "danger" });
                return;
            }
    
            // ✅ Assign merchandizer to order and all lines
            order.merchandizer_id = staff.id;
            const orderLines = order.lines || [];
            orderLines.forEach(line => {
                line.merchandizer_id = staff.id;
            });
    
            // Log assignment details
            console.log("✅ Assigned Merchandizer:", {
                staff_id: staff.id,
                staff_code: staff.code,
                staff_name: staff.name,
                order_name: order.name,
                order_uuid: order.uuid,
                lines: orderLines.map(l => ({
                    product: l.product_id?.display_name,
                    qty: l.getQuantity(),
                    merchandizer_id: l.merchandizer_id
                }))
            });
    
            this.notification.add(_t("Merchandizer: %s", staff.name), { type: "success" });
    
        } catch (err) {
            console.error("❌ UI Error:", err);
            this.notification.add(_t("Error: %s", err.message), { type: "danger" });
        }
    },
    

    async _showStaffCodeDialogFallback() {
        if (document.querySelector(".sales-staff-dialog")) return;

        const overlay = document.createElement("div");
        overlay.className = "sales-staff-dialog-overlay";

        const dialog = document.createElement("div");
        dialog.className = "sales-staff-dialog";
        dialog.innerHTML = `
            <div class="sales-staff-dialog-content">
                <h3 style="margin-top:0">Merchandizer ID</h3>
                <input type="number" id="staff-code-input" placeholder="Enter Code..." autocomplete="off">
                <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:10px;">
                    <button class="cancel" style="padding:5px 15px; cursor:pointer;">Cancel</button>
                    <button class="confirm" style="background:#714B67; color:white; border:none; padding:5px 15px; border-radius:3px; cursor:pointer;">Confirm</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        document.body.appendChild(dialog);

        const input = dialog.querySelector("#staff-code-input");
        const confirmBtn = dialog.querySelector(".confirm");

        const handleConfirm = async () => {
            if (input.value) {
                const code = input.value;
                overlay.remove();
                dialog.remove();
                await this._validateAndAssignStaff(code);
            }
        };

        confirmBtn.addEventListener("click", handleConfirm);
        input.addEventListener("keydown", (e) => { if (e.key === "Enter") handleConfirm(); });
        dialog.querySelector(".cancel").addEventListener("click", () => { overlay.remove(); dialog.remove(); });
        setTimeout(() => input.focus(), 150);
    },

    _injectStyles() {
        if (document.getElementById("sales-staff-styles")) return;
        const style = document.createElement("style");
        style.id = "sales-staff-styles";
        style.textContent = `
            .sales-staff-dialog { position: fixed; top: 40%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); z-index: 10001; min-width: 250px; }
            .sales-staff-dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 10000; }
            .sales-staff-dialog input { width: 100%; padding: 10px; margin: 15px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 16px; }
        `;
        document.head.appendChild(style);
    }
});
