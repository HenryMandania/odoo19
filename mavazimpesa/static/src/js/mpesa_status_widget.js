/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MpesaStatusWidget extends Component {
    static template = "mavazimpesa.MpesaStatusWidget";
    static props = {};

    setup() {
        // 使用正确的服务获取方式
        this.orm = useService("orm");
        this.pos = useService("pos");

        // Reactive state
        this.state = useState({
            count: 0,
            payments: [],
            showDetails: false,
        });

        // Poll for updates every 5s
        onMounted(() => {
            this._fetchUpdates();
            this.pollTimer = setInterval(() => this._fetchUpdates(), 5000);
        });

        onWillUnmount(() => {
            if (this.pollTimer) clearInterval(this.pollTimer);
        });
    }

    async _fetchUpdates() {
        try {
            // 直接使用 ORM 服务调用
            const result = await this.orm.call(
                "mpesa.transaction",
                "get_open_payments_count",
                [],
                {}
            );

            this.state.count = result ? result.length : 0;
            this.state.payments = result ? result.slice(0, 5) : [];
        } catch (err) {
            console.warn("M-Pesa background poll paused:", err.message);
        }
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }
}