/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.pos = useService("pos");
        
        // Inject custom CSS for our window
        this._injectMpesaStyles();

        this._onMpesaKeydown = (ev) => {
            if (ev.key === "F9") {
                ev.preventDefault();
                this.showMpesaManualWindow();
            }
        };

        onMounted(() => window.addEventListener("keydown", this._onMpesaKeydown));
        onWillUnmount(() => window.removeEventListener("keydown", this._onMpesaKeydown));
    },

    async showMpesaManualWindow() {
        // Prevent multiple windows
        if (document.querySelector(".mpesa-custom-overlay")) return;

        try {
            // Get data directly from Python
            const transactions = await this.orm.call(
                "mpesa.transaction",
                "get_open_payments",
                []
            );
            this._renderCustomWindow(transactions);
        } catch (err) {
            console.error("M-Pesa Data Error:", err);
        }
    },

    _renderCustomWindow(transactions) {
        const overlay = document.createElement("div");
        overlay.className = "mpesa-custom-overlay";
        
        const container = document.createElement("div");
        container.className = "mpesa-custom-window";

        const itemsHtml = transactions.map(t => `
            <div class="mpesa-item" data-id="${t.id}" data-name="${t.name}">
                <div class="mpesa-info">
                    <span class="mpesa-code">${t.name}</span>
                    <span class="mpesa-amt">KES ${t.amount}</span>
                </div>
                <button class="mpesa-select-action">Link Order</button>
            </div>
        `).join('') || '<div class="mpesa-none">No payments found</div>';

        container.innerHTML = `
            <div class="mpesa-header">
                <h2>M-Pesa Selection</h2>
                <span class="mpesa-close-btn">&times;</span>
            </div>
            <div class="mpesa-body">${itemsHtml}</div>
        `;

        document.body.appendChild(overlay);
        document.body.appendChild(container);

        // Bind Actions
        container.querySelectorAll(".mpesa-select-action").forEach(btn => {
            btn.onclick = (e) => {
                const row = e.target.closest(".mpesa-item");
                this._linkTransaction(row.dataset.id, row.dataset.name);
                this._destroyWindow(overlay, container);
            };
        });

        container.querySelector(".mpesa-close-btn").onclick = () => this._destroyWindow(overlay, container);
        overlay.onclick = () => this._destroyWindow(overlay, container);
    },

    _linkTransaction(id, name) {
        const order = this.pos.get_order();
        if (order) {
            // Save info to order for backend sync
            order.mpesa_transaction_id = [parseInt(id), name];
            order.mpesa_receipt = name;
            
            // Trigger a UI refresh if needed
            if (order._update) order._update();
            alert("Order linked to M-Pesa: " + name);
        }
    },

    _destroyWindow(ov, con) {
        ov.remove();
        con.remove();
    },

    _injectMpesaStyles() {
        if (document.getElementById("mpesa-custom-css")) return;
        const style = document.createElement("style");
        style.id = "mpesa-custom-css";
        style.textContent = `
            .mpesa-custom-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:999998; }
            .mpesa-custom-window { position: fixed; top:50%; left:50%; transform:translate(-50%, -50%); background:#fff; width:380px; border-radius:12px; z-index:999999; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            .mpesa-header { background:#157347; color:#fff; padding:15px; border-radius:12px 12px 0 0; display:flex; justify-content:space-between; align-items:center; }
            .mpesa-header h2 { margin:0; font-size:18px; }
            .mpesa-close-btn { cursor:pointer; font-size:24px; }
            .mpesa-body { padding:10px; max-height:400px; overflow-y:auto; }
            .mpesa-item { display:flex; justify-content:space-between; align-items:center; padding:12px; border-bottom:1px solid #eee; }
            .mpesa-code { display:block; font-weight:bold; color:#157347; }
            .mpesa-amt { font-size:14px; color:#666; }
            .mpesa-select-action { background:#157347; color:#fff; border:none; padding:8px 15px; border-radius:6px; cursor:pointer; }
            .mpesa-select-action:hover { background:#115c39; }
        `;
        document.head.appendChild(style);
    }
});