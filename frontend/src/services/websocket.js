let socket = null;
let reconnectAttempts = 0;
let reconnectTimeout = null;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;

let messageHandlers = {
  onMessage: null,
  onConnect: null,
  onDisconnect: null
};

const reconnect = () => {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.error('Max reconnection attempts reached');
    if (messageHandlers.onMessage) {
      messageHandlers.onMessage({
        type: 'error',
        message: 'Unable to connect to server. Please check your connection.'
      });
    }
    return;
  }
  
  reconnectAttempts++;
  console.log(`Reconnection attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);
  
  reconnectTimeout = setTimeout(() => {
    connectWebSocket(
      messageHandlers.onMessage, 
      messageHandlers.onConnect, 
      messageHandlers.onDisconnect
    );
  }, RECONNECT_DELAY);
};

export const connectWebSocket = (onMessage, onConnect, onDisconnect) => {
  // Check if already connected
  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log('WebSocket already connected, skipping new connection');
    return socket;
  }
  
  messageHandlers = { onMessage, onConnect, onDisconnect };
  
  const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws/stream';
  console.log(`[WebSocket] Attempting to connect to ${wsUrl}`);
  
  try {
    socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
      console.log('[WebSocket] Connection opened successfully');
      reconnectAttempts = 0;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }
      if (onConnect) onConnect();
    };
    
    socket.onclose = (event) => {
      console.log(`[WebSocket] Connection closed - Code: ${event.code}, Reason: ${event.reason}, Clean: ${event.wasClean}`);
      if (onDisconnect) onDisconnect();
      
      if (!event.wasClean && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        console.log('[WebSocket] Unclean close, attempting reconnect...');
        reconnect();
      }
    };
    
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WebSocket] Message received:', data.type, data);
        
        if (data.type === 'progress' || data.type === 'node_output') {
          // Convert backend message format to frontend expected format
          const convertedData = {
            type: 'agent_update',
            agent: data.current_agent || data.metadata?.agent || 'unknown',
            progress: data.progress || 0,
            message: data.message || '',
            data: data.data || data,
            status: data.type === 'complete' ? 'completed' : 'processing'
          };
          if (onMessage) onMessage(convertedData);
        } else if (data.type === 'acknowledgment') {
          // Handle acknowledgment messages
          if (onMessage) onMessage({
            type: 'agent_update',
            agent: 'supervisor',
            message: data.message || 'Processing your request...',
            progress: 0,
            status: 'processing'
          });
        } else if (data.type === 'error') {
          if (onMessage) onMessage(data);
        } else if (data.type === 'complete') {
          if (onMessage) onMessage(data);
        } else {
          if (onMessage) onMessage(data);
        }
      } catch (error) {
        console.error('Error parsing message:', error);
        if (onMessage) {
          onMessage({
            type: 'error',
            message: 'Error parsing server message'
          });
        }
      }
    };
    
    socket.onerror = (error) => {
      console.error('[WebSocket] Error occurred:', error);
      if (onMessage) {
        onMessage({
          type: 'error',
          message: 'WebSocket connection error'
        });
      }
    };
    
  } catch (error) {
    console.error('[WebSocket] Failed to create WebSocket:', error);
    reconnect();
  }
  
  return socket;
};

export const sendMessage = (data) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    const message = {
      type: 'invoke',
      input: data.message || data.input || '',
      thread_id: data.thread_id || null
    };
    socket.send(JSON.stringify(message));
    console.log('[WebSocket] Sent message:', message);
  } else {
    console.error(`[WebSocket] Cannot send message - Socket state: ${socket ? socket.readyState : 'null'}`);
  }
};

export const disconnectWebSocket = () => {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
  
  if (socket) {
    socket.close();
    socket = null;
  }
};

export const isConnected = () => {
  return socket && socket.readyState === WebSocket.OPEN;
};

export default {
  connectWebSocket,
  sendMessage,
  disconnectWebSocket,
  isConnected
};