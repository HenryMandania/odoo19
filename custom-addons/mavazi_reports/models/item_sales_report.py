from odoo import models, fields, tools


class MemorisedItemSalesReport(models.Model):
    _name = 'memorised.item.sales.report'
    _description = 'Memorised Item Sales Report'
    _auto = False
    _order = 'product_name'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=True
    )

    product_reference = fields.Char(
        string='Product Reference',
        readonly=True
    )

    product_name = fields.Char(
        string='Product Name',
        readonly=True
    )

    category_id = fields.Many2one(
        'product.category',
        string='Category',
        readonly=True
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company / Branch',
        readonly=True
    )

    date_order = fields.Datetime(
        string='Date',
        readonly=True
    )

    qty_sold = fields.Float(
        string='Qty Sold',
        readonly=True
    )

    net_sales = fields.Float(
        string='Net Sales',
        readonly=True
    )

    vat_amount = fields.Float(
        string='VAT Amount',
        readonly=True
    )

    gross_sales = fields.Float(
        string='Gross Sales',
        readonly=True
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW memorised_item_sales_report AS (
                SELECT
                    MIN(pol.id) AS id,
                    pol.product_id AS product_id,
                    pp.default_code AS product_reference,
                    pt.name->>'en_US' AS product_name,
                    pt.categ_id AS category_id,
                    seller.partner_id AS vendor_id,
                    po.company_id AS company_id,
                    po.date_order AS date_order,

                    SUM(pol.qty) AS qty_sold,
                    SUM(pol.price_subtotal) AS net_sales,
                    SUM(pol.price_subtotal_incl - pol.price_subtotal) AS vat_amount,
                    SUM(pol.price_subtotal_incl) AS gross_sales

                FROM pos_order_line pol

                INNER JOIN pos_order po
                    ON po.id = pol.order_id

                INNER JOIN product_product pp
                    ON pp.id = pol.product_id

                INNER JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id

                LEFT JOIN LATERAL (
                    SELECT psi.partner_id
                    FROM product_supplierinfo psi
                    WHERE psi.product_tmpl_id = pt.id
                    ORDER BY psi.sequence ASC, psi.id ASC
                    LIMIT 1
                ) seller ON TRUE

                WHERE po.state IN ('paid', 'done', 'invoiced')

                GROUP BY
                    pol.product_id,
                    pp.default_code,
                    pt.name,
                    pt.categ_id,
                    seller.partner_id,
                    po.company_id,
                    po.date_order
            )
        """)