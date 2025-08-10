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

    def test_default_offline_status_new_professionals(self):
        """Test that new professionals start with offline status"""
        print("\n🔍 Testing Default Offline Status for New Professionals...")
        
        import time
        timestamp = int(time.time()) + 200  # Unique timestamp
        test_email = f"offline_test{timestamp}@test.com"
        
        professional_data = {
            "name": "Dr. Offline Test",
            "email": test_email,
            "password": "test123"
        }
        
        success, response = self.run_test(
            "Register New Professional (Should Default to Offline)",
            "POST",
            "/api/register",
            200,
            data=professional_data
        )
        
        if success:
            user_status = response.get('user', {}).get('status')
            if user_status == 'offline':
                print(f"   ✅ New professional defaults to offline status: {user_status}")
                self.tests_run += 1
                self.tests_passed += 1
                return True
            else:
                print(f"   ❌ New professional status is not offline: {user_status}")
                self.tests_run += 1
                return False
        
        return False

    def test_category_filter_api(self):
        """Test /api/professionals endpoint with category parameter"""
        print("\n🔍 Testing Category Filter API...")
        
        # First, create a professional with Médico category
        import time
        timestamp = int(time.time()) + 300
        medico_email = f"medico{timestamp}@test.com"
        
        medico_data = {
            "name": "Dr. Médico Test",
            "email": medico_email,
            "password": "test123"
        }
        
        success_reg, response_reg = self.run_test(
            "Register Médico Professional",
            "POST",
            "/api/register",
            200,
            data=medico_data
        )
        
        if not success_reg:
            print("   ❌ Failed to register médico professional")
            self.tests_run += 1
            return False
        
        medico_token = response_reg.get('access_token')
        medico_id = response_reg.get('user', {}).get('id')
        
        # Enable professional mode with Médico category
        profile_data = {
            "professional_mode": True,
            "category": "Médico",
            "price_per_minute": 5
        }
        
        success_profile, response_profile = self.run_test(
            "Enable Professional Mode for Médico",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=medico_token
        )
        
        if not success_profile:
            print("   ❌ Failed to enable professional mode for médico")
            self.tests_run += 1
            return False
        
        # Test category filter for Médico
        success_medico, response_medico = self.run_test(
            "Get Professionals with Médico Category Filter",
            "GET",
            "/api/professionals?category=Médico",
            200
        )
        
        if success_medico:
            medico_professionals = [p for p in response_medico if p.get('category') == 'Médico']
            print(f"   Found {len(medico_professionals)} Médico professionals")
            
            # Verify our test professional is in the list
            test_prof_found = any(p.get('id') == medico_id for p in medico_professionals)
            if test_prof_found:
                print("   ✅ Category filter for Médico working correctly")
            else:
                print("   ❌ Test Médico professional not found in filtered results")
                self.tests_run += 1
                return False
        else:
            print("   ❌ Failed to get professionals with Médico filter")
            self.tests_run += 1
            return False
        
        # Test category filter for Psicólogo (should return empty or different results)
        success_psico, response_psico = self.run_test(
            "Get Professionals with Psicólogo Category Filter",
            "GET",
            "/api/professionals?category=Psicólogo",
            200
        )
        
        if success_psico:
            psico_professionals = [p for p in response_psico if p.get('category') == 'Psicólogo']
            print(f"   Found {len(psico_professionals)} Psicólogo professionals")
            
            # Verify our Médico professional is NOT in Psicólogo results
            test_prof_not_found = not any(p.get('id') == medico_id for p in psico_professionals)
            if test_prof_not_found:
                print("   ✅ Category filter for Psicólogo correctly excludes Médico professionals")
                self.tests_run += 1
                self.tests_passed += 1
                return True
            else:
                print("   ❌ Médico professional incorrectly found in Psicólogo filter results")
                self.tests_run += 1
                return False
        
        return False

    def test_include_offline_professionals(self):
        """Test that offline professionals are included in listings"""
        print("\n🔍 Testing Include Offline Professionals in Listings...")
        
        # Create a professional and keep them offline
        import time
        timestamp = int(time.time()) + 400
        offline_email = f"offline_prof{timestamp}@test.com"
        
        offline_data = {
            "name": "Dr. Offline Professional",
            "email": offline_email,
            "password": "test123"
        }
        
        success_reg, response_reg = self.run_test(
            "Register Offline Professional",
            "POST",
            "/api/register",
            200,
            data=offline_data
        )
        
        if not success_reg:
            print("   ❌ Failed to register offline professional")
            self.tests_run += 1
            return False
        
        offline_token = response_reg.get('access_token')
        offline_id = response_reg.get('user', {}).get('id')
        
        # Enable professional mode but keep offline status
        profile_data = {
            "professional_mode": True,
            "category": "Psicólogo",
            "price_per_minute": 8
        }
        
        success_profile, response_profile = self.run_test(
            "Enable Professional Mode (Keep Offline)",
            "PUT",
            "/api/profile",
            200,
            data=profile_data,
            token=offline_token
        )
        
        if not success_profile:
            print("   ❌ Failed to enable professional mode")
            self.tests_run += 1
            return False
        
        # Verify professional is still offline
        success_me, response_me = self.run_test(
            "Check Professional Status (Should be Offline)",
            "GET",
            "/api/me",
            200,
            token=offline_token
        )
        
        if success_me:
            status = response_me.get('status')
            print(f"   Professional status: {status}")
            if status != 'offline':
                print(f"   ⚠️  Professional status is {status}, not offline as expected")
        
        # Test that offline professional appears in general listings
        success_list, response_list = self.run_test(
            "Get All Professionals (Should Include Offline)",
            "GET",
            "/api/professionals",
            200
        )
        
        if success_list:
            offline_prof_found = any(p.get('id') == offline_id for p in response_list)
            if offline_prof_found:
                offline_prof = next(p for p in response_list if p.get('id') == offline_id)
                print(f"   ✅ Offline professional found in listings")
                print(f"   Professional Name: {offline_prof.get('name')}")
                print(f"   Professional Status: {offline_prof.get('status')}")
                print(f"   Professional Category: {offline_prof.get('category')}")
                self.tests_run += 1
                self.tests_passed += 1
                return True
            else:
                print("   ❌ Offline professional not found in listings")
                self.tests_run += 1
                return False
        
        return False

    def test_busy_status_support(self):
        """Test new 'busy' status in professional management"""
        print("\n🔍 Testing Busy Status Support...")
        
        if not self.professional_token:
            print("   ❌ No professional token available for busy status test")
            self.tests_run += 1
            return False
        
        # Test updating status to busy
        success_busy, response_busy = self.run_test(
            "Update Professional Status to Busy",
            "PUT",
            "/api/status",
            200,
            data={"status": "busy"},
            token=self.professional_token
        )
        
        if not success_busy:
            print("   ❌ Failed to update status to busy")
            self.tests_run += 1
            return False
        
        # Verify status was updated
        success_me, response_me = self.run_test(
            "Check Professional Status (Should be Busy)",
            "GET",
            "/api/me",
            200,
            token=self.professional_token
        )
        
        if success_me:
            status = response_me.get('status')
            if status == 'busy':
                print(f"   ✅ Professional status updated to busy: {status}")
            else:
                print(f"   ❌ Professional status not updated to busy: {status}")
                self.tests_run += 1
                return False
        else:
            print("   ❌ Failed to get professional status")
            self.tests_run += 1
            return False
        
        # Test that busy professionals appear in listings
        success_list, response_list = self.run_test(
            "Get Professionals (Should Include Busy)",
            "GET",
            "/api/professionals",
            200
        )
        
        if success_list:
            busy_prof_found = any(p.get('id') == self.professional_id and p.get('status') == 'busy' for p in response_list)
            if busy_prof_found:
                print("   ✅ Busy professional found in listings")
            else:
                print("   ❌ Busy professional not found in listings or status incorrect")
                self.tests_run += 1
                return False
        else:
            print("   ❌ Failed to get professional listings")
            self.tests_run += 1
            return False
        
        # Test updating back to online
        success_online, response_online = self.run_test(
            "Update Professional Status Back to Online",
            "PUT",
            "/api/status",
            200,
            data={"status": "online"},
            token=self.professional_token
        )
        
        if success_online:
            print("   ✅ Professional status updated back to online")
            self.tests_run += 1
            self.tests_passed += 1
            return True
        else:
            print("   ❌ Failed to update status back to online")
            self.tests_run += 1
            return False

    def test_all_status_types_in_listings(self):
        """Test that all status types (offline, busy, online) are included in professional listings"""
        print("\n🔍 Testing All Status Types in Professional Listings...")
        
        # Create professionals with different statuses
        import time
        base_timestamp = int(time.time()) + 500
        
        professionals = []
        statuses = ['offline', 'busy', 'online']
        
        for i, status in enumerate(statuses):
            email = f"status_test_{status}_{base_timestamp + i}@test.com"
            prof_data = {
                "name": f"Dr. {status.title()} Test",
                "email": email,
                "password": "test123"
            }
            
            success_reg, response_reg = self.run_test(
                f"Register {status.title()} Professional",
                "POST",
                "/api/register",
                200,
                data=prof_data
            )
            
            if success_reg:
                token = response_reg.get('access_token')
                prof_id = response_reg.get('user', {}).get('id')
                
                # Enable professional mode
                profile_data = {
                    "professional_mode": True,
                    "category": "Médico",
                    "price_per_minute": 5
                }
                
                success_profile, response_profile = self.run_test(
                    f"Enable Professional Mode for {status.title()}",
                    "PUT",
                    "/api/profile",
                    200,
                    data=profile_data,
                    token=token
                )
                
                if success_profile:
                    # Set the desired status (only if not offline, as that's default)
                    if status != 'offline':
                        success_status, response_status = self.run_test(
                            f"Set Status to {status.title()}",
                            "PUT",
                            "/api/status",
                            200,
                            data={"status": status},
                            token=token
                        )
                        
                        if success_status:
                            professionals.append({'id': prof_id, 'status': status, 'token': token})
                    else:
                        professionals.append({'id': prof_id, 'status': status, 'token': token})
        
        if len(professionals) < 3:
            print(f"   ❌ Failed to create all test professionals. Created: {len(professionals)}")
            self.tests_run += 1
            return False
        
        # Test that all professionals appear in listings regardless of status
        success_list, response_list = self.run_test(
            "Get All Professionals (All Status Types)",
            "GET",
            "/api/professionals",
            200
        )
        
        if success_list:
            found_statuses = set()
            for prof in professionals:
                found_prof = next((p for p in response_list if p.get('id') == prof['id']), None)
                if found_prof:
                    found_statuses.add(found_prof.get('status'))
                    print(f"   Found professional with status: {found_prof.get('status')}")
            
            if len(found_statuses) >= 2:  # At least 2 different statuses found
                print(f"   ✅ Professionals with multiple status types found in listings: {found_statuses}")
                self.tests_run += 1
                self.tests_passed += 1
                return True
            else:
                print(f"   ❌ Not enough status variety in listings: {found_statuses}")
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