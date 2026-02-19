/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class MpesaConfirmationDialog extends Component {
    static template = "odoo19mpesa.MpesaConfirmationDialog";
    static components = { Dialog };
    static props = {
        customerName: String,
        phone: String,
        mpesaCode: String,
        amount: [String, Number],
        onConfirm: { type: Function, optional: true },
        close: Function,
        title: { type: String, optional: true },
        error: { type: Boolean, optional: true },
    };

    get title() {
        return this.props.title || _t("MPESA Customer Details");
    }

    async confirm() {
        if (this.props.onConfirm) {
            await this.props.onConfirm();
        }
        this.props.close();
    }
}