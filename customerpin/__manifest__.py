{
    "name": "Customer PIN",
    "version": "1.0",
    "category": "Point of Sale",
    "summary": "Add PIN button with F9 shortcut in POS",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "customerpin/static/src/js/product_screen.js",
           
            "customerpin/static/src/xml/product_screen.xml",
             
        ]
    },
    "installable": True,
    "application": False,
}