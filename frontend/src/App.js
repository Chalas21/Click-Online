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
  const [fileUpload, setFileUpload] = useState(null);
  const [availableDevices, setAvailableDevices] = useState({ cameras: [], microphones: [] });
  const [showCategorySelection, setShowCategorySelection] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);

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
    price_per_minute: 1,
    description: '',
    profile_photo: ''
  });

  // WebRTC Configuration with additional STUN servers
  const rtcConfig = {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
      { urls: 'stun:stun2.l.google.com:19302' },
      { urls: 'stun:stun3.l.google.com:19302' }
    ],
    iceCandidatePoolSize: 10
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
            
          case 'file_message':
            setChatMessages(prev => [...prev, {
              from: message.from,
              file: message.file,
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
        price_per_minute: user.price_per_minute || 1,
        description: user.description || '',
        profile_photo: user.profile_photo || ''
      });
    }
  }, [user]);

  // Load professionals after category selection
  useEffect(() => {
    if (user && selectedCategory) {
      loadProfessionals(selectedCategory);
      const interval = setInterval(() => loadProfessionals(selectedCategory), 10000);
      return () => clearInterval(interval);
    }
  }, [user, selectedCategory]);

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

  const loadProfessionals = async (category = null) => {
    try {
      const endpoint = category ? `/api/professionals?category=${encodeURIComponent(category)}` : '/api/professionals';
      const data = await apiCall(endpoint);
      if (data) {
        setProfessionals(data);
      }
    } catch (error) {
      console.error('Failed to load professionals:', error);
    }
  };

  // Request media permissions and detect available devices
  const detectAvailableDevices = async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cameras = devices.filter(device => device.kind === 'videoinput');
      const microphones = devices.filter(device => device.kind === 'audioinput');
      
      setAvailableDevices({ cameras, microphones });
      
      console.log('Detected cameras:', cameras.length);
      console.log('Detected microphones:', microphones.length);
      
      return { cameras, microphones };
    } catch (error) {
      console.error('Error detecting devices:', error);
      return { cameras: [], microphones: [] };
    }
  };

  // Request media permissions
  const requestMediaPermissions = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 }, 
        audio: true 
      });
      
      // Detect devices after getting permission
      await detectAvailableDevices();
      
      // Stop the stream immediately after getting permission
      stream.getTracks().forEach(track => track.stop());
      return true;
    } catch (error) {
      console.error('Media permission denied:', error);
      alert('É necessário permitir o acesso à câmera e microfone para realizar videochamadas.');
      return false;
    }
  };

  // Initialize device detection on component mount
  useEffect(() => {
    detectAvailableDevices();
  }, []);

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

  const selectCategory = (category) => {
    setSelectedCategory(category);
    setShowCategorySelection(false);
    loadProfessionals(category);
  };

  const backToCategorySelection = () => {
    setSelectedCategory(null);
    setShowCategorySelection(true);
    setProfessionals([]);
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
    console.log('Initializing peer connection...');
    const peerConnection = new RTCPeerConnection(rtcConfig);
    
    // ICE candidate handling
    peerConnection.onicecandidate = (event) => {
      console.log('ICE candidate event:', event.candidate);
      if (event.candidate && websocketRef.current && currentCall) {
        console.log('Sending ICE candidate via WebSocket');
        websocketRef.current.send(JSON.stringify({
          type: 'ice-candidate',
          candidate: event.candidate,
          target: currentCall?.other_user_id
        }));
      } else if (!event.candidate) {
        console.log('ICE gathering completed');
      }
    };
    
    // Remote stream handling - CRITICAL for receiving audio/video
    peerConnection.ontrack = (event) => {
      console.log('🎥 REMOTE TRACK RECEIVED!');
      console.log('Remote streams count:', event.streams.length);
      console.log('Remote tracks:', event.streams[0]?.getTracks().map(t => ({ kind: t.kind, enabled: t.enabled, readyState: t.readyState })));
      
      if (event.streams && event.streams[0]) {
        const remoteStream = event.streams[0];
        console.log('Setting remote stream to video element');
        
        if (remoteVideoRef.current) {
          remoteVideoRef.current.srcObject = remoteStream;
          setRemoteVideo(remoteStream);
          
          // Ensure video plays
          remoteVideoRef.current.play().catch(e => {
            console.warn('Error playing remote video:', e);
          });
        }
      }
    };

    // Connection state monitoring
    peerConnection.onconnectionstatechange = () => {
      console.log('🔗 Connection state changed:', peerConnection.connectionState);
      
      if (peerConnection.connectionState === 'connected') {
        console.log('✅ WebRTC connection established!');
      } else if (peerConnection.connectionState === 'failed') {
        console.log('❌ WebRTC connection failed');
        // Attempt to restart ICE
        peerConnection.restartIce();
      } else if (peerConnection.connectionState === 'disconnected') {
        console.log('🔌 WebRTC connection disconnected');
      }
    };

    // ICE connection state monitoring
    peerConnection.oniceconnectionstatechange = () => {
      console.log('🧊 ICE connection state:', peerConnection.iceConnectionState);
      
      if (peerConnection.iceConnectionState === 'connected' || 
          peerConnection.iceConnectionState === 'completed') {
        console.log('✅ ICE connection successful!');
      } else if (peerConnection.iceConnectionState === 'failed') {
        console.log('❌ ICE connection failed');
      }
    };

    // ICE gathering state
    peerConnection.onicegatheringstatechange = () => {
      console.log('❄️ ICE gathering state:', peerConnection.iceGatheringState);
    };

    // Signaling state monitoring
    peerConnection.onsignalingstatechange = () => {
      console.log('📡 Signaling state:', peerConnection.signalingState);
    };
    
    return peerConnection;
  };

  const startCall = async (isCaller) => {
    try {
      console.log('🚀 Starting call, isCaller:', isCaller);
      
      // Request permissions first if we haven't already
      const hasPermissions = await requestMediaPermissions();
      if (!hasPermissions) {
        return;
      }
      
      console.log('📹 Getting user media...');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 }, 
          height: { ideal: 480 },
          facingMode: 'user'
        }, 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      console.log('✅ Local stream obtained:', stream.getTracks().map(t => ({ kind: t.kind, enabled: t.enabled })));
      
      // Set local video first
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
        setLocalVideo(stream);
        localVideoRef.current.play().catch(e => console.warn('Local video play error:', e));
      }
      localStreamRef.current = stream;

      // Initialize peer connection AFTER getting stream
      console.log('🔗 Initializing peer connection...');
      const peerConnection = initializePeerConnection();
      peerConnectionRef.current = peerConnection;

      // Add ALL tracks to peer connection
      console.log('➕ Adding tracks to peer connection...');
      stream.getTracks().forEach((track, index) => {
        console.log(`Adding track ${index + 1}:`, track.kind, track.enabled);
        peerConnection.addTrack(track, stream);
      });

      // Wait a bit for the peer connection to be ready
      await new Promise(resolve => setTimeout(resolve, 100));

      if (isCaller) {
        console.log('📞 Caller: Creating offer...');
        try {
          const offer = await peerConnection.createOffer({
            offerToReceiveAudio: true,
            offerToReceiveVideo: true
          });
          
          console.log('📄 Offer created:', offer.type, offer.sdp?.length, 'chars');
          await peerConnection.setLocalDescription(offer);
          console.log('✅ Local description set (caller)');
          
          // Send offer via WebSocket
          console.log('📤 Sending offer via WebSocket');
          websocketRef.current.send(JSON.stringify({
            type: 'offer',
            sdp: offer,
            target: currentCall.other_user_id
          }));
        } catch (error) {
          console.error('❌ Error creating/sending offer:', error);
          throw error;
        }
      }
    } catch (error) {
      console.error('❌ Error starting call:', error);
      alert('Não foi possível acessar câmera/microfone: ' + error.message);
    }
  };

  const handleOffer = async (offer, from) => {
    console.log('📨 Handling offer from:', from);
    console.log('📄 Offer received:', offer.type, offer.sdp?.length, 'chars');
    
    try {
      // Initialize peer connection first
      console.log('🔗 Initializing peer connection for callee...');
      const peerConnection = initializePeerConnection();
      peerConnectionRef.current = peerConnection;

      // Get user media
      console.log('📹 Getting callee user media...');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 }, 
          height: { ideal: 480 },
          facingMode: 'user'
        }, 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      console.log('✅ Callee local stream obtained:', stream.getTracks().map(t => ({ kind: t.kind, enabled: t.enabled })));
      
      // Set local video
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
        setLocalVideo(stream);
        localVideoRef.current.play().catch(e => console.warn('Callee local video play error:', e));
      }
      localStreamRef.current = stream;

      // Add tracks to peer connection BEFORE setting remote description
      console.log('➕ Adding callee tracks to peer connection...');
      stream.getTracks().forEach((track, index) => {
        console.log(`Adding callee track ${index + 1}:`, track.kind, track.enabled);
        peerConnection.addTrack(track, stream);
      });

      // Set remote description (offer)
      console.log('📥 Setting remote description (offer)...');
      await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
      console.log('✅ Remote description set (callee)');
      
      // Create answer
      console.log('📞 Creating answer...');
      const answer = await peerConnection.createAnswer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: true
      });
      
      console.log('📄 Answer created:', answer.type, answer.sdp?.length, 'chars');
      await peerConnection.setLocalDescription(answer);
      console.log('✅ Local description set (callee)');

      // Send answer via WebSocket
      console.log('📤 Sending answer via WebSocket');
      websocketRef.current.send(JSON.stringify({
        type: 'answer',
        sdp: answer,
        target: from
      }));

      // Update call state
      setCurrentCall({ other_user_id: from, call_id: incomingCall.call_id });
      console.log('✅ Call state updated for callee');
    } catch (error) {
      console.error('❌ Error handling offer:', error);
      alert('Erro ao processar chamada: ' + error.message);
    }
  };

  const handleAnswer = async (answer) => {
    console.log('📨 Handling answer...');
    console.log('📄 Answer received:', answer.type, answer.sdp?.length, 'chars');
    
    if (peerConnectionRef.current) {
      try {
        console.log('📥 Setting remote description (answer)...');
        await peerConnectionRef.current.setRemoteDescription(new RTCSessionDescription(answer));
        console.log('✅ Remote description set successfully (caller)');
        
        // Check connection state after setting answer
        console.log('📊 Connection state after answer:', peerConnectionRef.current.connectionState);
        console.log('📊 ICE connection state after answer:', peerConnectionRef.current.iceConnectionState);
        
      } catch (error) {
        console.error('❌ Error setting remote description (answer):', error);
        // Try to recover by restarting ICE
        try {
          peerConnectionRef.current.restartIce();
        } catch (restartError) {
          console.error('❌ Failed to restart ICE:', restartError);
        }
      }
    } else {
      console.error('❌ No peer connection available to handle answer');
    }
  };

  const handleIceCandidate = async (candidate) => {
    console.log('🧊 Handling ICE candidate:', candidate);
    
    if (peerConnectionRef.current && peerConnectionRef.current.remoteDescription) {
      try {
        await peerConnectionRef.current.addIceCandidate(new RTCIceCandidate(candidate));
        console.log('✅ ICE candidate added successfully');
      } catch (error) {
        console.error('❌ Error adding ICE candidate:', error);
        // This is often not critical, so we continue
      }
    } else {
      console.warn('⚠️ Cannot add ICE candidate: no peer connection or remote description not set yet');
      // Could queue the candidate for later, but usually handled by browser
    }
  };

  const initiateCall = async (professionalId) => {
    try {
      // Request media permissions before initiating call
      const hasPermissions = await requestMediaPermissions();
      if (!hasPermissions) {
        return;
      }

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
      console.log('🟢 Accepting call:', incomingCall.call_id);
      
      // Request permissions before accepting
      const hasPermissions = await requestMediaPermissions();
      if (!hasPermissions) {
        return;
      }
      
      // Accept via API first
      await apiCall(`/api/call/${incomingCall.call_id}/accept`, {
        method: 'POST',
      });
      
      console.log('✅ Call accepted via API, starting WebRTC as callee...');
      
      // Set call state
      setCurrentCall({ 
        call_id: incomingCall.call_id, 
        other_user_id: incomingCall.caller.id 
      });
      setIncomingCall(null);
      
      // Wait for offer to arrive via WebSocket - handled by handleOffer
      console.log('⏳ Waiting for offer from caller...');
      
    } catch (error) {
      console.error('❌ Failed to accept call:', error);
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
    setChatMinimized(true); // Reset chat to minimized state
    
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }
    if (remoteVideoRef.current) {
      remoteVideoRef.current.srcObject = null;
    }
  };

  const sendChatMessage = () => {
    if (chatInput.trim() && websocketRef.current && currentCall) {
      console.log('Sending chat message:', chatInput);
      console.log('Current call:', currentCall);
      console.log('WebSocket state:', websocketRef.current.readyState);
      
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
    } else {
      console.log('Cannot send message:', {
        chatInput: chatInput.trim(),
        websocket: !!websocketRef.current,
        currentCall: !!currentCall
      });
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
      if (!allowedTypes.includes(file.type)) {
        alert('Apenas imagens (JPEG, PNG, GIF) e arquivos PDF são permitidos.');
        return;
      }

      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        alert('Arquivo muito grande. Tamanho máximo: 5MB.');
        return;
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        const fileData = {
          name: file.name,
          type: file.type,
          size: file.size,
          data: event.target.result
        };

        if (websocketRef.current && currentCall) {
          websocketRef.current.send(JSON.stringify({
            type: 'file_message',
            file: fileData,
            target: currentCall.other_user_id
          }));

          setChatMessages(prev => [...prev, {
            from: user.id,
            file: fileData,
            timestamp: new Date().toISOString()
          }]);
        }
      };
      
      reader.readAsDataURL(file);
      e.target.value = ''; // Reset file input
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
                <input
                  type="text"
                  placeholder="Nome completo"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                />
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
          {user.professional_mode && <span className="pro-badge">👨‍⚕️ Profissional</span>}
          <span className="token-balance">💰 {user.token_balance} tokens</span>
          <button onClick={() => setShowSettings(true)} className="settings-btn">⚙️</button>
          <button onClick={handleLogout} className="logout-btn">Sair</button>
        </div>
      </header>

      {/* Settings Modal */}
      {showSettings && (
        <div className="settings-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h2>⚙️ Configurações do Perfil</h2>
              <button onClick={() => setShowSettings(false)} className="close-btn">✕</button>
            </div>
            
            <form onSubmit={updateSettings} className="settings-form">
              <div className="form-group">
                <label>Nome:</label>
                <input
                  type="text"
                  value={settingsData.name}
                  onChange={(e) => setSettingsData({...settingsData, name: e.target.value})}
                  placeholder="Seu nome completo"
                />
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={settingsData.professional_mode}
                    onChange={(e) => setSettingsData({...settingsData, professional_mode: e.target.checked})}
                  />
                  Ativar modo profissional
                </label>
              </div>

              {settingsData.professional_mode && (
                <>
                  <div className="form-group">
                    <label>Categoria:</label>
                    <select
                      value={settingsData.category}
                      onChange={(e) => setSettingsData({...settingsData, category: e.target.value})}
                    >
                      <option value="Médico">👨‍⚕️ Médico</option>
                      <option value="Psicólogo">🧠 Psicólogo</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Preço por minuto (tokens):</label>
                    <input
                      type="number"
                      value={settingsData.price_per_minute}
                      onChange={(e) => setSettingsData({...settingsData, price_per_minute: parseInt(e.target.value) || 1})}
                      min="1"
                      max="100"
                    />
                  </div>

                  <div className="form-group">
                    <label>Descrição Profissional:</label>
                    <textarea
                      value={settingsData.description}
                      onChange={(e) => setSettingsData({...settingsData, description: e.target.value})}
                      placeholder="Descreva sua experiência e especialidades..."
                      rows={3}
                      maxLength={300}
                    />
                    <small>{settingsData.description.length}/300 caracteres</small>
                  </div>

                  <div className="form-group">
                    <label>Foto de Perfil (URL):</label>
                    <input
                      type="url"
                      value={settingsData.profile_photo}
                      onChange={(e) => setSettingsData({...settingsData, profile_photo: e.target.value})}
                      placeholder="https://exemplo.com/sua-foto.jpg"
                    />
                    {settingsData.profile_photo && (
                      <div className="photo-preview">
                        <img 
                          src={settingsData.profile_photo} 
                          alt="Preview" 
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      </div>
                    )}
                  </div>
                </>
              )}

              {availableDevices.cameras.length > 0 || availableDevices.microphones.length > 0 ? (
                <div className="form-group">
                  <label>Dispositivos Detectados:</label>
                  <div className="device-list">
                    {availableDevices.cameras.length > 0 && (
                      <p>📹 Câmeras: {availableDevices.cameras.length}</p>
                    )}
                    {availableDevices.microphones.length > 0 && (
                      <p>🎤 Microfones: {availableDevices.microphones.length}</p>
                    )}
                  </div>
                </div>
              ) : null}

              <div className="modal-actions">
                <button type="button" onClick={() => setShowSettings(false)} className="cancel-btn">
                  Cancelar
                </button>
                <button type="submit" disabled={loading} className="save-btn">
                  {loading ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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

          <div className={`chat-container ${chatMinimized ? 'minimized' : 'expanded'}`}>
            <div className="chat-header">
              <span>💬 Chat</span>
              <button 
                className="chat-toggle"
                onClick={() => setChatMinimized(!chatMinimized)}
              >
                {chatMinimized ? '▲' : '▼'}
              </button>
            </div>
            
            {!chatMinimized && (
              <>
                <div className="chat-messages">
                  {chatMessages.map((msg, index) => (
                    <div key={index} className={`chat-message ${msg.from === user.id ? 'own' : 'other'}`}>
                      {msg.message && (
                        <>
                          <div className="message-content">{msg.message}</div>
                          <div className="message-time">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </div>
                        </>
                      )}
                      {msg.file && (
                        <>
                          <div className="file-message">
                            {msg.file.type.startsWith('image/') ? (
                              <img 
                                src={msg.file.data} 
                                alt={msg.file.name}
                                className="chat-image"
                                onClick={() => window.open(msg.file.data, '_blank')}
                              />
                            ) : (
                              <a 
                                href={msg.file.data} 
                                download={msg.file.name}
                                className="chat-file-link"
                              >
                                📄 {msg.file.name}
                              </a>
                            )}
                          </div>
                          <div className="message-time">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
                <div className="chat-input-container">
                  <div className="chat-input">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Digite uma mensagem..."
                      onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
                    />
                    <input
                      type="file"
                      id="fileUpload"
                      accept="image/*,.pdf"
                      onChange={handleFileUpload}
                      style={{ display: 'none' }}
                    />
                    <button 
                      onClick={() => document.getElementById('fileUpload').click()}
                      className="file-upload-btn"
                      title="Enviar imagem ou PDF"
                    >
                      📎
                    </button>
                    <button onClick={sendChatMessage}>Enviar</button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="main-content">
          {user.professional_mode ? (
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
                <p><strong>Categoria:</strong> {user.category || 'Não definida'}</p>
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
              
              {!user.professional_mode && (
                <div className="become-professional">
                  <p>💡 Você também pode ser um profissional! Clique em ⚙️ nas configurações para ativar.</p>
                </div>
              )}
              
              {professionals.length === 0 ? (
                <p>Nenhum profissional online no momento.</p>
              ) : (
                <div className="professionals-grid">
                  {professionals.map(prof => (
                    <div key={prof.id} className="professional-card">
                      <div className="prof-photo">
                        {prof.profile_photo ? (
                          <img 
                            src={prof.profile_photo} 
                            alt={prof.name}
                            onError={(e) => {
                              e.target.src = '/api/placeholder/150/150?text=' + encodeURIComponent(prof.name.split(' ').map(n => n[0]).join(''));
                            }}
                          />
                        ) : (
                          <div className="photo-placeholder">
                            {prof.name.split(' ').map(n => n[0]).join('').toUpperCase()}
                          </div>
                        )}
                      </div>
                      <div className="prof-info">
                        <div className="prof-header">
                          <h3>{prof.name}</h3>
                          <span className={`status-badge status-${prof.status}`}>
                            {prof.status === 'online' ? '🟢 Disponível' : '🟡 Ocupado'}
                          </span>
                        </div>
                        <p><strong>Categoria:</strong> {prof.category === 'Médico' ? '👨‍⚕️ Médico' : '🧠 Psicólogo'}</p>
                        <p><strong>Preço:</strong> {prof.price_per_minute} tokens/min</p>
                        {prof.description && (
                          <p className="prof-description">
                            <strong>Descrição:</strong> {prof.description}
                          </p>
                        )}
                        <button
                          onClick={() => initiateCall(prof.id)}
                          disabled={prof.status !== 'online'}
                          className="call-btn"
                        >
                          {prof.status === 'online' ? '📞 Chamar' : '🔴 Ocupado'}
                        </button>
                      </div>
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