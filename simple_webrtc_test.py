#!/usr/bin/env python3
"""
Simplified WebRTC testing for Click Online application
Tests WebRTC signaling and backend functionality
"""

import requests
import json
import sys
import time
from datetime import datetime

class SimpleWebRTCTester:
    def __init__(self, base_url="https://5b150b65-5d96-4838-871d-ad852054efe0.preview.emergentagent.com"):
        self.base_url = base_url
        self.user_token = None
        self.professional_token = None
        self.user_id = None
        self.professional_id = None
        self.call_id = None
        self.tests_run = 0
        self.tests_passed = 0

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")

    def setup_users(self):
        """Setup test users for WebRTC testing"""
        print("🔧 Setting up WebRTC test users...")
        
        # Register professional
        timestamp = int(time.time())
        prof_data = {
            "name": "Dr. WebRTC Professional",
            "email": f"webrtc_prof_{timestamp}@test.com",
            "password": "webrtc123"
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/register", json=prof_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.professional_token = data['access_token']
                self.professional_id = data['user']['id']
                print(f"   Professional registered: {self.professional_id}")
            else:
                print(f"   Failed to register professional: {response.status_code}")
                return False
        except Exception as e:
            print(f"   Error registering professional: {e}")
            return False

        # Register user
        user_data = {
            "name": "WebRTC Test User",
            "email": f"webrtc_user_{timestamp}@test.com",
            "password": "webrtc123"
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/register", json=user_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.user_token = data['access_token']
                self.user_id = data['user']['id']
                print(f"   User registered: {self.user_id}")
            else:
                print(f"   Failed to register user: {response.status_code}")
                return False
        except Exception as e:
            print(f"   Error registering user: {e}")
            return False

        # Enable professional mode
        try:
            profile_data = {
                "professional_mode": True,
                "category": "Médico",
                "price_per_minute": 3
            }
            headers = {'Authorization': f'Bearer {self.professional_token}', 'Content-Type': 'application/json'}
            response = requests.put(f"{self.base_url}/api/profile", json=profile_data, headers=headers, timeout=10)
            if response.status_code == 200:
                print("   Professional mode enabled")
            else:
                print(f"   Failed to enable professional mode: {response.status_code}")
                return False
        except Exception as e:
            print(f"   Error enabling professional mode: {e}")
            return False

        # Set professional status to online
        try:
            status_data = {"status": "online"}
            headers = {'Authorization': f'Bearer {self.professional_token}', 'Content-Type': 'application/json'}
            response = requests.put(f"{self.base_url}/api/status", json=status_data, headers=headers, timeout=10)
            if response.status_code == 200:
                print("   Professional status set to online")
                return True
            else:
                print(f"   Failed to set professional status: {response.status_code}")
                return False
        except Exception as e:
            print(f"   Error setting professional status: {e}")
            return False

    def test_webrtc_backend_support(self):
        """Test WebRTC backend support by examining server code"""
        print("\n🔍 Testing WebRTC Backend Support...")
        
        try:
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
            
            # Check for WebRTC signaling message types
            webrtc_types = ['offer', 'answer', 'ice-candidate']
            supported_types = []
            
            for msg_type in webrtc_types:
                if f'"{msg_type}"' in server_code:
                    supported_types.append(msg_type)
            
            if len(supported_types) == 3:
                self.log_test("WebRTC Message Types Support", True, f"All WebRTC types supported: {', '.join(supported_types)}")
            else:
                self.log_test("WebRTC Message Types Support", False, f"Missing types: {set(webrtc_types) - set(supported_types)}")
                return False
            
            # Check for proper message relay functionality
            if 'target_user = message.get("target")' in server_code:
                self.log_test("WebRTC Target User Handling", True, "Target user routing implemented")
            else:
                self.log_test("WebRTC Target User Handling", False, "Target user routing missing")
                return False
            
            # Check for sender identification
            if '"from": user_id' in server_code:
                self.log_test("WebRTC Sender Identification", True, "Sender identification implemented")
            else:
                self.log_test("WebRTC Sender Identification", False, "Sender identification missing")
                return False
            
            # Check for WebSocket manager
            if 'await manager.send_to_user' in server_code:
                self.log_test("WebRTC Message Relay", True, "WebSocket message relay functionality confirmed")
            else:
                self.log_test("WebRTC Message Relay", False, "WebSocket message relay missing")
                return False
            
            return True
            
        except Exception as e:
            self.log_test("WebRTC Backend Support", False, f"Error checking backend: {e}")
            return False

    def test_websocket_endpoint_availability(self):
        """Test WebSocket endpoint availability"""
        print("\n🔍 Testing WebSocket Endpoint Configuration...")
        
        try:
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
            
            # Check for WebSocket endpoint with /api prefix
            if '@app.websocket("/api/ws/{user_id}")' in server_code:
                self.log_test("WebSocket Endpoint Configuration", True, "WebSocket endpoint correctly configured with /api prefix")
            else:
                self.log_test("WebSocket Endpoint Configuration", False, "WebSocket endpoint missing /api prefix")
                return False
            
            # Check for connection manager
            if 'class ConnectionManager:' in server_code:
                self.log_test("WebSocket Connection Manager", True, "Connection manager class found")
            else:
                self.log_test("WebSocket Connection Manager", False, "Connection manager missing")
                return False
            
            # Check for user connection tracking
            if 'self.user_connections: Dict[str, str]' in server_code:
                self.log_test("User Connection Tracking", True, "User connection tracking implemented")
            else:
                self.log_test("User Connection Tracking", False, "User connection tracking missing")
                return False
            
            return True
            
        except Exception as e:
            self.log_test("WebSocket Endpoint Availability", False, f"Error checking endpoint: {e}")
            return False

    def test_call_flow_webrtc_integration(self):
        """Test call flow integration with WebRTC"""
        print("\n🔍 Testing Call Flow WebRTC Integration...")
        
        # Step 1: Initiate call
        try:
            call_data = {"professional_id": self.professional_id}
            headers = {'Authorization': f'Bearer {self.user_token}', 'Content-Type': 'application/json'}
            response = requests.post(f"{self.base_url}/api/call/initiate", json=call_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                call_response = response.json()
                self.call_id = call_response['call_id']
                self.log_test("Call Initiation for WebRTC", True, f"Call initiated: {self.call_id}")
            else:
                self.log_test("Call Initiation for WebRTC", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Call Initiation for WebRTC", False, f"Error: {e}")
            return False

        # Step 2: Accept call
        try:
            headers = {'Authorization': f'Bearer {self.professional_token}', 'Content-Type': 'application/json'}
            response = requests.post(f"{self.base_url}/api/call/{self.call_id}/accept", headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.log_test("Call Acceptance for WebRTC", True, "Call accepted - ready for WebRTC signaling")
            else:
                self.log_test("Call Acceptance for WebRTC", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Call Acceptance for WebRTC", False, f"Error: {e}")
            return False

        # Step 3: Verify call is active (ready for WebRTC)
        try:
            headers = {'Authorization': f'Bearer {self.user_token}', 'Content-Type': 'application/json'}
            response = requests.get(f"{self.base_url}/api/calls", headers=headers, timeout=10)
            
            if response.status_code == 200:
                calls = response.json()
                active_call = None
                for call in calls:
                    if call.get('id') == self.call_id and call.get('status') == 'active':
                        active_call = call
                        break
                
                if active_call:
                    self.log_test("Active Call State for WebRTC", True, "Call is active and ready for WebRTC signaling")
                else:
                    self.log_test("Active Call State for WebRTC", False, "Call not found in active state")
                    return False
            else:
                self.log_test("Active Call State for WebRTC", False, f"Failed to get calls: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Active Call State for WebRTC", False, f"Error: {e}")
            return False

        # Step 4: End call
        try:
            headers = {'Authorization': f'Bearer {self.user_token}', 'Content-Type': 'application/json'}
            response = requests.post(f"{self.base_url}/api/call/{self.call_id}/end", headers=headers, timeout=10)
            
            if response.status_code == 200:
                call_end_data = response.json()
                self.log_test("Call Termination after WebRTC", True, 
                            f"Call ended - Duration: {call_end_data.get('duration', 0):.2f}min, Cost: {call_end_data.get('cost', 0)} tokens")
                return True
            else:
                self.log_test("Call Termination after WebRTC", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Call Termination after WebRTC", False, f"Error: {e}")
            return False

    def test_webrtc_message_structure(self):
        """Test WebRTC message structure requirements"""
        print("\n🔍 Testing WebRTC Message Structure Requirements...")
        
        try:
            with open('/app/backend/server.py', 'r') as f:
                server_code = f.read()
            
            # Check for proper message structure handling
            required_patterns = [
                ('Message Type Handling', 'message["type"]'),
                ('Target User Extraction', 'message.get("target")'),
                ('Message Forwarding', '**message'),
                ('Sender Addition', '"from": user_id'),
                ('WebSocket Disconnect Handling', 'WebSocketDisconnect'),
                ('User Status Update on Disconnect', '"status": "offline"')
            ]
            
            all_passed = True
            for test_name, pattern in required_patterns:
                if pattern in server_code:
                    self.log_test(test_name, True, f"Pattern '{pattern}' found")
                else:
                    self.log_test(test_name, False, f"Pattern '{pattern}' missing")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log_test("WebRTC Message Structure", False, f"Error checking structure: {e}")
            return False

    def test_stun_server_configuration(self):
        """Test STUN server configuration (frontend check)"""
        print("\n🔍 Testing STUN Server Configuration...")
        
        try:
            # Check if frontend has WebRTC configuration
            with open('/app/frontend/src/App.js', 'r') as f:
                frontend_code = f.read()
            
            # Look for WebRTC configuration patterns
            webrtc_patterns = [
                ('RTCPeerConnection Usage', 'RTCPeerConnection'),
                ('STUN Server Configuration', 'stun:'),
                ('ICE Candidate Handling', 'onicecandidate'),
                ('Remote Stream Handling', 'ontrack'),
                ('WebSocket Integration', 'WebSocket')
            ]
            
            found_patterns = 0
            for test_name, pattern in webrtc_patterns:
                if pattern in frontend_code:
                    self.log_test(test_name, True, f"WebRTC pattern '{pattern}' found in frontend")
                    found_patterns += 1
                else:
                    self.log_test(test_name, False, f"WebRTC pattern '{pattern}' not found in frontend")
            
            if found_patterns >= 3:
                self.log_test("Overall WebRTC Frontend Configuration", True, f"Found {found_patterns}/5 WebRTC patterns")
                return True
            else:
                self.log_test("Overall WebRTC Frontend Configuration", False, f"Only found {found_patterns}/5 WebRTC patterns")
                return False
            
        except Exception as e:
            self.log_test("STUN Server Configuration", False, f"Error checking frontend: {e}")
            return False

    def run_all_tests(self):
        """Run all WebRTC tests"""
        print("🚀 Starting Comprehensive WebRTC Testing for Click Online")
        print("=" * 65)
        
        # Setup
        if not self.setup_users():
            print("❌ Failed to setup test users")
            return False

        # Test backend WebRTC support
        if not self.test_webrtc_backend_support():
            return False

        # Test WebSocket endpoint
        if not self.test_websocket_endpoint_availability():
            return False

        # Test call flow integration
        if not self.test_call_flow_webrtc_integration():
            return False

        # Test message structure
        if not self.test_webrtc_message_structure():
            return False

        # Test frontend configuration
        if not self.test_stun_server_configuration():
            return False

        return True

    def print_results(self):
        """Print final test results"""
        print("\n" + "=" * 65)
        print("📊 COMPREHENSIVE WEBRTC TEST RESULTS")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        if self.tests_run > 0:
            print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All WebRTC tests passed!")
            return True
        else:
            print("⚠️  Some WebRTC tests failed!")
            return False

def main():
    tester = SimpleWebRTCTester()
    success = tester.run_all_tests()
    overall_success = tester.print_results()
    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(main())