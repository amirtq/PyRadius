from django.test import TestCase
from .models import RadiusUser

class RadiusUserTest(TestCase):
    def test_check_password_cleartext(self):
        user = RadiusUser(username='testuser_clear')
        user.set_password('secret123', use_cleartext=True)
        
        # Verify internal storage format
        self.assertTrue(user.password_hash.startswith('ctp:'))
        
        # Verify check_password works
        self.assertTrue(user.check_password('secret123'))
        self.assertFalse(user.check_password('wrong'))
        
    def test_check_password_hashed(self):
        user = RadiusUser(username='testuser_hashed')
        user.set_password('secret456')
        
        self.assertFalse(user.password_hash.startswith('ctp:'))
        
        self.assertTrue(user.check_password('secret456'))
        self.assertFalse(user.check_password('wrong'))
