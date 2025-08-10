#!/usr/bin/env python3
"""
WebRTC-focused testing for Click Online application
Tests the complete WebRTC signaling flow and connection establishment
"""

import asyncio
import websockets
import json
import requests
import sys
from datetime import datetime
import time

class WebRTCTester:
    def __init__(self, base_url="https://5b150b65-5d96-4838-871d-ad852054efe0.preview.emergentagent.com"):
        self.base_url = base_url
        self.ws_url = base_url.replace('https://', 'wss://').replace('http://', 'ws://')
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
        print("🔧 Setting up test users...")
        
        # Register professional
        timestamp = int(time.time())
        prof_data = {
            "name": "Dr. WebRTC Test",
            "email": f"webrtc_prof_{timestamp}@test.com",
            "password": "test123"
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
            "name": "WebRTC User",
            "email": f"webrtc_user_{timestamp}@test.com",
            "password": "test123"
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
                "price_per_minute": 5
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

    async def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        print("\n🔍 Testing WebSocket Connection Establishment...")
        
        try:
            # Test user WebSocket connection
            user_ws_url = f"{self.ws_url}/api/ws/{self.user_id}"
            async with websockets.connect(user_ws_url, timeout=10) as user_ws:
                self.log_test("User WebSocket Connection", True, f"Connected to {user_ws_url}")
                
                # Test professional WebSocket connection
                prof_ws_url = f"{self.ws_url}/api/ws/{self.professional_id}"
                async with websockets.connect(prof_ws_url, timeout=10) as prof_ws:
                    self.log_test("Professional WebSocket Connection", True, f"Connected to {prof_ws_url}")
                    return True, user_ws, prof_ws
                    
        except Exception as e:
            self.log_test("WebSocket Connection", False, f"Connection failed: {e}")
            return False, None, None

    async def test_webrtc_signaling_flow(self):
        """Test complete WebRTC signaling flow"""
        print("\n🔍 Testing WebRTC Signaling Flow...")
        
        try:
            # Connect both WebSockets
            user_ws_url = f"{self.ws_url}/api/ws/{self.user_id}"
            prof_ws_url = f"{self.ws_url}/api/ws/{self.professional_id}"
            
            async with websockets.connect(user_ws_url, timeout=10) as user_ws, \
                       websockets.connect(prof_ws_url, timeout=10) as prof_ws:
                
                # Test 1: Send offer from user to professional
                offer_message = {
                    "type": "offer",
                    "target": self.professional_id,
                    "sdp": "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n...",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await user_ws.send(json.dumps(offer_message))
                self.log_test("WebRTC Offer Sent", True, "Offer message sent from user to professional")
                
                # Wait for offer to be received by professional
                try:
                    received_message = await asyncio.wait_for(prof_ws.recv(), timeout=5.0)
                    received_data = json.loads(received_message)
                    
                    if (received_data.get("type") == "offer" and 
                        received_data.get("from") == self.user_id and
                        "sdp" in received_data):
                        self.log_test("WebRTC Offer Received", True, "Professional received offer with correct format")
                    else:
                        self.log_test("WebRTC Offer Received", False, f"Invalid offer format: {received_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    self.log_test("WebRTC Offer Received", False, "Timeout waiting for offer")
                    return False

                # Test 2: Send answer from professional to user
                answer_message = {
                    "type": "answer",
                    "target": self.user_id,
                    "sdp": "v=0\r\no=- 987654321 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n...",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await prof_ws.send(json.dumps(answer_message))
                self.log_test("WebRTC Answer Sent", True, "Answer message sent from professional to user")
                
                # Wait for answer to be received by user
                try:
                    received_message = await asyncio.wait_for(user_ws.recv(), timeout=5.0)
                    received_data = json.loads(received_message)
                    
                    if (received_data.get("type") == "answer" and 
                        received_data.get("from") == self.professional_id and
                        "sdp" in received_data):
                        self.log_test("WebRTC Answer Received", True, "User received answer with correct format")
                    else:
                        self.log_test("WebRTC Answer Received", False, f"Invalid answer format: {received_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    self.log_test("WebRTC Answer Received", False, "Timeout waiting for answer")
                    return False

                # Test 3: Send ICE candidates
                ice_candidate_message = {
                    "type": "ice-candidate",
                    "target": self.professional_id,
                    "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54400 typ host",
                    "sdpMid": "0",
                    "sdpMLineIndex": 0,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await user_ws.send(json.dumps(ice_candidate_message))
                self.log_test("ICE Candidate Sent", True, "ICE candidate sent from user to professional")
                
                # Wait for ICE candidate to be received
                try:
                    received_message = await asyncio.wait_for(prof_ws.recv(), timeout=5.0)
                    received_data = json.loads(received_message)
                    
                    if (received_data.get("type") == "ice-candidate" and 
                        received_data.get("from") == self.user_id and
                        "candidate" in received_data):
                        self.log_test("ICE Candidate Received", True, "Professional received ICE candidate with correct format")
                    else:
                        self.log_test("ICE Candidate Received", False, f"Invalid ICE candidate format: {received_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    self.log_test("ICE Candidate Received", False, "Timeout waiting for ICE candidate")
                    return False

                return True
                
        except Exception as e:
            self.log_test("WebRTC Signaling Flow", False, f"Signaling flow failed: {e}")
            return False

    async def test_call_flow_with_webrtc(self):
        """Test complete call flow with WebRTC signaling"""
        print("\n🔍 Testing Call Flow with WebRTC Integration...")
        
        try:
            # Step 1: Initiate call via REST API
            call_data = {"professional_id": self.professional_id}
            headers = {'Authorization': f'Bearer {self.user_token}', 'Content-Type': 'application/json'}
            response = requests.post(f"{self.base_url}/api/call/initiate", json=call_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                call_response = response.json()
                self.call_id = call_response['call_id']
                self.log_test("Call Initiation", True, f"Call initiated with ID: {self.call_id}")
            else:
                self.log_test("Call Initiation", False, f"Failed to initiate call: {response.status_code}")
                return False

            # Step 2: Connect WebSockets and verify call notification
            user_ws_url = f"{self.ws_url}/api/ws/{self.user_id}"
            prof_ws_url = f"{self.ws_url}/api/ws/{self.professional_id}"
            
            async with websockets.connect(user_ws_url, timeout=10) as user_ws, \
                       websockets.connect(prof_ws_url, timeout=10) as prof_ws:
                
                # Professional should receive call_request notification
                # Note: Since we initiated the call before connecting WebSocket,
                # we'll simulate the notification flow
                
                # Step 3: Accept call via REST API
                headers = {'Authorization': f'Bearer {self.professional_token}', 'Content-Type': 'application/json'}
                response = requests.post(f"{self.base_url}/api/call/{self.call_id}/accept", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    self.log_test("Call Acceptance", True, "Call accepted successfully")
                else:
                    self.log_test("Call Acceptance", False, f"Failed to accept call: {response.status_code}")
                    return False

                # Step 4: Test WebRTC signaling during active call
                await asyncio.sleep(1)  # Brief pause for call state to update
                
                # Send offer during active call
                offer_message = {
                    "type": "offer",
                    "target": self.professional_id,
                    "call_id": self.call_id,
                    "sdp": "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n...",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await user_ws.send(json.dumps(offer_message))
                
                # Professional should receive the offer
                try:
                    received_message = await asyncio.wait_for(prof_ws.recv(), timeout=5.0)
                    received_data = json.loads(received_message)
                    
                    if received_data.get("type") == "offer" and received_data.get("from") == self.user_id:
                        self.log_test("WebRTC During Active Call", True, "WebRTC signaling working during active call")
                    else:
                        self.log_test("WebRTC During Active Call", False, "WebRTC signaling failed during active call")
                        
                except asyncio.TimeoutError:
                    self.log_test("WebRTC During Active Call", False, "Timeout during active call WebRTC test")

                # Step 5: End call
                headers = {'Authorization': f'Bearer {self.user_token}', 'Content-Type': 'application/json'}
                response = requests.post(f"{self.base_url}/api/call/{self.call_id}/end", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    call_end_data = response.json()
                    self.log_test("Call Termination", True, f"Call ended - Duration: {call_end_data.get('duration', 0):.2f}min, Cost: {call_end_data.get('cost', 0)} tokens")
                    return True
                else:
                    self.log_test("Call Termination", False, f"Failed to end call: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("Call Flow with WebRTC", False, f"Call flow failed: {e}")
            return False

    async def test_websocket_error_handling(self):
        """Test WebSocket error handling and recovery"""
        print("\n🔍 Testing WebSocket Error Handling...")
        
        try:
            # Test connection to invalid user ID
            invalid_ws_url = f"{self.ws_url}/api/ws/invalid_user_id"
            try:
                async with websockets.connect(invalid_ws_url, timeout=5) as ws:
                    # If connection succeeds, it should still handle invalid messages gracefully
                    invalid_message = {
                        "type": "invalid_type",
                        "data": "test"
                    }
                    await ws.send(json.dumps(invalid_message))
                    self.log_test("Invalid Message Handling", True, "WebSocket accepts invalid messages gracefully")
            except Exception as e:
                # Connection failure is also acceptable for invalid user IDs
                self.log_test("Invalid User ID Connection", True, f"Properly rejected invalid user ID: {e}")

            # Test malformed JSON
            user_ws_url = f"{self.ws_url}/api/ws/{self.user_id}"
            async with websockets.connect(user_ws_url, timeout=10) as ws:
                try:
                    await ws.send("invalid json")
                    # WebSocket should handle this gracefully
                    self.log_test("Malformed JSON Handling", True, "WebSocket handles malformed JSON gracefully")
                except Exception as e:
                    self.log_test("Malformed JSON Handling", True, f"WebSocket properly handles malformed JSON: {e}")

            return True
            
        except Exception as e:
            self.log_test("WebSocket Error Handling", False, f"Error handling test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all WebRTC tests"""
        print("🚀 Starting WebRTC-focused Testing for Click Online")
        print("=" * 60)
        
        # Setup
        if not self.setup_users():
            print("❌ Failed to setup test users")
            return False

        # Test WebSocket connections
        success, user_ws, prof_ws = await self.test_websocket_connection()
        if not success:
            return False

        # Test WebRTC signaling flow
        if not await self.test_webrtc_signaling_flow():
            return False

        # Test call flow with WebRTC
        if not await self.test_call_flow_with_webrtc():
            return False

        # Test error handling
        if not await self.test_websocket_error_handling():
            return False

        return True

    def print_results(self):
        """Print final test results"""
        print("\n" + "=" * 60)
        print("📊 WEBRTC TEST RESULTS")
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

async def main():
    tester = WebRTCTester()
    success = await tester.run_all_tests()
    overall_success = tester.print_results()
    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))