import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [user, setUser] = useState(null);
  const [professionals, setProfessionals] = useState([]);
  const [currentCall, setCurrentCall] = useState(null);
  const [localVideo, setLocalVideo] = useState(null);
  const [remoteVideo, setRemoteVideo] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatMinimized, setChatMinimized] = useState(true);
  const [loading, setLoading] = useState(false);
  const [incomingCall, setIncomingCall] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const localStreamRef = useRef(null);
  const websocketRef = useRef(null);

  // Authentication state
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: ''
  });

  // Settings form data
  const [settingsData, setSettingsData] = useState({
    name: '',
    professional_mode: false,
    category: 'Médico',
    price_per_minute: 1
  });

  // WebRTC Configuration
  const rtcConfig = {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' }
    ]
  };

  // Initialize WebSocket connection
  useEffect(() => {
    if (user && !websocketRef.current) {
      // Properly construct WebSocket URL for HTTPS->WSS and add /api prefix
      const wsUrl = API_BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://') + `/api/ws/${user.id}`;
      websocketRef.current = new WebSocket(wsUrl);
      
      websocketRef.current.onopen = () => {
        console.log('WebSocket connected successfully');
      };
      
      websocketRef.current.onerror = (error) => {
        console.error('WebSocket connection error:', error);
      };
      
      websocketRef.current.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        websocketRef.current = null;
      };
      
      websocketRef.current.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        
        switch (message.type) {
          case 'call_request':
            setIncomingCall(message);
            break;
            
          case 'call_accepted':
            await startCall(true); // true = is caller
            break;
            
          case 'offer':
            await handleOffer(message.sdp, message.from);
            break;
            
          case 'answer':
            await handleAnswer(message.sdp);
            break;
            
          case 'ice-candidate':
            await handleIceCandidate(message.candidate);
            break;
            
          case 'chat_message':
            setChatMessages(prev => [...prev, {
              from: message.from,
              message: message.message,
              timestamp: message.timestamp
            }]);
            break;
            
          case 'call_ended':
            endCall();
            alert(`Call ended. Duration: ${message.duration?.toFixed(1)} minutes. Cost: ${message.cost} tokens`);
            break;
        }
      };
    }
    
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
        websocketRef.current = null;
      }
    };
  }, [user]);

  // Load user data into settings when user changes
  useEffect(() => {
    if (user) {
      setSettingsData({
        name: user.name || '',
        professional_mode: user.professional_mode || false,
        category: user.category || 'Médico',
        price_per_minute: user.price_per_minute || 1
      });
    }
  }, [user]);

  // Load professionals when user logs in
  useEffect(() => {
    if (user) {
      loadProfessionals();
      const interval = setInterval(loadProfessionals, 10000); // Refresh every 10 seconds
      return () => clearInterval(interval);
    }
  }, [user]);

  const apiCall = async (endpoint, options = {}) => {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
    });

    if (response.status === 401) {
      localStorage.removeItem('token');
      setUser(null);
      return null;
    }

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Request failed');
    }
    return data;
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const endpoint = authMode === 'login' ? '/api/login' : '/api/register';
      const response = await apiCall(endpoint, {
        method: 'POST',
        body: JSON.stringify(formData),
      });

      if (response) {
        localStorage.setItem('token', response.access_token);
        setUser(response.user);
      }
    } catch (error) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
    }
  };

  const loadProfessionals = async () => {
    try {
      const data = await apiCall('/api/professionals');
      if (data) {
        setProfessionals(data);
      }
    } catch (error) {
      console.error('Failed to load professionals:', error);
    }
  };

  const updateSettings = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await apiCall('/api/profile', {
        method: 'PUT',
        body: JSON.stringify(settingsData),
      });

      if (response) {
        setUser(response);
        setShowSettings(false);
        alert('Perfil atualizado com sucesso!');
      }
    } catch (error) {
      alert('Erro ao atualizar perfil: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (status) => {
    try {
      await apiCall('/api/status', {
        method: 'PUT',
        body: JSON.stringify({ status }),
      });
      setUser(prev => ({ ...prev, status }));
    } catch (error) {
      alert('Failed to update status: ' + error.message);
    }
  };

  // WebRTC Functions
  const initializePeerConnection = () => {
    const peerConnection = new RTCPeerConnection(rtcConfig);
    
    peerConnection.onicecandidate = (event) => {
      if (event.candidate && websocketRef.current && currentCall) {
        websocketRef.current.send(JSON.stringify({
          type: 'ice-candidate',
          candidate: event.candidate,
          target: currentCall?.other_user_id
        }));
      }
    };
    
    peerConnection.ontrack = (event) => {
      console.log('Remote stream received:', event.streams[0]);
      if (remoteVideoRef.current && event.streams[0]) {
        remoteVideoRef.current.srcObject = event.streams[0];
        setRemoteVideo(event.streams[0]);
      }
    };

    peerConnection.onconnectionstatechange = () => {
      console.log('Connection state:', peerConnection.connectionState);
    };

    peerConnection.oniceconnectionstatechange = () => {
      console.log('ICE connection state:', peerConnection.iceConnectionState);
    };
    
    return peerConnection;
  };

  const startCall = async (isCaller) => {
    try {
      console.log('Starting call, isCaller:', isCaller);
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 }, 
        audio: true 
      });
      
      console.log('Local stream obtained:', stream);
      
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
        setLocalVideo(stream);
      }
      localStreamRef.current = stream;

      const peerConnection = initializePeerConnection();
      peerConnectionRef.current = peerConnection;

      // Add tracks to peer connection
      stream.getTracks().forEach(track => {
        console.log('Adding track to peer connection:', track.kind);
        peerConnection.addTrack(track, stream);
      });

      if (isCaller) {
        console.log('Creating offer...');
        const offer = await peerConnection.createOffer({
          offerToReceiveVideo: true,
          offerToReceiveAudio: true
        });
        await peerConnection.setLocalDescription(offer);
        
        console.log('Sending offer via WebSocket');
        websocketRef.current.send(JSON.stringify({
          type: 'offer',
          sdp: offer,
          target: currentCall.other_user_id
        }));
      }
    } catch (error) {
      console.error('Error starting call:', error);
      alert('Não foi possível acessar câmera/microfone: ' + error.message);
    }
  };

  const handleOffer = async (offer, from) => {
    console.log('Handling offer from:', from);
    
    const peerConnection = initializePeerConnection();
    peerConnectionRef.current = peerConnection;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 }, 
        audio: true 
      });
      
      console.log('Local stream obtained for callee:', stream);
      
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
        setLocalVideo(stream);
      }
      localStreamRef.current = stream;

      stream.getTracks().forEach(track => {
        console.log('Adding track to peer connection:', track.kind);
        peerConnection.addTrack(track, stream);
      });

      console.log('Setting remote description...');
      await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
      
      console.log('Creating answer...');
      const answer = await peerConnection.createAnswer({
        offerToReceiveVideo: true,
        offerToReceiveAudio: true
      });
      await peerConnection.setLocalDescription(answer);

      console.log('Sending answer via WebSocket');
      websocketRef.current.send(JSON.stringify({
        type: 'answer',
        sdp: answer,
        target: from
      }));

      setCurrentCall({ other_user_id: from, call_id: incomingCall.call_id });
    } catch (error) {
      console.error('Error handling offer:', error);
      alert('Erro ao processar chamada: ' + error.message);
    }
  };

  const handleAnswer = async (answer) => {
    console.log('Handling answer...');
    if (peerConnectionRef.current) {
      try {
        await peerConnectionRef.current.setRemoteDescription(new RTCSessionDescription(answer));
        console.log('Remote description set successfully');
      } catch (error) {
        console.error('Error setting remote description:', error);
      }
    }
  };

  const handleIceCandidate = async (candidate) => {
    console.log('Handling ICE candidate...');
    if (peerConnectionRef.current) {
      try {
        await peerConnectionRef.current.addIceCandidate(new RTCIceCandidate(candidate));
        console.log('ICE candidate added successfully');
      } catch (error) {
        console.error('Error adding ICE candidate:', error);
      }
    }
  };

  const initiateCall = async (professionalId) => {
    try {
      const response = await apiCall('/api/call/initiate', {
        method: 'POST',
        body: JSON.stringify({ professional_id: professionalId }),
      });

      if (response) {
        setCurrentCall({ 
          call_id: response.call_id, 
          other_user_id: professionalId,
          status: 'pending' 
        });
        setChatMessages([]);
      }
    } catch (error) {
      alert('Failed to initiate call: ' + error.message);
    }
  };

  const acceptCall = async () => {
    try {
      await apiCall(`/api/call/${incomingCall.call_id}/accept`, {
        method: 'POST',
      });
      setCurrentCall({ 
        call_id: incomingCall.call_id, 
        other_user_id: incomingCall.caller.id 
      });
      setIncomingCall(null);
    } catch (error) {
      alert('Failed to accept call: ' + error.message);
    }
  };

  const rejectCall = () => {
    setIncomingCall(null);
  };

  const endCall = async () => {
    if (currentCall) {
      try {
        await apiCall(`/api/call/${currentCall.call_id}/end`, {
          method: 'POST',
        });
      } catch (error) {
        console.error('Error ending call:', error);
      }
    }

    // Clean up WebRTC
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
    }
    
    peerConnectionRef.current = null;
    localStreamRef.current = null;
    setCurrentCall(null);
    setChatMessages([]);
    
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }
    if (remoteVideoRef.current) {
      remoteVideoRef.current.srcObject = null;
    }
  };

  const sendChatMessage = () => {
    if (chatInput.trim() && websocketRef.current && currentCall) {
      websocketRef.current.send(JSON.stringify({
        type: 'chat_message',
        message: chatInput,
        target: currentCall.other_user_id
      }));
      
      setChatMessages(prev => [...prev, {
        from: user.id,
        message: chatInput,
        timestamp: new Date().toISOString()
      }]);
      
      setChatInput('');
    }
  };

  // Check for existing token on app load
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      apiCall('/api/me').then(data => {
        if (data) {
          setUser(data);
        }
      }).catch(() => {
        localStorage.removeItem('token');
      });
    }
  }, []);

  // Login/Register Form
  if (!user) {
    return (
      <div className="app">
        <div className="auth-container">
          <div className="auth-card">
            <h1>Click Online</h1>
            <p>Videochamadas profissionais com pagamento por tokens</p>
            
            <div className="auth-tabs">
              <button 
                className={authMode === 'login' ? 'active' : ''}
                onClick={() => setAuthMode('login')}
              >
                Login
              </button>
              <button 
                className={authMode === 'register' ? 'active' : ''}
                onClick={() => setAuthMode('register')}
              >
                Cadastro
              </button>
            </div>

            <form onSubmit={handleAuth} className="auth-form">
              {authMode === 'register' && (
                <>
                  <input
                    type="text"
                    placeholder="Nome completo"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                  />
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({...formData, role: e.target.value})}
                  >
                    <option value="user">Usuário</option>
                    <option value="professional">Profissional</option>
                  </select>
                  {formData.role === 'professional' && (
                    <>
                      <input
                        type="text"
                        placeholder="Especialização (ex: Advogado, Médico)"
                        value={formData.specialization}
                        onChange={(e) => setFormData({...formData, specialization: e.target.value})}
                        required
                      />
                      <input
                        type="number"
                        placeholder="Preço por minuto (tokens)"
                        value={formData.price_per_minute}
                        onChange={(e) => setFormData({...formData, price_per_minute: parseInt(e.target.value) || 5})}
                        min="1"
                        max="100"
                      />
                    </>
                  )}
                </>
              )}
              
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
              />
              <input
                type="password"
                placeholder="Senha"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                required
              />
              
              <button type="submit" disabled={loading}>
                {loading ? 'Processando...' : (authMode === 'login' ? 'Entrar' : 'Cadastrar')}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // Main App Interface
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>Click Online</h1>
        <div className="header-info">
          <span>{user.name}</span>
          <span className="token-balance">💰 {user.token_balance} tokens</span>
          <button onClick={handleLogout} className="logout-btn">Sair</button>
        </div>
      </header>

      {/* Incoming Call Modal */}
      {incomingCall && (
        <div className="incoming-call-modal">
          <div className="modal-content">
            <h2>📞 Chamada recebida</h2>
            <p>De: {incomingCall.caller.name}</p>
            <div className="modal-actions">
              <button onClick={acceptCall} className="accept-btn">Aceitar</button>
              <button onClick={rejectCall} className="reject-btn">Recusar</button>
            </div>
          </div>
        </div>
      )}

      {/* Call Interface */}
      {currentCall ? (
        <div className="call-interface">
          <div className="video-container">
            <video 
              ref={remoteVideoRef} 
              autoPlay 
              playsInline 
              className="remote-video"
            />
            <video 
              ref={localVideoRef} 
              autoPlay 
              playsInline 
              muted 
              className="local-video"
            />
          </div>
          
          <div className="call-controls">
            <button onClick={endCall} className="end-call-btn">
              📞 Encerrar Chamada
            </button>
          </div>

          <div className="chat-container">
            <div className="chat-messages">
              {chatMessages.map((msg, index) => (
                <div key={index} className={`chat-message ${msg.from === user.id ? 'own' : 'other'}`}>
                  <div className="message-content">{msg.message}</div>
                  <div className="message-time">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
            <div className="chat-input">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Digite uma mensagem..."
                onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
              />
              <button onClick={sendChatMessage}>Enviar</button>
            </div>
          </div>
        </div>
      ) : (
        <div className="main-content">
          {user.role === 'professional' ? (
            // Professional Dashboard
            <div className="professional-dashboard">
              <div className="status-controls">
                <h2>Status: <span className={`status-${user.status}`}>{user.status}</span></h2>
                <div className="status-buttons">
                  <button 
                    onClick={() => updateStatus('online')}
                    className={user.status === 'online' ? 'active' : ''}
                  >
                    🟢 Online
                  </button>
                  <button 
                    onClick={() => updateStatus('offline')}
                    className={user.status === 'offline' ? 'active' : ''}
                  >
                    ⭕ Offline
                  </button>
                </div>
              </div>
              
              <div className="professional-info">
                <h3>Suas informações</h3>
                <p><strong>Especialização:</strong> {user.specialization}</p>
                <p><strong>Preço por minuto:</strong> {user.price_per_minute} tokens</p>
                <p><strong>Saldo:</strong> {user.token_balance} tokens</p>
              </div>
              
              <div className="waiting-message">
                {user.status === 'online' ? (
                  <p>🎯 Aguardando chamadas...</p>
                ) : (
                  <p>📴 Você está offline. Mude seu status para receber chamadas.</p>
                )}
              </div>
            </div>
          ) : (
            // User Dashboard
            <div className="user-dashboard">
              <h2>Profissionais Disponíveis</h2>
              
              {professionals.length === 0 ? (
                <p>Nenhum profissional online no momento.</p>
              ) : (
                <div className="professionals-grid">
                  {professionals.map(prof => (
                    <div key={prof.id} className="professional-card">
                      <div className="prof-header">
                        <h3>{prof.name}</h3>
                        <span className={`status-badge status-${prof.status}`}>
                          {prof.status === 'online' ? '🟢 Disponível' : '🟡 Ocupado'}
                        </span>
                      </div>
                      <p><strong>Especialização:</strong> {prof.specialization}</p>
                      <p><strong>Preço:</strong> {prof.price_per_minute} tokens/min</p>
                      <button
                        onClick={() => initiateCall(prof.id)}
                        disabled={prof.status !== 'online'}
                        className="call-btn"
                      >
                        {prof.status === 'online' ? '📞 Chamar' : '🔴 Ocupado'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;