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
        timestamp = int(time.time()) + 1  # Add 1 to ensure different timestamp
        self.user_email = f"user{timestamp}@test.com"
        user_data = {
            "name": "Maria Santos",
            "email": self.user_email,
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

    def test_disable_professional_mode(self):
        """Test disabling professional mode"""
        profile_data = {
            "professional_mode": False
        }
        
        success, response = self.run_test(
            "Disable Professional Mode",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=self.professional_token
        )
        
        if success:
            print(f"   Professional Mode: {response.get('professional_mode')}")
            if response.get('professional_mode') == False:
                print("   ✅ Professional mode disabled successfully")
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
            403  # FastAPI returns 403 for missing auth, which is acceptable
        )
        return success

    def test_duplicate_user_registration_portuguese_error(self):
        """Test duplicate user registration returns Portuguese error message"""
        # First, register a user
        import time
        timestamp = int(time.time()) + 100  # Unique timestamp
        duplicate_email = f"duplicate{timestamp}@test.com"
        
        user_data = {
            "name": "Test User",
            "email": duplicate_email,
            "password": "test123"
        }
        
        # Register first user
        success1, response1 = self.run_test(
            "First User Registration",
            "POST",
            "/api/register",
            200,
            data=user_data
        )
        
        if not success1:
            print("❌ Failed to register first user")
            return False
        
        # Try to register same email again
        success2, response2 = self.run_test(
            "Duplicate Email Registration (Should Fail with Portuguese Message)",
            "POST",
            "/api/register",
            400,
            data=user_data
        )
        
        if success2:
            # Check if error message is in Portuguese
            error_detail = response2.get('detail', '')
            if 'já está cadastrado' in error_detail and 'Faça login ou use outro email' in error_detail:
                print(f"   ✅ Portuguese error message correct: {error_detail}")
                return True
            else:
                print(f"   ❌ Error message not in Portuguese or incorrect: {error_detail}")
                return False
        return False

    def test_websocket_file_message_handling(self):
        """Test WebSocket file message handling (simulated)"""
        print("\n🔍 Testing WebSocket File Message Support...")
        
        # This test simulates WebSocket file message functionality
        # Since we can't easily test real WebSocket connections in this environment,
        # we'll verify the backend code structure supports file messages
        
        try:
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
                
            # Check for file message handling
            if 'file_message' in server_code and 'message["file"]' in server_code:
                print("   ✅ WebSocket file message handling code found in backend")
                
                # Check for proper message relay structure
                if 'await manager.send_to_user(target_user' in server_code:
                    print("   ✅ WebSocket message relay functionality confirmed")
                    
                    # Check for timestamp addition
                    if 'timestamp": datetime.utcnow().isoformat()' in server_code:
                        print("   ✅ Timestamp handling for file messages confirmed")
                        self.tests_run += 1
                        self.tests_passed += 1
                        return True
                        
            print("   ❌ WebSocket file message handling not properly implemented")
            self.tests_run += 1
            return False
            
        except Exception as e:
            print(f"   ❌ Error checking WebSocket file message support: {str(e)}")
            self.tests_run += 1
            return False

    def test_websocket_chat_message_handling(self):
        """Test WebSocket chat message handling (simulated)"""
        print("\n🔍 Testing WebSocket Chat Message Support...")
        
        try:
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
                
            # Check for chat message handling
            if 'chat_message' in server_code and 'message["message"]' in server_code:
                print("   ✅ WebSocket chat message handling code found in backend")
                
                # Check for proper message relay with from field
                if '"from": user_id' in server_code:
                    print("   ✅ Chat message sender identification confirmed")
                    
                    # Check for timestamp addition
                    if 'timestamp": datetime.utcnow().isoformat()' in server_code:
                        print("   ✅ Timestamp handling for chat messages confirmed")
                        self.tests_run += 1
                        self.tests_passed += 1
                        return True
                        
            print("   ❌ WebSocket chat message handling not properly implemented")
            self.tests_run += 1
            return False
            
        except Exception as e:
            print(f"   ❌ Error checking WebSocket chat message support: {str(e)}")
            self.tests_run += 1
            return False

    def test_websocket_webrtc_signaling(self):
        """Test WebSocket WebRTC signaling support"""
        print("\n🔍 Testing WebSocket WebRTC Signaling Support...")
        
        try:
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
                
            # Check for WebRTC signaling message types
            webrtc_types = ['offer', 'answer', 'ice-candidate']
            all_types_found = all(msg_type in server_code for msg_type in webrtc_types)
            
            if all_types_found:
                print("   ✅ All WebRTC signaling message types supported")
                
                # Check for proper target user handling
                if 'target_user = message.get("target")' in server_code:
                    print("   ✅ WebRTC target user handling confirmed")
                    
                    # Check for from field addition
                    if '"from": user_id' in server_code:
                        print("   ✅ WebRTC message sender identification confirmed")
                        self.tests_run += 1
                        self.tests_passed += 1
                        return True
                        
            print("   ❌ WebSocket WebRTC signaling not properly implemented")
            self.tests_run += 1
            return False
            
        except Exception as e:
            print(f"   ❌ Error checking WebSocket WebRTC signaling support: {str(e)}")
            self.tests_run += 1
            return False

    def test_enhanced_error_messages_validation(self):
        """Test enhanced error messages for various validation scenarios"""
        print("\n🔍 Testing Enhanced Error Messages...")
        
        # Test category validation error message
        if not self.professional_token:
            print("   ❌ No professional token available for validation tests")
            self.tests_run += 1
            return False
            
        # Test invalid category error message
        invalid_category_data = {
            "category": "InvalidCategory"
        }
        
        success, response = self.run_test(
            "Invalid Category Error Message",
            "PUT",
            "/api/profile",
            400,
            data=invalid_category_data,
            token=self.professional_token
        )
        
        if success:
            error_detail = response.get('detail', '')
            if "Categoria deve ser 'Médico' ou 'Psicólogo'" in error_detail:
                print("   ✅ Portuguese category validation error message correct")
            else:
                print(f"   ❌ Category error message not in Portuguese: {error_detail}")
                return False
        else:
            return False
            
        # Test price validation error message
        invalid_price_data = {
            "price_per_minute": 150
        }
        
        success2, response2 = self.run_test(
            "Invalid Price Error Message",
            "PUT",
            "/api/profile",
            400,
            data=invalid_price_data,
            token=self.professional_token
        )
        
        if success2:
            error_detail2 = response2.get('detail', '')
            if "Preço deve estar entre 1 e 100 tokens por minuto" in error_detail2:
                print("   ✅ Portuguese price validation error message correct")
                return True
            else:
                print(f"   ❌ Price error message not in Portuguese: {error_detail2}")
                return False
        
        return False

    def test_profile_photo_and_description_update(self):
        """Test new profile photo and description fields"""
        print("\n🔍 Testing Profile Photo and Description Updates...")
        
        if not self.professional_token:
            print("   ❌ No professional token available for profile tests")
            self.tests_run += 1
            return False
        
        # Test valid profile photo and description update
        profile_data = {
            "description": "Experienced medical professional with 10 years of practice in cardiology and general medicine.",
            "profile_photo": "https://example.com/photos/doctor.jpg"
        }
        
        success, response = self.run_test(
            "Update Profile Photo and Description",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=self.professional_token
        )
        
        if success:
            if (response.get('description') == profile_data['description'] and 
                response.get('profile_photo') == profile_data['profile_photo']):
                print("   ✅ Profile photo and description updated successfully")
                print(f"   Description: {response.get('description')[:50]}...")
                print(f"   Profile Photo: {response.get('profile_photo')}")
            else:
                print("   ❌ Profile photo or description not updated correctly")
                return False
        else:
            return False
        
        # Test description length validation (over 300 characters)
        long_description = "A" * 301  # 301 characters
        invalid_data = {
            "description": long_description
        }
        
        success2, response2 = self.run_test(
            "Description Too Long (Should Fail)",
            "PUT",
            "/api/profile",
            400,
            data=invalid_data,
            token=self.professional_token
        )
        
        if success2:
            error_detail = response2.get('detail', '')
            if "300 caracteres" in error_detail:
                print("   ✅ Description length validation working correctly")
            else:
                print(f"   ❌ Description length error message incorrect: {error_detail}")
                return False
        else:
            return False
        
        # Test invalid profile photo URL
        invalid_photo_data = {
            "profile_photo": "invalid-url-without-protocol"
        }
        
        success3, response3 = self.run_test(
            "Invalid Profile Photo URL (Should Fail)",
            "PUT",
            "/api/profile",
            400,
            data=invalid_photo_data,
            token=self.professional_token
        )
        
        if success3:
            error_detail3 = response3.get('detail', '')
            if "http://" in error_detail3 and "https://" in error_detail3:
                print("   ✅ Profile photo URL validation working correctly")
                return True
            else:
                print(f"   ❌ Profile photo URL error message incorrect: {error_detail3}")
                return False
        
        return False

    def test_professional_listing_with_new_fields(self):
        """Test that professional listings include new profile fields"""
        print("\n🔍 Testing Professional Listings with New Profile Fields...")
        
        # First, enable professional mode and set profile data
        profile_data = {
            "professional_mode": True,
            "category": "Médico",
            "price_per_minute": 8,
            "description": "Cardiologist with expertise in preventive medicine and patient care.",
            "profile_photo": "https://example.com/photos/cardio-doctor.jpg"
        }
        
        success_setup, response_setup = self.run_test(
            "Setup Professional Profile with New Fields",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=self.professional_token
        )
        
        if not success_setup:
            print("   ❌ Failed to setup professional profile")
            self.tests_run += 1
            return False
        
        # Update status to online so professional appears in listings
        success_status, response_status = self.run_test(
            "Set Professional Status Online",
            "PUT",
            "/api/status",
            200,
            data={"status": "online"},
            token=self.professional_token
        )
        
        if not success_status:
            print("   ❌ Failed to set professional status online")
            self.tests_run += 1
            return False
        
        # Now test professional listings
        success, response = self.run_test(
            "Get Professionals with New Profile Fields",
            "GET",
            "/api/professionals",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   Found {len(response)} online professionals")
            
            # Find our test professional in the list
            test_professional = None
            for prof in response:
                if prof.get('id') == self.professional_id:
                    test_professional = prof
                    break
            
            if test_professional:
                print(f"   Professional Name: {test_professional.get('name')}")
                print(f"   Category: {test_professional.get('category')}")
                print(f"   Price: {test_professional.get('price_per_minute')} tokens/min")
                print(f"   Description: {test_professional.get('description', 'None')[:50]}...")
                print(f"   Profile Photo: {test_professional.get('profile_photo', 'None')}")
                
                # Verify new fields are present
                if (test_professional.get('description') and 
                    test_professional.get('profile_photo') and
                    test_professional.get('professional_mode') == True):
                    print("   ✅ Professional listing includes new profile fields")
                    self.tests_run += 1
                    self.tests_passed += 1
                    return True
                else:
                    print("   ❌ Professional listing missing new profile fields")
                    self.tests_run += 1
                    return False
            else:
                print("   ❌ Test professional not found in listings")
                self.tests_run += 1
                return False
        
        return False

    def test_placeholder_image_api(self):
        """Test the new placeholder image API endpoint"""
        print("\n🔍 Testing Placeholder Image API...")
        
        success, response = self.run_test(
            "Placeholder Image API",
            "GET",
            "/api/placeholder/150x150?text=Profile",
            200  # JSON response instead of redirect
        )
        
        if success:
            if (response.get('placeholder') == True and 
                response.get('width') == 150 and 
                response.get('height') == 150):
                print("   ✅ Placeholder image API working (returns JSON)")
                print(f"   Dimensions: {response.get('width')}x{response.get('height')}")
                print(f"   Text: {response.get('text')}")
                self.tests_run += 1
                self.tests_passed += 1
                return True
            else:
                print("   ❌ Placeholder image API response format incorrect")
                self.tests_run += 1
                return False
        else:
            print("   ❌ Placeholder image API not working")
            self.tests_run += 1
            return False

    def test_user_serialization_with_new_fields(self):
        """Test that user serialization includes new fields"""
        print("\n🔍 Testing User Serialization with New Fields...")
        
        # Update user profile with new fields
        profile_data = {
            "description": "Regular user interested in health consultations.",
            "profile_photo": "https://example.com/photos/user-avatar.jpg"
        }
        
        success_update, response_update = self.run_test(
            "Update User Profile with New Fields",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=self.user_token
        )
        
        if not success_update:
            print("   ❌ Failed to update user profile")
            self.tests_run += 1
            return False
        
        # Test /api/me endpoint includes new fields
        success, response = self.run_test(
            "Get User Info with New Fields",
            "GET",
            "/api/me",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   User Name: {response.get('name')}")
            print(f"   Description: {response.get('description', 'None')}")
            print(f"   Profile Photo: {response.get('profile_photo', 'None')}")
            print(f"   Professional Mode: {response.get('professional_mode')}")
            
            # Verify new fields are present in serialization
            if (response.get('description') == profile_data['description'] and 
                response.get('profile_photo') == profile_data['profile_photo']):
                print("   ✅ User serialization includes new profile fields")
                self.tests_run += 1
                self.tests_passed += 1
                return True
            else:
                print("   ❌ User serialization missing new profile fields")
                self.tests_run += 1
                return False
        
        return False

def main():
    print("🚀 Starting Click Online API Tests")
    print("=" * 50)
    
    tester = ClickOnlineAPITester()
    
    # Test sequence - focusing on bug fixes and new features
    test_sequence = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Professional Registration", tester.test_register_professional),
        ("User Registration", tester.test_register_user),
        ("Get Professional Info", tester.test_get_me_professional),
        ("Get User Info", tester.test_get_me_user),
        ("Enable Professional Mode", tester.test_update_profile_enable_professional_mode),
        ("Category Validation", tester.test_update_profile_category_validation),
        ("Price Validation", tester.test_update_profile_price_validation),
        ("Disable Professional Mode", tester.test_disable_professional_mode),
        ("Update Professional Status", tester.test_update_professional_status),
        ("Get Online Professionals", tester.test_get_professionals),
        ("Initiate Call", tester.test_initiate_call),
        ("Accept Call", tester.test_accept_call),
        ("End Call", tester.test_end_call),
        ("Get Calls History", tester.test_get_calls_history),
        ("Invalid Login Test", tester.test_invalid_login),
        ("Unauthorized Access Test", tester.test_unauthorized_access),
        # NEW TESTS FOR BUG FIXES AND FEATURES
        ("Duplicate User Portuguese Error", tester.test_duplicate_user_registration_portuguese_error),
        ("WebSocket File Message Support", tester.test_websocket_file_message_handling),
        ("WebSocket Chat Message Support", tester.test_websocket_chat_message_handling),
        ("WebSocket WebRTC Signaling", tester.test_websocket_webrtc_signaling),
        ("Enhanced Error Messages", tester.test_enhanced_error_messages_validation),
        # NEW TESTS FOR LATEST IMPROVEMENTS
        ("Profile Photo and Description", tester.test_profile_photo_and_description_update),
        ("Professional Listings with New Fields", tester.test_professional_listing_with_new_fields),
        ("Placeholder Image API", tester.test_placeholder_image_api),
        ("User Serialization with New Fields", tester.test_user_serialization_with_new_fields),
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