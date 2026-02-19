/** POS C-Note Integration — Refunds Only */
import { patch } from '@web/core/utils/patch';
import { PaymentScreen } from '@point_of_sale/app/screens/payment_screen/payment_screen';

/**
 * Wait for POS order to exist safely
 */
async function getOrderSafely(env, retries = 5, delay = 100) {
    for (let i = 0; i < retries; i++) {
        if (env.pos) {
            const order = env.pos.get_order();
            if (order) return order;
        }
        await new Promise(r => setTimeout(r, delay));
    }
    return null; // could not find order safely
}

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = await getOrderSafely(this.env);

        if (!order) {
            console.warn('POS order is not ready, skipping refund/C-Note logic');
            return await super.validateOrder(isForceValidate);
        }

        // Only handle refunds
        if (order.get_total_with_tax() < 0 || order.isRefund) {
            const total = Math.abs(order.get_total_with_tax());

            const code = await this.env.services.rpc({
                model: 'pos.c.note',
                method: 'create_from_pos',
                args: [{
                    original_amount: total,
                    remaining_amount: total,
                    currency_id: this.env.pos.currency.id,
                }],
            });

            this.showPopup('ConfirmPopup', {
                title: 'Store Credit Issued',
                body: `C-Note Code: ${code}\nValue: ${total.toFixed(2)}`,
            });

            order.finalized = true;
            return; // skip normal payment
        }

        return await super.validateOrder(isForceValidate);
    },

    async addNewPaymentLine(paymentMethod) {
        const order = await getOrderSafely(this.env);

        if (!order) {
            console.warn('POS order is not ready, skipping refund/C-Note logic');
            return await super.addNewPaymentLine(paymentMethod);
        }

        // Only handle refunds
        if (order.isRefund) {
            const total = Math.abs(order.get_total_with_tax());

            const code = await this.env.services.rpc({
                model: 'pos.c.note',
                method: 'create_from_pos',
                args: [{
                    original_amount: total,
                    remaining_amount: total,
                    currency_id: this.env.pos.currency.id,
                }],
            });

            this.showPopup('ConfirmPopup', {
                title: 'Store Credit Issued',
                body: `C-Note Code: ${code}\nValue: ${total.toFixed(2)}`,
            });

            order.finalized = true;
            return; // skip normal payment
        }

        return await super.addNewPaymentLine(paymentMethod);
    },

    async applyCNote(code) {
        const order = await getOrderSafely(this.env);
        if (!order) throw new Error('No active POS order found');

        const notes = await this.orm.searchRead(
            'pos.c.note',
            [['name', '=', code], ['active', '=', true]],
            ['remaining_amount']
        );

        if (!notes.length) throw new Error('Invalid or exhausted C-Note');

        const note = notes[0];
        const amount = Math.min(note.remaining_amount, order.get_due());

        const cnoteMethod = this.env.pos.payment_methods.find(pm => pm.name === 'C-Note / Store Credit');
        if (!cnoteMethod) throw new Error('C-Note payment method not configured in POS');

        order.add_paymentline(cnoteMethod);
        order.selected_paymentline.set_amount(amount);

        await this.orm.call('pos.c.note', 'redeem', [[note.id], amount]);
    },
});
