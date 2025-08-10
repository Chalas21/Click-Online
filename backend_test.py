import requests
import sys
import json
from datetime import datetime

class ClickOnlineAPITester:
    def __init__(self, base_url="https://5b150b65-5d96-4838-871d-ad852054efe0.preview.emergentagent.com"):
        self.base_url = base_url
        self.user_token = None
        self.professional_token = None
        self.user_id = None
        self.professional_id = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root endpoint"""
        return self.run_test("Root Endpoint", "GET", "/", 200)

    def test_register_professional(self):
        """Test professional registration"""
        professional_data = {
            "name": "Dr. João Silva",
            "email": "doctor@test.com",
            "password": "test123",
            "role": "professional",
            "specialization": "Médico Cardiologista",
            "price_per_minute": 10
        }
        
        success, response = self.run_test(
            "Professional Registration",
            "POST",
            "/api/register",
            200,
            data=professional_data
        )
        
        if success and 'access_token' in response:
            self.professional_token = response['access_token']
            self.professional_id = response['user']['id']
            print(f"   Professional ID: {self.professional_id}")
            return True
        return False

    def test_register_user(self):
        """Test user registration"""
        user_data = {
            "name": "Maria Santos",
            "email": "user@test.com",
            "password": "test123",
            "role": "user"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "/api/register",
            200,
            data=user_data
        )
        
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   User ID: {self.user_id}")
            print(f"   Token Balance: {response['user']['token_balance']}")
            return True
        return False

    def test_login_professional(self):
        """Test professional login"""
        login_data = {
            "email": "doctor@test.com",
            "password": "test123"
        }
        
        success, response = self.run_test(
            "Professional Login",
            "POST",
            "/api/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.professional_token = response['access_token']
            print(f"   Professional logged in successfully")
            return True
        return False

    def test_login_user(self):
        """Test user login"""
        login_data = {
            "email": "user@test.com",
            "password": "test123"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "/api/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            print(f"   User logged in successfully")
            return True
        return False

    def test_get_me_professional(self):
        """Test get current professional info"""
        success, response = self.run_test(
            "Get Professional Info",
            "GET",
            "/api/me",
            200,
            token=self.professional_token
        )
        
        if success:
            print(f"   Name: {response.get('name')}")
            print(f"   Role: {response.get('role')}")
            print(f"   Specialization: {response.get('specialization')}")
            print(f"   Status: {response.get('status')}")
            return True
        return False

    def test_get_me_user(self):
        """Test get current user info"""
        success, response = self.run_test(
            "Get User Info",
            "GET",
            "/api/me",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   Name: {response.get('name')}")
            print(f"   Role: {response.get('role')}")
            print(f"   Token Balance: {response.get('token_balance')}")
            return True
        return False

    def test_update_professional_status(self):
        """Test updating professional status to online"""
        success, response = self.run_test(
            "Update Professional Status to Online",
            "PUT",
            "/api/status",
            200,
            data={"status": "online"},
            token=self.professional_token
        )
        return success

    def test_get_professionals(self):
        """Test getting list of online professionals"""
        success, response = self.run_test(
            "Get Online Professionals",
            "GET",
            "/api/professionals",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   Found {len(response)} online professionals")
            for prof in response:
                print(f"   - {prof.get('name')}: {prof.get('specialization')} ({prof.get('price_per_minute')} tokens/min)")
            return True
        return False

    def test_initiate_call(self):
        """Test initiating a call to professional"""
        if not self.professional_id:
            print("❌ No professional ID available for call test")
            return False
            
        success, response = self.run_test(
            "Initiate Call",
            "POST",
            "/api/call/initiate",
            200,
            data={"professional_id": self.professional_id},
            token=self.user_token
        )
        
        if success and 'call_id' in response:
            self.call_id = response['call_id']
            print(f"   Call ID: {self.call_id}")
            return True
        return False

    def test_accept_call(self):
        """Test accepting a call"""
        if not hasattr(self, 'call_id'):
            print("❌ No call ID available for accept test")
            return False
            
        success, response = self.run_test(
            "Accept Call",
            "POST",
            f"/api/call/{self.call_id}/accept",
            200,
            token=self.professional_token
        )
        return success

    def test_end_call(self):
        """Test ending a call"""
        if not hasattr(self, 'call_id'):
            print("❌ No call ID available for end test")
            return False
            
        success, response = self.run_test(
            "End Call",
            "POST",
            f"/api/call/{self.call_id}/end",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   Duration: {response.get('duration', 0):.2f} minutes")
            print(f"   Cost: {response.get('cost', 0)} tokens")
            return True
        return False

    def test_get_calls_history(self):
        """Test getting calls history"""
        success, response = self.run_test(
            "Get Calls History",
            "GET",
            "/api/calls",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   Found {len(response)} calls in history")
            return True
        return False

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        login_data = {
            "email": "invalid@test.com",
            "password": "wrongpassword"
        }
        
        success, response = self.run_test(
            "Invalid Login (Should Fail)",
            "POST",
            "/api/login",
            401,
            data=login_data
        )
        return success

    def test_unauthorized_access(self):
        """Test accessing protected endpoint without token"""
        success, response = self.run_test(
            "Unauthorized Access (Should Fail)",
            "GET",
            "/api/me",
            401
        )
        return success

def main():
    print("🚀 Starting Click Online API Tests")
    print("=" * 50)
    
    tester = ClickOnlineAPITester()
    
    # Test sequence
    test_sequence = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Professional Registration", tester.test_register_professional),
        ("User Registration", tester.test_register_user),
        ("Professional Login", tester.test_login_professional),
        ("User Login", tester.test_login_user),
        ("Get Professional Info", tester.test_get_me_professional),
        ("Get User Info", tester.test_get_me_user),
        ("Update Professional Status", tester.test_update_professional_status),
        ("Get Online Professionals", tester.test_get_professionals),
        ("Initiate Call", tester.test_initiate_call),
        ("Accept Call", tester.test_accept_call),
        ("End Call", tester.test_end_call),
        ("Get Calls History", tester.test_get_calls_history),
        ("Invalid Login Test", tester.test_invalid_login),
        ("Unauthorized Access Test", tester.test_unauthorized_access),
    ]
    
    # Run all tests
    for test_name, test_func in test_sequence:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 FINAL RESULTS")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())