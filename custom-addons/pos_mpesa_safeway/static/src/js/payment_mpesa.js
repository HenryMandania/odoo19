/** @odoo-module **/

import { _t } from "@web/core/l10n/translation"; 
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PaymentMpesa extends PaymentInterface {

    async sendPaymentRequest(uuid) {
        const order = this.pos.get_order();
        const line = order.get_selected_paymentline();

        line.set_payment_status("waiting");

        // 💳 Till Mode: Require Manual Transaction Code Entry
        if (this.payment_method.mpesa_type === "till") {
            return await this._verifyManualTransaction(line);
        }

        // 📱 STK Push Mode: Phone input popup
        const { confirmed, payload } = await this.env.services.dialog.add(NumberPopup, {
            title: _t("M-Pesa STK Push"),
            body: _t("Enter customer phone number (2547XXXXXXXX)"),
            startingValue: "2547",
        });

        if (!confirmed) {
            line.set_payment_status("retry");
            return false;
        }

        try {
            const result = await this.env.services.rpc("/mpesa/stk_push", {
                phone: payload,
                amount: line.amount,
                method_id: this.payment_method.id,
            });

            if (!result || result.success === false) {
                this._showError(result?.error || "STK Push failed.");
                line.set_payment_status("retry");
                return false;
            }

            // Start polling the server to see if the callback has arrived
            return await this._pollForPayment(line, payload);

        } catch (error) {
            this._showError("Network error while sending STK Push.");
            line.set_payment_status("retry");
            return false;
        }
    }

    /**
     * Logic for Till Mode: Verify a manually entered M-Pesa Code
     */
    async _verifyManualTransaction(line) {
        const { confirmed, payload } = await this.env.services.dialog.add(TextInputPopup, {
            title: _t("Manual M-Pesa Entry"),
            body: _t("Enter the M-Pesa Transaction Code (e.g. RDK...)"),
            startingValue: "",
        });

        if (!confirmed || !payload) {
            line.set_payment_status("retry");
            return false;
        }

        try {
            // Call the Python validation method we defined in the previous step
            const result = await this.env.services.rpc("/web/dataset/call_kw/mpesa.transaction/validate_pos_payment", {
                model: 'mpesa.transaction',
                method: 'validate_pos_payment',
                args: [payload.toUpperCase(), line.amount],
                kwargs: {},
            });

            if (result && result.confirmed) {
                line.transaction_id = payload.toUpperCase();
                line.set_payment_status("done");
                return true;
            } else {
                this._showError("Transaction ID not found or already used.");
                line.set_payment_status("retry");
                return false;
            }
        } catch (error) {
            this._showError("Error verifying transaction.");
            line.set_payment_status("retry");
            return false;
        }
    }

    /**
     * Logic for STK Mode: Poll until the webhook updates the transaction state
     */
    async _pollForPayment(line, phone) {
        // Poll for ~60 seconds (20 attempts * 3 seconds)
        for (let i = 0; i < 20; i++) {
            const status = await this.env.services.rpc("/mpesa/check_payment", {
                phone: phone,
                amount: line.amount,
            });

            if (status?.found) {
                line.transaction_id = status.trans_id || status.name;
                line.set_payment_status("done");
                return true;
            }

            await new Promise(resolve => setTimeout(resolve, 3000));
        }

        this._showError("M-Pesa payment timeout. Verify on your phone or try again.");
        line.set_payment_status("retry");
        return false;
    }

    _showError(message) {
        this.env.services.dialog.add(AlertDialog, {
            title: _t("M-Pesa Error"),
            body: message,
        });
    }
}

register_payment_method("mpesa", PaymentMpesa);