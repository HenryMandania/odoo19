import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Input } from "@point_of_sale/app/components/inputs/input/input";

export class MpesaTransactionPopup extends Component {
    static components = { Dialog, Input };
    static template = "pos_safaricom.MpesaTransactionPopup";
    static props = {
        close: Function,   // Closes the dialog
        confirm: Function, // Returns data to 'makeAwaitable'
        qrCode: { type: String, optional: true },
        amount: { type: Number, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            transactions: [],
            showQrCode: !!this.props.qrCode,
            searchQuery: "",
        });

        // Odoo 19: fetch data before the component shows
        onWillStart(async () => {
            await this.updateTransactions();
        });
    }

    async updateTransactions() {
        try {
            // Using Odoo 19 pos.data service
            const records = await this.pos.data.searchRead("transaction.lipa.na.mpesa", [
                ["pos_payment_id", "=", false]
            ]);
            this.state.transactions = (records || []).map((r) => ({
                id: r.id,
                name: r.name || "Customer",
                phone: r.number || "N/A",
                amount: r.amount || 0,
                received_at: r.received_at,
            })).reverse();
        } catch (e) {
            console.error("M-Pesa fetch failed", e);
        }
    }

    // Call this when clicking "Accept" in your XML
    onSelectTransaction(tx) {
        this.props.confirm(tx);
        this.props.close();
    }

    onCancel() {
        this.props.close();
    }

    toggleQrCode() {
        this.state.showQrCode = !this.state.showQrCode;
    }

    get transactions() {
        const query = this.state.searchQuery.toLowerCase();
        if (!query) return this.state.transactions;
        return this.state.transactions.filter(t => 
            (t.name && t.name.toLowerCase().includes(query)) || 
            (t.phone && t.phone.includes(query))
        );
    }
}