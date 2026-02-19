{
    "name": "Customer PIN in POS",
    "version": "1.0",
    "depends": ["point_of_sale", "sale"],   
    "data": [
        "security/ir.model.access.csv",
        "views/customer_pin_register.xml",    
        "views/customer_pin_report.xml", 
          
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "customerpin/static/src/js/product_screen.js",       
            "customerpin/static/src/js/customer_pin_popup.js",  
            "customerpin/static/src/xml/product_screen.xml",     
            "customerpin/static/src/xml/customer_pin_popup.xml"  
             
        ],
    },
}
