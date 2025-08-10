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
        """Test user registration (unified system - all users start as regular users)"""
        import time
        timestamp = int(time.time())
        self.professional_email = f"doctor{timestamp}@test.com"
        professional_data = {
            "name": "Dr. João Silva",
            "email": self.professional_email,
            "password": "test123"
        }
        
        success, response = self.run_test(
            "Professional Registration (Unified System)",
            "POST",
            "/api/register",
            200,
            data=professional_data
        )
        
        if success and 'access_token' in response:
            self.professional_token = response['access_token']
            self.professional_id = response['user']['id']
            print(f"   Professional ID: {self.professional_id}")
            print(f"   Initial Token Balance: {response['user']['token_balance']}")
            print(f"   Professional Mode: {response['user']['professional_mode']}")
            print(f"   Role: {response['user']['role']}")
            # Verify new unified system defaults
            if response['user']['token_balance'] == 1000 and response['user']['professional_mode'] == False:
                print("   ✅ Unified system working: 1000 tokens, professional_mode=false")
            return True
        return False

    def test_register_user(self):
        """Test user registration (unified system)"""
        import time
        timestamp = int(time.time())
        user_data = {
            "name": "Maria Santos",
            "email": f"user{timestamp}@test.com",
            "password": "test123"
        }
        
        success, response = self.run_test(
            "User Registration (Unified System)",
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
            print(f"   Professional Mode: {response['user']['professional_mode']}")
            print(f"   Default Price Per Minute: {response['user']['price_per_minute']}")
            # Verify new unified system defaults
            if (response['user']['token_balance'] == 1000 and 
                response['user']['professional_mode'] == False and
                response['user']['price_per_minute'] == 1):
                print("   ✅ Unified system working: 1000 tokens, professional_mode=false, 1 token/min")
            return True
        return False

    def test_login_professional(self):
        """Test professional login"""
        # Use the same timestamp-based email from registration
        if not hasattr(self, 'professional_email'):
            print("❌ Professional email not available from registration")
            return False
            
        login_data = {
            "email": self.professional_email,
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
        # Use the same timestamp-based email from registration
        if not hasattr(self, 'user_email'):
            print("❌ User email not available from registration")
            return False
            
        login_data = {
            "email": self.user_email,
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
            print(f"   Professional Mode: {response.get('professional_mode')}")
            print(f"   Category: {response.get('category')}")
            print(f"   Status: {response.get('status')}")
            return True
        return False

    def test_update_profile_enable_professional_mode(self):
        """Test enabling professional mode via profile update"""
        profile_data = {
            "professional_mode": True,
            "category": "Médico",
            "price_per_minute": 5
        }
        
        success, response = self.run_test(
            "Enable Professional Mode",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=self.professional_token
        )
        
        if success:
            print(f"   Professional Mode: {response.get('professional_mode')}")
            print(f"   Category: {response.get('category')}")
            print(f"   Price Per Minute: {response.get('price_per_minute')}")
            if response.get('professional_mode') == True and response.get('category') == "Médico":
                print("   ✅ Professional mode enabled successfully")
            return True
        return False

    def test_update_profile_category_validation(self):
        """Test category validation in profile update"""
        # Test valid category
        profile_data = {
            "category": "Psicólogo"
        }
        
        success, response = self.run_test(
            "Update Category to Psicólogo",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=self.professional_token
        )
        
        if success and response.get('category') == "Psicólogo":
            print("   ✅ Valid category update successful")
        
        # Test invalid category
        invalid_profile_data = {
            "category": "InvalidCategory"
        }
        
        success_invalid, response_invalid = self.run_test(
            "Invalid Category (Should Fail)",
            "PUT",
            "/api/profile",
            400,
            data=invalid_profile_data,
            token=self.professional_token
        )
        
        if success_invalid:
            print("   ✅ Invalid category properly rejected")
        
        return success and success_invalid

    def test_update_profile_price_validation(self):
        """Test price validation in profile update"""
        # Test valid price
        profile_data = {
            "price_per_minute": 10
        }
        
        success, response = self.run_test(
            "Update Price to 10 tokens/min",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=self.professional_token
        )
        
        if success and response.get('price_per_minute') == 10:
            print("   ✅ Valid price update successful")
        
        # Test invalid price (too high)
        invalid_profile_data = {
            "price_per_minute": 150
        }
        
        success_invalid, response_invalid = self.run_test(
            "Invalid Price Too High (Should Fail)",
            "PUT",
            "/api/profile",
            400,
            data=invalid_profile_data,
            token=self.professional_token
        )
        
        if success_invalid:
            print("   ✅ Invalid high price properly rejected")
        
        # Test invalid price (too low)
        invalid_profile_data2 = {
            "price_per_minute": 0
        }
        
        success_invalid2, response_invalid2 = self.run_test(
            "Invalid Price Too Low (Should Fail)",
            "PUT",
            "/api/profile",
            400,
            data=invalid_profile_data2,
            token=self.professional_token
        )
        
        if success_invalid2:
            print("   ✅ Invalid low price properly rejected")
        
        return success and success_invalid and success_invalid2

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
        """Test getting list of online professionals (now filters by professional_mode)"""
        success, response = self.run_test(
            "Get Online Professionals (Professional Mode Filter)",
            "GET",
            "/api/professionals",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   Found {len(response)} online professionals")
            for prof in response:
                print(f"   - {prof.get('name')}: {prof.get('category')} ({prof.get('price_per_minute')} tokens/min)")
                print(f"     Professional Mode: {prof.get('professional_mode')}")
            if len(response) > 0:
                print("   ✅ Professional mode filtering working")
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
        ("Enable Professional Mode", tester.test_update_profile_enable_professional_mode),
        ("Category Validation", tester.test_update_profile_category_validation),
        ("Price Validation", tester.test_update_profile_price_validation),
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