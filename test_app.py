import unittest
from app import app
from models import db, User, BusRoute, BusPass, Attendance, NewsNotice

class CSMSSBusSystemTests(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Use a temporary in-memory database for testing, or use the seeded development db
        # We can test against the existing dev db, but let's test using the seeded SQLite database file to preserve data or test properly.
        # Since we've already seeded csmss_bus.db, let's keep the config database URI to test the actual database.
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_public_pages(self):
        """Test that all public endpoints render successfully."""
        print("Testing public pages...")
        
        # Home
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CSMSS', response.data)
        
        # Login Page
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign In', response.data)
        
        # Register Page
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Register', response.data)
        
        # Schedules Page
        response = self.client.get('/schedules')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Schedules', response.data)
        
        # Notices Page
        response = self.client.get('/notices')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Notice', response.data)
        
        # Contact Page
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Helpline', response.data)

    def login(self, email, password):
        return self.client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_authentication_rbac(self):
        """Test user login, redirect behaviour, and role-based access control (RBAC)."""
        print("Testing authentication & role-based dashboard access...")
        
        # 1. Admin Login
        response = self.login('admin@csmss.edu', 'admin123')
        self.assertIn(b'Admin Dashboard', response.data)
        self.assertIn(b'Total Revenue', response.data)
        
        # Admin trying to access student pages (admin gets redirected or blocked appropriately by RBAC)
        # Check that admin has admin page access
        response = self.client.get('/admin/routes')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'MH-20-EF-1234', response.data)
        
        self.logout()
        
        # 2. Staff Login
        response = self.login('staff@csmss.edu', 'staff123')
        self.assertIn(b'Staff Dashboard', response.data)
        self.assertIn(b'Attendance Log', response.data or b'')
        
        # Staff trying to access admin configurations (should redirect back to staff dashboard with flash)
        response = self.client.get('/admin/settings', follow_redirects=True)
        self.assertIn(b'Unauthorized access', response.data)
        
        self.logout()

        # 3. Student Login
        response = self.login('student@csmss.edu', 'student123')
        self.assertIn(b'Commuter Dashboard', response.data)
        self.assertIn(b'Aditya Deshmukh', response.data)
        
        # Test student routes_view page (the newly created student routes template)
        response = self.client.get('/student/routes')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Bus Routes & Timetables', response.data)
        self.assertIn(b'Active Campus Commutes', response.data)
        
        # Test student buy pass page
        response = self.client.get('/student/buy-pass')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Purchase / Renew Bus Pass', response.data)
        
        self.logout()

    def test_mock_payment_process(self):
        """Test buy pass payment gateway simulation."""
        print("Testing mock payment gateway simulation...")
        
        # Login student
        self.login('student@csmss.edu', 'student123')
        
        # Submit mock payment JSON POST
        response = self.client.post('/student/process-payment', data=dict(
            pass_type='Quarterly',
            price=1400.0,
            payment_method='Stripe Sim'
        ))
        
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertTrue(json_data['success'])
        self.assertIn('receipt_id', json_data)
        
        receipt_id = json_data['receipt_id']
        
        # Verify receipt page loads for this pass
        response = self.client.get(f'/student/receipt/{receipt_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Quarterly', response.data)
        self.assertIn(b'CSMSS Commute Receipt', response.data)

        self.logout()

if __name__ == '__main__':
    unittest.main()
