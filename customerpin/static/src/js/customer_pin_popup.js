/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class CustomerPinPopup extends Component {
    setup() {
        this.state = useState({ code: "" });
    }

    confirm() {
        this.props.onConfirm?.(this.state.code);
    }

    cancel() {
        this.props.onCancel?.();
    }
}

CustomerPinPopup.template = "customerpin.CustomerPinPopup";
