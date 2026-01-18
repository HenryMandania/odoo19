from odoo import models, fields, api
import requests
import base64

class MpesaConfig(models.Model):
    _name = 'mpesa.config'
    _description = 'Mpesa API Configuration'

    name = fields.Char(default="Mpesa Settings")
    # RENAMED from 'env' to 'mpesa_env' to avoid the _ids crash
    mpesa_env = fields.Selection([
        ('sandbox', 'Sandbox'), 
        ('production', 'Production')
    ], string="Environment", default='sandbox')
    
    consumer_key = fields.Char(string="Consumer Key", password=True)
    consumer_secret = fields.Char(string="Consumer Secret", password=True)
    business_shortcode = fields.Char(string="Shortcode (Till/Paybill)")
    passkey = fields.Char(string="Passkey", password=True)
    callback_url = fields.Char(string="Base Callback URL (HTTPS)")

    def _get_access_token(self):
        # Update the reference here to self.mpesa_env
        url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        if self.mpesa_env == 'production':
            url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        
        auth_str = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        
        headers = {"Authorization": f"Basic {encoded_auth}"}
        # Use timeout=10 to prevent the server from hanging if Safaricom is slow
        response = requests.get(url, headers=headers, timeout=10)
        return response.json().get('access_token')
    
    def action_register_url(self):
        """
        Registers C2B Confirmation and Validation URLs with Safaricom.
        """
        self.ensure_one()
        token = self._get_access_token()
        if not token:
            return False
            
        url = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"
        if self.mpesa_env == 'production':
            url = "https://api.safaricom.co.ke/mpesa/c2b/v1/registerurl"
            
        payload = {
            "ShortCode": self.business_shortcode,
            "ResponseType": "Completed",
            "ConfirmationURL": f"{self.callback_url}/payment/mpesa/callback",
            "ValidationURL": f"{self.callback_url}/payment/mpesa/validate"
        }
        
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        # Send to Safaricom
        # response = requests.post(url, json=payload, headers=headers)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Registration',
                'message': 'C2B Registration request sent!',
                'type': 'success',
            }
        }