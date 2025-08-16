"""
Real-time Feedback Service with WebSocket communication
"""
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.services.body_language_service import BodyLanguageAnalyzer
from app.services.audio_analysis_service import ToneAnalyzer
from app.db.models import InterviewSession, User

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time feedback"""
    
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}  # session_id -> websocket
        self.session_analyzers: Dict[int, Dict[str, Any]] = {}  # session_id -> analyzers
    
    async def connect(self, websocket: WebSocket, session_id: int):
        """Accept WebSocket connection and initialize analyzers"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Initialize analyzers for this session
        self.session_analyzers[session_id] = {
            'body_language': BodyLanguageAnalyzer(),
            'audio': ToneAnalyzer(),
            'last_feedback_time': datetime.utcnow(),
            'feedback_interval': 5  # seconds
        }
        
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: int):
        """Remove connection and cleanup analyzers"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        if session_id in self.session_analyzers:
            del self.session_analyzers[session_id]
        
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_personal_message(self, message: dict, session_id: int):
        """Send message to specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to session {session_id}: {e}")
                self.disconnect(session_id)
    
    async def broadcast_to_session(self, message: dict, session_id: int):
        """Broadcast message to session (same as send_personal_message for now)"""
        await self.send_personal_message(message, session_id)


class RealTimeFeedbackService:
    """Service for processing real-time feedback during interviews"""
    
    def __init__(self, db: Session):
        self.db = db
        self.connection_manager = ConnectionManager()
    
    async def handle_websocket_connection(self, websocket: WebSocket, session_id: int, user_id: int):
        """Handle WebSocket connection for real-time feedback"""
        # Verify session ownership
        session = self.db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            await websocket.close(code=4004, reason="Session not found or access denied")
            return
        
        await self.connection_manager.connect(websocket, session_id)
        
        try:
            while True:
                # Receive data from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Process different message types
                await self._process_message(message, session_id, user_id)
                
        except WebSocketDisconnect:
            self.connection_manager.disconnect(session_id)
        except Exception as e:
            logger.error(f"WebSocket error for session {session_id}: {e}")
            self.connection_manager.disconnect(session_id)
    
    async def _process_message(self, message: Dict[str, Any], session_id: int, user_id: int):
        """Process incoming WebSocket message"""
        message_type = message.get('type')
        
        if message_type == 'video_frame':
            await self._process_video_frame(message, session_id)
        elif message_type == 'audio_chunk':
            await self._process_audio_chunk(message, session_id)
        elif message_type == 'ping':
            await self._send_pong(session_id)
        elif message_type == 'request_feedback':
            await self._send_current_feedback(session_id)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _process_video_frame(self, message: Dict[str, Any], session_id: int):
        """Process video frame for body language analysis"""
        try:
            frame_data = message.get('frame_data')
            if not frame_data:
                return
            
            analyzers = self.connection_manager.session_analyzers.get(session_id)
            if not analyzers:
                return
            
            # Analyze body language
            body_language_analyzer = analyzers['body_language']
            analysis_result = body_language_analyzer.analyze_frame(frame_data)
            
            # Send real-time feedback if enough time has passed
            await self._maybe_send_feedback(session_id, 'body_language', analysis_result)
            
        except Exception as e:
            logger.error(f"Error processing video frame for session {session_id}: {e}")
    
    async def _process_audio_chunk(self, message: Dict[str, Any], session_id: int):
        """Process audio chunk for tone analysis"""
        try:
            audio_data = message.get('audio_data')
            if not audio_data:
                return
            
            analyzers = self.connection_manager.session_analyzers.get(session_id)
            if not analyzers:
                return
            
            # Analyze audio
            audio_analyzer = analyzers['audio']
            analysis_result = audio_analyzer.analyze_audio_chunk(audio_data)
            
            # Send real-time feedback if enough time has passed
            await self._maybe_send_feedback(session_id, 'audio', analysis_result)
            
        except Exception as e:
            logger.error(f"Error processing audio chunk for session {session_id}: {e}")
    
    async def _maybe_send_feedback(self, session_id: int, analysis_type: str, result: Dict[str, Any]):
        """Send feedback if enough time has passed since last feedback"""
        analyzers = self.connection_manager.session_analyzers.get(session_id)
        if not analyzers:
            return
        
        current_time = datetime.utcnow()
        last_feedback_time = analyzers['last_feedback_time']
        feedback_interval = analyzers['feedback_interval']
        
        # Check if enough time has passed
        if (current_time - last_feedback_time).total_seconds() >= feedback_interval:
            await self._send_realtime_feedback(session_id, analysis_type, result)
            analyzers['last_feedback_time'] = current_time
    
    async def _send_realtime_feedback(self, session_id: int, analysis_type: str, result: Dict[str, Any]):
        """Send real-time feedback to client"""
        feedback_message = {
            'type': 'realtime_feedback',
            'analysis_type': analysis_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': result
        }
        
        await self.connection_manager.send_personal_message(feedback_message, session_id)
    
    async def _send_pong(self, session_id: int):
        """Send pong response to ping"""
        pong_message = {
            'type': 'pong',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.send_personal_message(pong_message, session_id)
    
    async def _send_current_feedback(self, session_id: int):
        """Send current feedback summary"""
        analyzers = self.connection_manager.session_analyzers.get(session_id)
        if not analyzers:
            return
        
        # Get current analysis state
        body_language_analyzer = analyzers['body_language']
        audio_analyzer = analyzers['audio']
        
        # Generate summary feedback
        summary = {
            'type': 'feedback_summary',
            'timestamp': datetime.utcnow().isoformat(),
            'body_language_report': body_language_analyzer.get_session_report(str(session_id)),
            'audio_report': audio_analyzer.get_session_audio_report(str(session_id))
        }
        
        await self.connection_manager.send_personal_message(summary, session_id)
    
    async def send_session_update(self, session_id: int, update_type: str, data: Dict[str, Any]):
        """Send session update to client"""
        update_message = {
            'type': 'session_update',
            'update_type': update_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        await self.connection_manager.send_personal_message(update_message, session_id)
    
    async def send_question_change(self, session_id: int, question_data: Dict[str, Any]):
        """Send question change notification"""
        question_message = {
            'type': 'question_change',
            'timestamp': datetime.utcnow().isoformat(),
            'question': question_data
        }
        
        await self.connection_manager.send_personal_message(question_message, session_id)
    
    async def send_session_complete(self, session_id: int, summary_data: Dict[str, Any]):
        """Send session completion notification"""
        completion_message = {
            'type': 'session_complete',
            'timestamp': datetime.utcnow().isoformat(),
            'summary': summary_data
        }
        
        await self.connection_manager.send_personal_message(completion_message, session_id)
    
    def get_active_sessions(self) -> List[int]:
        """Get list of active session IDs"""
        return list(self.connection_manager.active_connections.keys())
    
    def is_session_active(self, session_id: int) -> bool:
        """Check if session has active WebSocket connection"""
        return session_id in self.connection_manager.active_connections
    
    async def cleanup_session(self, session_id: int):
        """Cleanup session resources"""
        if session_id in self.connection_manager.session_analyzers:
            # Get final reports before cleanup
            analyzers = self.connection_manager.session_analyzers[session_id]
            
            body_language_report = analyzers['body_language'].get_session_report(str(session_id))
            audio_report = analyzers['audio'].get_session_audio_report(str(session_id))
            
            # Send final summary
            final_summary = {
                'type': 'final_analysis',
                'timestamp': datetime.utcnow().isoformat(),
                'body_language_report': body_language_report,
                'audio_report': audio_report
            }
            
            await self.connection_manager.send_personal_message(final_summary, session_id)
        
        # Disconnect and cleanup
        self.connection_manager.disconnect(session_id)


# Global connection manager instance
connection_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, session_id: int, db: Session, user_id: int):
    """WebSocket endpoint for real-time feedback"""
    feedback_service = RealTimeFeedbackService(db)
    await feedback_service.handle_websocket_connection(websocket, session_id, user_id)