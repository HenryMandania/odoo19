/** @odoo-module **/

import { Orderline } from "@point_of_sale/app/screens/product_screen/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, {
    get lineScreenValues() {
        // Run the original Odoo logic first
        const vals = super.lineScreenValues;
        
        // Add the Internal Reference (default_code) to the display values
        vals.default_code = this.props.line.product_id?.default_code || null;
        
        return vals;
    },
});