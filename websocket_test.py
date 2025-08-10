import asyncio
import websockets
import json
import requests
import sys
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketTester:
    def __init__(self, base_url="https://5b150b65-5d96-4838-871d-ad852054efe0.preview.emergentagent.com"):
        self.base_url = base_url
        self.ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
        self.user_token = None
        self.professional_token = None
        self.user_id = None
        self.professional_id = None
        self.call_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_ws = None
        self.professional_ws = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        logger.info(f"Test: {name}, Success: {success}, Details: {details}")

    async def setup_users(self):
        """Setup test users via REST API"""
        print("\n🔧 Setting up test users...")
        
        # Generate unique emails with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Register professional
        professional_data = {
            "name": "Dr. Ana Costa",
            "email": f"ana.costa.{timestamp}@clinic.com",
            "password": "secure123",
            "role": "professional",
            "specialization": "Cardiologista",
            "price_per_minute": 8
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/register", json=professional_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.professional_token = data['access_token']
                self.professional_id = data['user']['id']
                print(f"   Professional registered: {self.professional_id}")
            else:
                print(f"   Professional registration failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"   Professional registration error: {e}")
            return False

        # Register user
        user_data = {
            "name": "Carlos Silva",
            "email": f"carlos.silva.{timestamp}@email.com",
            "password": "secure123",
            "role": "user"
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/register", json=user_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.user_token = data['access_token']
                self.user_id = data['user']['id']
                print(f"   User registered: {self.user_id}")
            else:
                print(f"   User registration failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"   User registration error: {e}")
            return False

        # Set professional status to online
        try:
            headers = {'Authorization': f'Bearer {self.professional_token}', 'Content-Type': 'application/json'}
            response = requests.put(f"{self.base_url}/api/status", json={"status": "online"}, headers=headers, timeout=10)
            if response.status_code == 200:
                print("   Professional status set to online")
            else:
                print(f"   Failed to set professional status: {response.status_code}")
        except Exception as e:
            print(f"   Status update error: {e}")

        return True

    async def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        print("\n🔌 Testing WebSocket Connections...")
        
        # Test user WebSocket connection
        try:
            user_ws_url = f"{self.ws_url}/api/ws/{self.user_id}"
            self.user_ws = await asyncio.wait_for(websockets.connect(user_ws_url), timeout=10)
            self.log_test("User WebSocket Connection", True, f"Connected to {user_ws_url}")
        except Exception as e:
            self.log_test("User WebSocket Connection", False, f"Error: {e}")
            return False

        # Test professional WebSocket connection
        try:
            prof_ws_url = f"{self.ws_url}/api/ws/{self.professional_id}"
            self.professional_ws = await asyncio.wait_for(websockets.connect(prof_ws_url), timeout=10)
            self.log_test("Professional WebSocket Connection", True, f"Connected to {prof_ws_url}")
        except Exception as e:
            self.log_test("Professional WebSocket Connection", False, f"Error: {e}")
            return False

        return True

    async def test_call_flow_notifications(self):
        """Test complete call flow with WebSocket notifications"""
        print("\n📞 Testing Call Flow Notifications...")
        
        if not self.user_ws or not self.professional_ws:
            self.log_test("Call Flow Setup", False, "WebSocket connections not established")
            return False

        # Step 1: Initiate call via REST API
        try:
            headers = {'Authorization': f'Bearer {self.user_token}', 'Content-Type': 'application/json'}
            response = requests.post(
                f"{self.base_url}/api/call/initiate",
                json={"professional_id": self.professional_id},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.call_id = data['call_id']
                self.log_test("Call Initiation", True, f"Call ID: {self.call_id}")
            else:
                self.log_test("Call Initiation", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Call Initiation", False, f"Error: {e}")
            return False

        # Step 2: Check if professional receives call_request notification
        try:
            message = await asyncio.wait_for(self.professional_ws.recv(), timeout=5.0)
            notification = json.loads(message)
            
            if notification.get("type") == "call_request" and notification.get("call_id") == self.call_id:
                self.log_test("Call Request Notification", True, f"Professional received call request")
            else:
                self.log_test("Call Request Notification", False, f"Unexpected message: {notification}")
                return False
        except asyncio.TimeoutError:
            self.log_test("Call Request Notification", False, "Timeout waiting for notification")
            return False
        except Exception as e:
            self.log_test("Call Request Notification", False, f"Error: {e}")
            return False

        # Step 3: Accept call via REST API
        try:
            headers = {'Authorization': f'Bearer {self.professional_token}', 'Content-Type': 'application/json'}
            response = requests.post(
                f"{self.base_url}/api/call/{self.call_id}/accept",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_test("Call Acceptance", True, "Call accepted successfully")
            else:
                self.log_test("Call Acceptance", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Call Acceptance", False, f"Error: {e}")
            return False

        # Step 4: Check if user receives call_accepted notification
        try:
            message = await asyncio.wait_for(self.user_ws.recv(), timeout=5.0)
            notification = json.loads(message)
            
            if notification.get("type") == "call_accepted" and notification.get("call_id") == self.call_id:
                self.log_test("Call Accepted Notification", True, "User received call accepted notification")
            else:
                self.log_test("Call Accepted Notification", False, f"Unexpected message: {notification}")
                return False
        except asyncio.TimeoutError:
            self.log_test("Call Accepted Notification", False, "Timeout waiting for notification")
            return False
        except Exception as e:
            self.log_test("Call Accepted Notification", False, f"Error: {e}")
            return False

        # Step 5: End call and test notification
        try:
            headers = {'Authorization': f'Bearer {self.user_token}', 'Content-Type': 'application/json'}
            response = requests.post(
                f"{self.base_url}/api/call/{self.call_id}/end",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_test("Call Termination", True, "Call ended successfully")
            else:
                self.log_test("Call Termination", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Call Termination", False, f"Error: {e}")
            return False

        # Step 6: Check if professional receives call_ended notification
        try:
            message = await asyncio.wait_for(self.professional_ws.recv(), timeout=5.0)
            notification = json.loads(message)
            
            if notification.get("type") == "call_ended" and notification.get("call_id") == self.call_id:
                self.log_test("Call Ended Notification", True, "Professional received call ended notification")
            else:
                self.log_test("Call Ended Notification", False, f"Unexpected message: {notification}")
                return False
        except asyncio.TimeoutError:
            self.log_test("Call Ended Notification", False, "Timeout waiting for notification")
            return False
        except Exception as e:
            self.log_test("Call Ended Notification", False, f"Error: {e}")
            return False

        return True

    async def test_webrtc_signaling(self):
        """Test WebRTC signaling messages"""
        print("\n🎥 Testing WebRTC Signaling...")
        
        if not self.user_ws or not self.professional_ws:
            self.log_test("WebRTC Signaling Setup", False, "WebSocket connections not established")
            return False

        # Test offer message
        offer_message = {
            "type": "offer",
            "target": self.professional_id,
            "sdp": "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"
        }
        
        try:
            await self.user_ws.send(json.dumps(offer_message))
            self.log_test("Send WebRTC Offer", True, "Offer sent from user")
        except Exception as e:
            self.log_test("Send WebRTC Offer", False, f"Error: {e}")
            return False

        # Check if professional receives the offer
        try:
            message = await asyncio.wait_for(self.professional_ws.recv(), timeout=5.0)
            received_offer = json.loads(message)
            
            if (received_offer.get("type") == "offer" and 
                received_offer.get("from") == self.user_id and
                "sdp" in received_offer):
                self.log_test("Receive WebRTC Offer", True, "Professional received offer")
            else:
                self.log_test("Receive WebRTC Offer", False, f"Unexpected message: {received_offer}")
                return False
        except asyncio.TimeoutError:
            self.log_test("Receive WebRTC Offer", False, "Timeout waiting for offer")
            return False
        except Exception as e:
            self.log_test("Receive WebRTC Offer", False, f"Error: {e}")
            return False

        # Test answer message
        answer_message = {
            "type": "answer",
            "target": self.user_id,
            "sdp": "v=0\r\no=- 987654321 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"
        }
        
        try:
            await self.professional_ws.send(json.dumps(answer_message))
            self.log_test("Send WebRTC Answer", True, "Answer sent from professional")
        except Exception as e:
            self.log_test("Send WebRTC Answer", False, f"Error: {e}")
            return False

        # Check if user receives the answer
        try:
            message = await asyncio.wait_for(self.user_ws.recv(), timeout=5.0)
            received_answer = json.loads(message)
            
            if (received_answer.get("type") == "answer" and 
                received_answer.get("from") == self.professional_id and
                "sdp" in received_answer):
                self.log_test("Receive WebRTC Answer", True, "User received answer")
            else:
                self.log_test("Receive WebRTC Answer", False, f"Unexpected message: {received_answer}")
                return False
        except asyncio.TimeoutError:
            self.log_test("Receive WebRTC Answer", False, "Timeout waiting for answer")
            return False
        except Exception as e:
            self.log_test("Receive WebRTC Answer", False, f"Error: {e}")
            return False

        # Test ICE candidate message
        ice_message = {
            "type": "ice-candidate",
            "target": self.professional_id,
            "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54400 typ host",
            "sdpMid": "0",
            "sdpMLineIndex": 0
        }
        
        try:
            await self.user_ws.send(json.dumps(ice_message))
            self.log_test("Send ICE Candidate", True, "ICE candidate sent from user")
        except Exception as e:
            self.log_test("Send ICE Candidate", False, f"Error: {e}")
            return False

        # Check if professional receives the ICE candidate
        try:
            message = await asyncio.wait_for(self.professional_ws.recv(), timeout=5.0)
            received_ice = json.loads(message)
            
            if (received_ice.get("type") == "ice-candidate" and 
                received_ice.get("from") == self.user_id and
                "candidate" in received_ice):
                self.log_test("Receive ICE Candidate", True, "Professional received ICE candidate")
            else:
                self.log_test("Receive ICE Candidate", False, f"Unexpected message: {received_ice}")
                return False
        except asyncio.TimeoutError:
            self.log_test("Receive ICE Candidate", False, "Timeout waiting for ICE candidate")
            return False
        except Exception as e:
            self.log_test("Receive ICE Candidate", False, f"Error: {e}")
            return False

        return True

    async def test_chat_messaging(self):
        """Test chat message relay functionality"""
        print("\n💬 Testing Chat Messaging...")
        
        if not self.user_ws or not self.professional_ws:
            self.log_test("Chat Messaging Setup", False, "WebSocket connections not established")
            return False

        # Send chat message from user to professional
        chat_message = {
            "type": "chat_message",
            "target": self.professional_id,
            "message": "Olá, doutor! Como está?"
        }
        
        try:
            await self.user_ws.send(json.dumps(chat_message))
            self.log_test("Send Chat Message", True, "Chat message sent from user")
        except Exception as e:
            self.log_test("Send Chat Message", False, f"Error: {e}")
            return False

        # Check if professional receives the chat message
        try:
            message = await asyncio.wait_for(self.professional_ws.recv(), timeout=5.0)
            received_chat = json.loads(message)
            
            if (received_chat.get("type") == "chat_message" and 
                received_chat.get("from") == self.user_id and
                received_chat.get("message") == "Olá, doutor! Como está?" and
                "timestamp" in received_chat):
                self.log_test("Receive Chat Message", True, "Professional received chat message")
            else:
                self.log_test("Receive Chat Message", False, f"Unexpected message: {received_chat}")
                return False
        except asyncio.TimeoutError:
            self.log_test("Receive Chat Message", False, "Timeout waiting for chat message")
            return False
        except Exception as e:
            self.log_test("Receive Chat Message", False, f"Error: {e}")
            return False

        # Send reply from professional to user
        reply_message = {
            "type": "chat_message",
            "target": self.user_id,
            "message": "Olá! Estou bem, obrigado. Como posso ajudá-lo?"
        }
        
        try:
            await self.professional_ws.send(json.dumps(reply_message))
            self.log_test("Send Chat Reply", True, "Chat reply sent from professional")
        except Exception as e:
            self.log_test("Send Chat Reply", False, f"Error: {e}")
            return False

        # Check if user receives the reply
        try:
            message = await asyncio.wait_for(self.user_ws.recv(), timeout=5.0)
            received_reply = json.loads(message)
            
            if (received_reply.get("type") == "chat_message" and 
                received_reply.get("from") == self.professional_id and
                received_reply.get("message") == "Olá! Estou bem, obrigado. Como posso ajudá-lo?" and
                "timestamp" in received_reply):
                self.log_test("Receive Chat Reply", True, "User received chat reply")
            else:
                self.log_test("Receive Chat Reply", False, f"Unexpected message: {received_reply}")
                return False
        except asyncio.TimeoutError:
            self.log_test("Receive Chat Reply", False, "Timeout waiting for chat reply")
            return False
        except Exception as e:
            self.log_test("Receive Chat Reply", False, f"Error: {e}")
            return False

        return True

    async def test_connection_error_handling(self):
        """Test WebSocket connection error handling"""
        print("\n🚨 Testing Connection Error Handling...")
        
        # Test connection to invalid user ID
        try:
            invalid_ws_url = f"{self.ws_url}/api/ws/invalid-user-id"
            invalid_ws = await asyncio.wait_for(websockets.connect(invalid_ws_url), timeout=5)
            await invalid_ws.close()
            self.log_test("Invalid User ID Connection", False, "Should have failed but didn't")
        except Exception as e:
            self.log_test("Invalid User ID Connection", True, f"Properly rejected: {e}")

        # Test connection to wrong endpoint
        try:
            wrong_endpoint_url = f"{self.ws_url}/ws/{self.user_id}"  # Missing /api prefix
            wrong_ws = await asyncio.wait_for(websockets.connect(wrong_endpoint_url), timeout=5)
            await wrong_ws.close()
            self.log_test("Wrong Endpoint Connection", False, "Should have failed but didn't")
        except Exception as e:
            self.log_test("Wrong Endpoint Connection", True, f"Properly rejected: {e}")

        return True

    async def cleanup(self):
        """Close WebSocket connections"""
        if self.user_ws:
            await self.user_ws.close()
        if self.professional_ws:
            await self.professional_ws.close()

    async def run_all_tests(self):
        """Run all WebSocket tests"""
        print("🚀 Starting WebSocket Tests for Click Online")
        print("=" * 60)
        
        try:
            # Setup
            if not await self.setup_users():
                print("❌ Failed to setup test users")
                return False

            # Test WebSocket connections
            if not await self.test_websocket_connection():
                print("❌ WebSocket connection tests failed")
                return False

            # Test call flow notifications
            if not await self.test_call_flow_notifications():
                print("❌ Call flow notification tests failed")
                return False

            # Test WebRTC signaling
            if not await self.test_webrtc_signaling():
                print("❌ WebRTC signaling tests failed")
                return False

            # Test chat messaging
            if not await self.test_chat_messaging():
                print("❌ Chat messaging tests failed")
                return False

            # Test error handling
            await self.test_connection_error_handling()

        finally:
            await self.cleanup()

        # Print results
        print("\n" + "=" * 60)
        print(f"📊 WEBSOCKET TEST RESULTS")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All WebSocket tests passed!")
            return True
        else:
            print("⚠️  Some WebSocket tests failed!")
            return False

async def main():
    tester = WebSocketTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))