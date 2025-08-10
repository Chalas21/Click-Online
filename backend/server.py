from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import jwt
import bcrypt
import asyncio
import json
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from enum import Enum
import uuid
import logging

# Configuration
DATABASE_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"

app = FastAPI(title="Click Online API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
client = AsyncIOMotorClient(DATABASE_URL)
db = client.click_online

# Security
security = HTTPBearer()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket Manager for signaling
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        self.user_connections[user_id] = connection_id
        logger.info(f"User {user_id} connected with connection {connection_id}")
        return connection_id
    
    def disconnect(self, connection_id: str, user_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if user_id in self.user_connections:
            del self.user_connections[user_id]
        logger.info(f"User {user_id} disconnected")
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.user_connections:
            connection_id = self.user_connections[user_id]
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    self.disconnect(connection_id, user_id)

manager = ConnectionManager()

# Enums
class UserRole(str, Enum):
    USER = "user"
    PROFESSIONAL = "professional"

class UserStatus(str, Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"

class CallStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"

# Models
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    status: UserStatus
    category: Optional[str] = None
    price_per_minute: Optional[float] = None
    token_balance: int = 0
    professional_mode: bool = False

class CallRequest(BaseModel):
    professional_id: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    professional_mode: Optional[bool] = None
    category: Optional[str] = None
    price_per_minute: Optional[float] = None

class StatusUpdate(BaseModel):
    status: UserStatus

# Authentication utilities
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

async def get_current_user(user_id: str = Depends(verify_token)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["id"] = str(user["_id"])
    return user

# Helper functions
def serialize_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "status": user.get("status", "offline"),
        "category": user.get("category"),
        "price_per_minute": user.get("price_per_minute", 1),
        "token_balance": user.get("token_balance", 1000),  # Default 1000 tokens for MVP
        "professional_mode": user.get("professional_mode", False)
    }

# API Routes
@app.get("/")
async def root():
    return {"message": "Click Online API is running"}

@app.post("/api/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = {
        "name": user_data.name,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "role": "user",  # All users start as regular users
        "status": "offline",
        "token_balance": 1000,  # Give 1000 tokens for MVP
        "professional_mode": False,  # Can be activated later in settings
        "price_per_minute": 1,  # Default 1 token per minute
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    token = create_access_token({"sub": user_id})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user({**user_dict, "_id": result.inserted_id})
    }

@app.post("/api/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update status to online
    await db.users.update_one(
        {"_id": user["_id"]}, 
        {"$set": {"status": "online", "last_login": datetime.utcnow()}}
    )
    
    token = create_access_token({"sub": str(user["_id"])})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user({**user, "status": "online"})
    }

@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return serialize_user(current_user)

@app.put("/api/profile")
async def update_profile(profile_data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    update_fields = {}
    
    if profile_data.name is not None:
        update_fields["name"] = profile_data.name
        
    if profile_data.professional_mode is not None:
        update_fields["professional_mode"] = profile_data.professional_mode
        # If enabling professional mode, set default category if not provided
        if profile_data.professional_mode and profile_data.category is None:
            update_fields["category"] = "Médico"  # Default category
            
    if profile_data.category is not None:
        # Validate category
        if profile_data.category not in ["Médico", "Psicólogo"]:
            raise HTTPException(status_code=400, detail="Categoria deve ser 'Médico' ou 'Psicólogo'")
        update_fields["category"] = profile_data.category
        
    if profile_data.price_per_minute is not None:
        if profile_data.price_per_minute < 1 or profile_data.price_per_minute > 100:
            raise HTTPException(status_code=400, detail="Preço deve estar entre 1 e 100 tokens por minuto")
        update_fields["price_per_minute"] = profile_data.price_per_minute
    
    if update_fields:
        await db.users.update_one(
            {"_id": ObjectId(current_user["_id"])},
            {"$set": update_fields}
        )
        
        # Get updated user
        updated_user = await db.users.find_one({"_id": ObjectId(current_user["_id"])})
        return serialize_user(updated_user)
    
    return serialize_user(current_user)

@app.put("/api/status")
async def update_status(status_update: StatusUpdate, current_user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": {"status": status_update.status}}
    )
    
    return {"message": "Status updated successfully"}

@app.get("/api/professionals")
async def get_professionals():
    professionals = await db.users.find({
        "professional_mode": True,
        "status": {"$in": ["online", "busy"]}
    }).to_list(100)
    
    return [serialize_user(prof) for prof in professionals]

@app.post("/api/call/initiate")
async def initiate_call(call_request: CallRequest, current_user: dict = Depends(get_current_user)):
    # Check if professional exists and is online
    professional = await db.users.find_one({"_id": ObjectId(call_request.professional_id)})
    if not professional:
        raise HTTPException(status_code=404, detail="Professional not found")
    
    if professional["status"] != "online":
        raise HTTPException(status_code=400, detail="Professional is not available")
    
    # Check user balance
    if current_user.get("token_balance", 0) < 10:  # Minimum 10 tokens to start call
        raise HTTPException(status_code=400, detail="Insufficient tokens")
    
    # Create call record
    call_data = {
        "caller_id": str(current_user["_id"]),
        "callee_id": call_request.professional_id,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    result = await db.calls.insert_one(call_data)
    call_id = str(result.inserted_id)
    
    # Update professional status to busy
    await db.users.update_one(
        {"_id": ObjectId(call_request.professional_id)},
        {"$set": {"status": "busy"}}
    )
    
    # Notify professional via WebSocket
    await manager.send_to_user(call_request.professional_id, {
        "type": "call_request",
        "call_id": call_id,
        "caller": serialize_user(current_user)
    })
    
    return {"call_id": call_id, "status": "pending"}

@app.post("/api/call/{call_id}/accept")
async def accept_call(call_id: str, current_user: dict = Depends(get_current_user)):
    call = await db.calls.find_one({"_id": ObjectId(call_id)})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if call["callee_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Update call status
    await db.calls.update_one(
        {"_id": ObjectId(call_id)},
        {"$set": {"status": "active", "started_at": datetime.utcnow()}}
    )
    
    # Notify caller
    await manager.send_to_user(call["caller_id"], {
        "type": "call_accepted",
        "call_id": call_id
    })
    
    return {"message": "Call accepted"}

@app.post("/api/call/{call_id}/end")
async def end_call(call_id: str, current_user: dict = Depends(get_current_user)):
    call = await db.calls.find_one({"_id": ObjectId(call_id)})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    user_id = str(current_user["_id"])
    if user_id not in [call["caller_id"], call["callee_id"]]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Calculate duration and cost
    duration = 0
    cost = 0
    if call.get("started_at"):
        duration = (datetime.utcnow() - call["started_at"]).total_seconds() / 60  # minutes
        
        # Get professional's price
        professional = await db.users.find_one({"_id": ObjectId(call["callee_id"])})
        price_per_minute = professional.get("price_per_minute", 5)
        cost = max(10, int(duration * price_per_minute))  # Minimum 10 tokens
    
    # Update call record
    await db.calls.update_one(
        {"_id": ObjectId(call_id)},
        {
            "$set": {
                "status": "ended",
                "ended_at": datetime.utcnow(),
                "duration_minutes": duration,
                "cost_tokens": cost
            }
        }
    )
    
    # Transfer tokens
    if cost > 0:
        # Deduct from caller
        await db.users.update_one(
            {"_id": ObjectId(call["caller_id"])},
            {"$inc": {"token_balance": -cost}}
        )
        
        # Add to professional (minus platform fee)
        professional_earning = int(cost * 0.85)  # 15% platform fee
        await db.users.update_one(
            {"_id": ObjectId(call["callee_id"])},
            {"$inc": {"token_balance": professional_earning}}
        )
    
    # Update professional status back to online
    await db.users.update_one(
        {"_id": ObjectId(call["callee_id"])},
        {"$set": {"status": "online"}}
    )
    
    # Notify both parties
    other_user_id = call["callee_id"] if user_id == call["caller_id"] else call["caller_id"]
    await manager.send_to_user(other_user_id, {
        "type": "call_ended",
        "call_id": call_id,
        "duration": duration,
        "cost": cost
    })
    
    return {"message": "Call ended", "duration": duration, "cost": cost}

@app.get("/api/calls")
async def get_calls(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    calls = await db.calls.find({
        "$or": [
            {"caller_id": user_id},
            {"callee_id": user_id}
        ]
    }).sort("created_at", -1).limit(20).to_list(20)
    
    for call in calls:
        call["id"] = str(call["_id"])
        del call["_id"]
    
    return calls

# WebSocket for signaling
@app.websocket("/api/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    connection_id = await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle WebRTC signaling
            if message["type"] in ["offer", "answer", "ice-candidate"]:
                target_user = message.get("target")
                if target_user:
                    await manager.send_to_user(target_user, {
                        **message,
                        "from": user_id
                    })
            
            # Handle chat messages
            elif message["type"] == "chat_message":
                target_user = message.get("target")
                if target_user:
                    await manager.send_to_user(target_user, {
                        "type": "chat_message",
                        "message": message["message"],
                        "from": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
    except WebSocketDisconnect:
        manager.disconnect(connection_id, user_id)
        
        # Update user status to offline
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"status": "offline"}}
        )