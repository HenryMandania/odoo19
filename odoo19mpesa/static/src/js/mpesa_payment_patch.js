import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService, useBus } from "@web/core/utils/hooks";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { onWillUnmount } from "@odoo/owl";

console.log("✅ M-Pesa PaymentScreen patch loaded!");

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        
        // Store polling intervals
        this.pollingIntervals = new Map();
        this.pollingTimeouts = new Map();
        this.pendingMpesaOrders = new Map();
        this.reminderTimeouts = new Map();

        // Listen for AUTO-ADDED payment notifications from backend
        useBus(this.env.bus, "mpesa.auto.payment", (payload) => {
            console.log("🎯 Backend auto-added payment:", payload);
            this._handleAutoAddedPayment(payload);
        });
        
        // Also listen to general M-Pesa events
        useBus(this.env.bus, "pos.mpesa", (payload) => {
            console.log("📩 General M-Pesa event:", payload);
            this._handleAutoAddedPayment(payload);
        });
        
        // Clean up polling intervals
        onWillUnmount(() => {
            this._cleanupAllPolling();
        });
        
        console.log("🎯 M-Pesa auto-payment listeners registered");
    },

    _cleanupAllPolling() {
        console.log("🧹 Cleaning up all polling intervals");
        
        this.pollingIntervals.forEach((intervalId, orderName) => {
            clearInterval(intervalId);
        });
        this.pollingIntervals.clear();
        
        this.pollingTimeouts.forEach((timeoutId, orderName) => {
            clearTimeout(timeoutId);
        });
        this.pollingTimeouts.clear();
        
        this.reminderTimeouts.forEach((timeoutId, orderName) => {
            clearTimeout(timeoutId);
        });
        this.reminderTimeouts.clear();
        
        this.pendingMpesaOrders.clear();
    },

    _stopPollingForOrder(orderName) {
        if (this.pollingIntervals.has(orderName)) {
            clearInterval(this.pollingIntervals.get(orderName));
            this.pollingIntervals.delete(orderName);
        }
        
        if (this.pollingTimeouts.has(orderName)) {
            clearTimeout(this.pollingTimeouts.get(orderName));
            this.pollingTimeouts.delete(orderName);
        }
        
        if (this.reminderTimeouts.has(orderName)) {
            clearTimeout(this.reminderTimeouts.get(orderName));
            this.reminderTimeouts.delete(orderName);
        }
        
        this.pendingMpesaOrders.delete(orderName);
    },

    _handleAutoAddedPayment(payload) {
        console.log("🔍 Processing auto-added payment:", payload);
        const currentOrder = this.currentOrder;
        
        if (!currentOrder) {
            console.warn("⚠️ No current order when auto-payment received");
            return;
        }
        
        // Check if this payment is for the current order
        if (payload.order_name === currentOrder.name || 
            payload.order_reference === currentOrder.name) {
            
            console.log("✅ Auto-payment matches current order!");
            
            // Check if payment already exists in frontend
            const existingPayment = currentOrder.paymentlines.find(
                line => line.mpesa_bank_ref === payload.receipt
            );
            
            if (existingPayment) {
                console.log("⚠️ Payment already exists in frontend:", payload.receipt);
                return;
            }
            
            // Find M-Pesa payment method
            const mpesaMethod = this.env.pos.payment_methods.find(
                method => method.name.includes("M-Pesa")
            );
            
            if (!mpesaMethod) {
                console.error("❌ M-Pesa payment method not found!");
                this.notification.add(_t("M-Pesa payment method not found!"), { type: "danger" });
                return;
            }
            
            // Add payment line locally to sync with backend
            const amount = parseFloat(payload.amount || 0);
            const added = currentOrder.addPaymentline(mpesaMethod);
            
            if (added.status) {
                added.data.amount = amount;
                added.data.mpesa_bank_ref = payload.receipt;
                this.numberBuffer.set(amount.toString());
                this.updateSelectedPaymentline(amount);
                
                console.log("✅ Frontend payment line added to match backend!");
                
                // Stop polling for this order
                this._stopPollingForOrder(currentOrder.name);
                
                // Clear checkout ID
                currentOrder.mpesa_checkout_id = null;
                
                // Show success notification
                this.notification.add(
                    _t("✅ M-Pesa payment automatically added!"),
                    { type: "success", sticky: true }
                );
                
                // Show confirmation dialog
                this.dialog.add(AlertDialog, {
                    title: _t("Payment Automatically Added"),
                    body: _t(
                        `✅ **PAYMENT CONFIRMED & ADDED**\n\n` +
                        `📄 Receipt: ${payload.receipt}\n` +
                        `💰 Amount: Ksh ${amount.toFixed(2)}\n` +
                        `📋 Order: ${currentOrder.name}\n\n` +
                        `The payment was automatically added to your order.`
                    ),
                });
                
                // Trigger UI update
                this.render(true);
            }
        } else {
            console.log("📝 Auto-payment is for different order:", payload.order_name);
        }
    },

    async addNewPaymentLine(paymentMethod) {
        const currentOrder = this.currentOrder;
        const dueAmount = currentOrder.remainingDue;

        if (dueAmount <= 0) return false;

        // --- M-Pesa STK (Backend will auto-add) ---
        if (paymentMethod.name.includes("M-Pesa")) {
            console.log("🎯 M-Pesa flow triggered for order:", currentOrder.name);

            // Show instructions
            const proceed = await new Promise((resolve) => {
                this.dialog.add(AlertDialog, {
                    title: _t("M-Pesa Payment"),
                    body: _t(
                        "**SYSTEM WILL AUTO-ADD PAYMENT**\n\n" +
                        "1. Enter customer phone number\n" +
                        "2. Enter amount\n" +
                        "3. System sends M-Pesa prompt\n" +
                        "4. **BACKEND WILL AUTO-ADD PAYMENT** when confirmed\n\n" +
                        "Proceed?"
                    ),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });

            if (!proceed) return false;

            // Get phone number
            const phoneNumber = await makeAwaitable(this.dialog, NumberPopup, {
                title: _t("Customer Phone (e.g., 2547XXXXXXXX)"),
                startingValue: "254",
                placeholder: _t("Enter customer phone number"),
            });

            if (!phoneNumber) return false;

            let cleanPhone = String(phoneNumber).trim().replace(/\s+/g, '');
            
            // Convert to international format
            if (cleanPhone.startsWith('0')) {
                cleanPhone = '254' + cleanPhone.substring(1);
            } else if (cleanPhone.startsWith('7') && cleanPhone.length === 9) {
                cleanPhone = '254' + cleanPhone;
            } else if (cleanPhone.startsWith('+254')) {
                cleanPhone = cleanPhone.substring(1);
            }

            if (!cleanPhone.startsWith('254') || cleanPhone.length !== 12) {
                this.dialog.add(AlertDialog, {
                    title: _t("Invalid Phone Number"),
                    body: _t("Phone must be in format: 2547XXXXXXXX (12 digits)"),
                });
                return false;
            }

            // Get amount
            const amount = await makeAwaitable(this.dialog, NumberPopup, {
                title: _t("Enter amount to push (Ksh)"),
                startingValue: dueAmount.toString(),
                placeholder: _t("Enter amount in Kenyan Shillings"),
            });

            if (!amount) return false;

            const floatAmount = parseFloat(amount);
            if (floatAmount <= 0) {
                this.notification.add(_t("Invalid amount"), { type: "warning" });
                return false;
            }

            if (floatAmount > dueAmount) {
                this.dialog.add(AlertDialog, {
                    title: _t("Amount Exceeds Total"),
                    body: _t("Amount (Ksh %s) exceeds order total (Ksh %s)")
                        .replace('%s', floatAmount.toFixed(2))
                        .replace('%s', dueAmount.toFixed(2)),
                });
                return false;
            }

            console.log("📤 Calling backend STK push:", {
                amount: floatAmount,
                phone: cleanPhone,
                order: currentOrder.name
            });

            this.notification.add(_t("Sending M-Pesa request..."), { type: "info" });

            try {
                const result = await this.orm.call(
                    "mpesa.provider",
                    "trigger_stk_push_from_pos",
                    [floatAmount, cleanPhone, currentOrder.name]
                );

                console.log("📥 STK Push result:", result);

                if (!(result && result.ResponseCode === "0")) {
                    const errorMsg = result?.CustomerMessage || "Unknown error";
                    this.dialog.add(AlertDialog, {
                        title: _t("M-Pesa Request Failed"),
                        body: _t("The M-Pesa request failed:\n%s").replace('%s', errorMsg),
                    });
                    return false;
                }

                const checkoutId = result.CheckoutRequestID || "";
                currentOrder.mpesa_checkout_id = checkoutId;
                
                console.log("📝 Saved checkout ID:", checkoutId);

                // Store for polling
                this.pendingMpesaOrders.set(currentOrder.name, {
                    checkoutId,
                    amount: floatAmount,
                    phone: cleanPhone,
                    timestamp: Date.now()
                });

                // Show instructions
                this.dialog.add(AlertDialog, {
                    title: _t("✅ M-Pesa Request Sent"),
                    body: _t(
                        "**SYSTEM WILL AUTO-ADD PAYMENT**\n\n" +
                        "📱 Sent to: %s\n" +
                        "💰 Amount: Ksh %s\n" +
                        "📋 Order: %s\n\n" +
                        "**WHAT HAPPENS NEXT:**\n" +
                        "1. Customer receives M-Pesa prompt\n" +
                        "2. Customer enters PIN\n" +
                        "3. **BACKEND AUTO-ADDS PAYMENT**\n" +
                        "4. Screen updates automatically\n\n" +
                        "⏰ Waiting for payment confirmation..."
                    ).replace('%s', cleanPhone)
                     .replace('%s', floatAmount.toFixed(2))
                     .replace('%s', currentOrder.name),
                });

                this.notification.add(
                    _t("✅ M-Pesa sent! Backend will auto-add payment when confirmed."),
                    { type: "success", sticky: true }
                );
                
                // Start polling (just for status updates - backend handles auto-add)
                this._startStatusPolling(checkoutId, currentOrder, floatAmount);
                
                return true;

            } catch (error) {
                console.error("💥 M-Pesa exception:", error);
                this.dialog.add(AlertDialog, {
                    title: _t("Network Error"),
                    body: _t("Failed to communicate with M-Pesa:\n%s").replace('%s', error.message || "Unknown error"),
                });
                return false;
            }
        }

        // --- Other payment methods ---
        return super.addNewPaymentLine(paymentMethod);
    },

    _startStatusPolling(checkoutId, order, amount) {
        console.log("🔄 Starting status polling for:", checkoutId);
        
        this._stopPollingForOrder(order.name);
        
        const orderName = order.name;
        let isPolling = true;
        let pollCount = 0;
        
        const pollInterval = setInterval(async () => {
            if (!isPolling) {
                clearInterval(pollInterval);
                return;
            }
            
            pollCount++;
            
            // Check if still on same order
            const currentOrder = this.currentOrder;
            if (!currentOrder || currentOrder.name !== orderName) {
                console.log("🛑 Polling stopped: Order changed");
                isPolling = false;
                clearInterval(pollInterval);
                this.pollingIntervals.delete(orderName);
                this.pendingMpesaOrders.delete(orderName);
                return;
            }
            
            try {
                console.log(`🔍 Checking status (attempt ${pollCount})...`);
                
                const result = await this.orm.call(
                    "mpesa.transaction",
                    "check_stk_status",
                    [checkoutId, orderName]
                );
                
                console.log("📊 Status result:", result);
                
                if (result && result.success) {
                    // Payment confirmed by backend (should already be auto-added)
                    console.log(`✅ Payment confirmed by backend after ${pollCount} attempts`);
                    
                    // Just stop polling - backend already auto-added
                    isPolling = false;
                    clearInterval(pollInterval);
                    this._stopPollingForOrder(orderName);
                    
                    // Show final confirmation
                    if (result.auto_added) {
                        this.notification.add(
                            _t("✅ Payment auto-added by backend!"),
                            { type: "success", sticky: true }
                        );
                    }
                } else if (result && result.status === 'failed') {
                    // Payment failed
                    isPolling = false;
                    clearInterval(pollInterval);
                    this._stopPollingForOrder(orderName);
                    
                    this.notification.add(
                        _t("❌ M-Pesa payment failed"),
                        { type: "danger", sticky: true }
                    );
                }
                // If still pending, continue polling
                
            } catch (error) {
                console.error("❌ Polling error:", error);
            }
        }, 5000); // Poll every 5 seconds
        
        this.pollingIntervals.set(orderName, pollInterval);
        
        // Timeout after 5 minutes
        const timeoutId = setTimeout(() => {
            if (isPolling && this.pollingIntervals.has(orderName)) {
                isPolling = false;
                clearInterval(pollInterval);
                this._stopPollingForOrder(orderName);
                
                if (this.currentOrder && this.currentOrder.name === orderName) {
                    this.notification.add(
                        _t("⏰ Payment check timed out"),
                        { type: "warning" }
                    );
                }
            }
        }, 300000);
        
        this.pollingTimeouts.set(orderName, timeoutId);
    }
});