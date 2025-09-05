"""
Difficulty State Validation and Diagnostics Service

This service provides comprehensive validation methods, diagnostic endpoints,
and health checks for difficulty state integrity across the system.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from enum import Enum

from app.db.models import InterviewSession, User
from app.services.session_difficulty_state import SessionDifficultyState, DifficultyChange
from app.services.session_specific_difficulty_service import SessionSpecificDifficultyService
from app.services.difficulty_state_recovery_service import DifficultyStateRecoveryService
from app.services.difficulty_mapping_service import DifficultyMappingService

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class DifficultyValidationService:
    """
    Service for difficulty state validation and diagnostics
    
    This service provides comprehensive validation methods to check difficulty state consistency,
    diagnostic endpoints for troubleshooting, and health checks for system integrity.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the difficulty validation service
        
        Args:
            db: Database session for validation operations
        """
        self.db = db
        self.session_difficulty_service = SessionSpecificDifficultyService(db)
        self.recovery_service = DifficultyStateRecoveryService(db)
        self.difficulty_mapping = DifficultyMappingService
        
        # Validation thresholds
        self.validation_thresholds = {
            "max_error_rate": 0.05,  # 5% error rate threshold
            "max_recovery_failures": 10,
            "max_state_corruption_rate": 0.02,  # 2% corruption rate
            "max_cache_inconsistency_rate": 0.03,  # 3% cache inconsistency
            "session_timeout_hours": 24,
            "max_orphaned_sessions": 50
        }
        
        logger.info("DifficultyValidationService initialized")
    
    def validate_difficulty_state_consistency(
        self, 
        session_id: Optional[int] = None,
        user_id: Optional[int] = None,
        include_cache_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Validate difficulty state consistency across the system
        
        Args:
            session_id: Optional specific session to validate
            user_id: Optional specific user to validate
            include_cache_validation: Whether to include cache consistency checks
            
        Returns:
            Dict containing comprehensive validation results
        """
        try:
            logger.info(f"Starting difficulty state validation - Session: {session_id}, User: {user_id}")
            
            validation_result = {
                "validation_id": f"validation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat(),
                "scope": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "include_cache": include_cache_validation
                },
                "overall_status": HealthStatus.HEALTHY.value,
                "summary": {
                    "total_sessions_checked": 0,
                    "sessions_with_issues": 0,
                    "critical_issues": 0,
                    "warnings": 0,
                    "info_items": 0
                },
                "detailed_results": {
                    "database_consistency": {},
                    "cache_consistency": {},
                    "state_integrity": {},
                    "inheritance_validation": {},
                    "isolation_validation": {}
                },
                "issues_found": [],
                "recommendations": []
            }
            
            # Get sessions to validate
            sessions = self._get_sessions_for_validation(session_id, user_id)
            validation_result["summary"]["total_sessions_checked"] = len(sessions)
            
            if not sessions:
                validation_result["issues_found"].append({
                    "severity": ValidationSeverity.INFO.value,
                    "category": "scope",
                    "message": "No sessions found for validation",
                    "details": {}
                })
                return validation_result
            
            # Validate database consistency
            db_validation = self._validate_database_consistency(sessions)
            validation_result["detailed_results"]["database_consistency"] = db_validation
            self._merge_validation_issues(validation_result, db_validation)
            
            # Validate cache consistency if requested
            if include_cache_validation:
                cache_validation = self._validate_cache_consistency(sessions)
                validation_result["detailed_results"]["cache_consistency"] = cache_validation
                self._merge_validation_issues(validation_result, cache_validation)
            
            # Validate state integrity
            state_validation = self._validate_state_integrity(sessions)
            validation_result["detailed_results"]["state_integrity"] = state_validation
            self._merge_validation_issues(validation_result, state_validation)
            
            # Validate practice session inheritance
            inheritance_validation = self._validate_inheritance_consistency(sessions)
            validation_result["detailed_results"]["inheritance_validation"] = inheritance_validation
            self._merge_validation_issues(validation_result, inheritance_validation)
            
            # Validate session isolation
            isolation_validation = self._validate_session_isolation(sessions)
            validation_result["detailed_results"]["isolation_validation"] = isolation_validation
            self._merge_validation_issues(validation_result, isolation_validation)
            
            # Determine overall status and generate recommendations
            validation_result["overall_status"] = self._determine_overall_health_status(validation_result)
            validation_result["recommendations"] = self._generate_recommendations(validation_result)
            
            logger.info(f"Validation complete - Status: {validation_result['overall_status']}, "
                       f"Issues: {validation_result['summary']['sessions_with_issues']}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during difficulty state validation: {str(e)}")
            return self._create_validation_error_response(e, session_id, user_id)
    
    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of the difficulty state system
        
        Returns:
            Dict containing health check results and system status
        """
        try:
            logger.info("Starting difficulty state system health check")
            
            health_check = {
                "check_id": f"health_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": HealthStatus.HEALTHY.value,
                "components": {
                    "database_health": {},
                    "cache_health": {},
                    "service_health": {},
                    "data_integrity": {},
                    "performance_metrics": {}
                },
                "alerts": [],
                "recommendations": [],
                "metrics": {}
            }
            
            # Check database health
            db_health = self._check_database_health()
            health_check["components"]["database_health"] = db_health
            
            # Check cache health
            cache_health = self._check_cache_health()
            health_check["components"]["cache_health"] = cache_health
            
            # Check service health
            service_health = self._check_service_health()
            health_check["components"]["service_health"] = service_health
            
            # Check data integrity
            integrity_check = self._check_data_integrity()
            health_check["components"]["data_integrity"] = integrity_check
            
            # Check performance metrics
            performance_metrics = self._check_performance_metrics()
            health_check["components"]["performance_metrics"] = performance_metrics
            
            # Aggregate alerts and determine overall status
            all_components = [db_health, cache_health, service_health, integrity_check, performance_metrics]
            health_check["overall_status"] = self._determine_overall_health_from_components(all_components)
            
            # Generate alerts and recommendations
            health_check["alerts"] = self._generate_health_alerts(all_components)
            health_check["recommendations"] = self._generate_health_recommendations(health_check)
            
            # Calculate key metrics
            health_check["metrics"] = self._calculate_health_metrics()
            
            logger.info(f"Health check complete - Overall status: {health_check['overall_status']}")
            return health_check
            
        except Exception as e:
            logger.error(f"Error during health check: {str(e)}")
            return self._create_health_check_error_response(e)
    
    def diagnose_session_issues(self, session_id: int) -> Dict[str, Any]:
        """
        Perform comprehensive diagnosis of issues for a specific session
        
        Args:
            session_id: The ID of the session to diagnose
            
        Returns:
            Dict containing detailed diagnostic information
        """
        try:
            logger.info(f"Starting diagnostic analysis for session {session_id}")
            
            diagnostic_result = {
                "session_id": session_id,
                "diagnosis_id": f"diag_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat(),
                "session_found": False,
                "session_info": {},
                "issues_detected": [],
                "state_analysis": {},
                "cache_analysis": {},
                "database_analysis": {},
                "recovery_options": [],
                "recommended_actions": []
            }
            
            # Get session information
            session = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if not session:
                diagnostic_result["issues_detected"].append({
                    "severity": ValidationSeverity.CRITICAL.value,
                    "category": "session_existence",
                    "message": f"Session {session_id} not found in database",
                    "impact": "Session cannot be accessed or recovered"
                })
                return diagnostic_result
            
            diagnostic_result["session_found"] = True
            diagnostic_result["session_info"] = self._extract_session_info(session)
            
            # Analyze difficulty state
            state_analysis = self._analyze_session_difficulty_state(session)
            diagnostic_result["state_analysis"] = state_analysis
            diagnostic_result["issues_detected"].extend(state_analysis.get("issues", []))
            
            # Analyze cache state
            cache_analysis = self._analyze_session_cache_state(session_id)
            diagnostic_result["cache_analysis"] = cache_analysis
            diagnostic_result["issues_detected"].extend(cache_analysis.get("issues", []))
            
            # Analyze database state
            db_analysis = self._analyze_session_database_state(session)
            diagnostic_result["database_analysis"] = db_analysis
            diagnostic_result["issues_detected"].extend(db_analysis.get("issues", []))
            
            # Generate recovery options
            diagnostic_result["recovery_options"] = self._generate_recovery_options(
                session, diagnostic_result["issues_detected"]
            )
            
            # Generate recommended actions
            diagnostic_result["recommended_actions"] = self._generate_diagnostic_recommendations(
                diagnostic_result
            )
            
            logger.info(f"Diagnostic complete for session {session_id} - "
                       f"Issues found: {len(diagnostic_result['issues_detected'])}")
            
            return diagnostic_result
            
        except Exception as e:
            logger.error(f"Error during session diagnosis for session {session_id}: {str(e)}")
            return self._create_diagnostic_error_response(e, session_id)
    
    def reset_difficulty_state(
        self, 
        session_id: Optional[int] = None,
        user_id: Optional[int] = None,
        reset_type: str = "soft"
    ) -> Dict[str, Any]:
        """
        Reset difficulty state for sessions when needed
        
        Args:
            session_id: Optional specific session to reset
            user_id: Optional specific user's sessions to reset
            reset_type: Type of reset ("soft", "hard", "cache_only")
            
        Returns:
            Dict containing reset operation results
        """
        try:
            logger.info(f"Starting difficulty state reset - Session: {session_id}, "
                       f"User: {user_id}, Type: {reset_type}")
            
            reset_result = {
                "reset_id": f"reset_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat(),
                "reset_type": reset_type,
                "scope": {
                    "session_id": session_id,
                    "user_id": user_id
                },
                "sessions_processed": 0,
                "sessions_reset": 0,
                "sessions_failed": 0,
                "operations_performed": [],
                "errors_encountered": [],
                "success": False
            }
            
            # Get sessions to reset
            sessions = self._get_sessions_for_validation(session_id, user_id)
            reset_result["sessions_processed"] = len(sessions)
            
            if not sessions:
                reset_result["errors_encountered"].append("No sessions found to reset")
                return reset_result
            
            # Perform reset operations based on type
            for session in sessions:
                try:
                    session_reset_success = False
                    
                    if reset_type == "soft":
                        # Soft reset: clear cache, keep database data
                        session_reset_success = self._perform_soft_reset(session)
                        
                    elif reset_type == "hard":
                        # Hard reset: clear cache and reset database fields
                        session_reset_success = self._perform_hard_reset(session)
                        
                    elif reset_type == "cache_only":
                        # Cache-only reset: only clear cache
                        session_reset_success = self._perform_cache_only_reset(session)
                    
                    if session_reset_success:
                        reset_result["sessions_reset"] += 1
                        reset_result["operations_performed"].append(
                            f"Successfully reset session {session.id}"
                        )
                    else:
                        reset_result["sessions_failed"] += 1
                        reset_result["errors_encountered"].append(
                            f"Failed to reset session {session.id}"
                        )
                        
                except Exception as session_error:
                    reset_result["sessions_failed"] += 1
                    reset_result["errors_encountered"].append(
                        f"Error resetting session {session.id}: {str(session_error)}"
                    )
                    logger.error(f"Error resetting session {session.id}: {str(session_error)}")
            
            reset_result["success"] = reset_result["sessions_failed"] == 0
            
            logger.info(f"Reset operation complete - Success: {reset_result['success']}, "
                       f"Reset: {reset_result['sessions_reset']}, Failed: {reset_result['sessions_failed']}")
            
            return reset_result
            
        except Exception as e:
            logger.error(f"Error during difficulty state reset: {str(e)}")
            return {
                "reset_id": f"reset_error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat(),
                "success": False,
                "error": str(e),
                "sessions_processed": 0,
                "sessions_reset": 0,
                "sessions_failed": 0
            }
    
    def _get_sessions_for_validation(
        self, 
        session_id: Optional[int],
        user_id: Optional[int]
    ) -> List[InterviewSession]:
        """Get sessions for validation based on scope"""
        
        query = self.db.query(InterviewSession)
        
        if session_id:
            query = query.filter(InterviewSession.id == session_id)
        elif user_id:
            query = query.filter(InterviewSession.user_id == user_id)
        else:
            # Limit to recent sessions for system-wide validation
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            query = query.filter(InterviewSession.created_at >= cutoff_date)
        
        return query.order_by(InterviewSession.created_at.desc()).limit(1000).all()
    
    def _validate_database_consistency(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Validate database consistency for difficulty fields"""
        
        validation = {
            "status": HealthStatus.HEALTHY.value,
            "sessions_checked": len(sessions),
            "issues_found": 0,
            "issues": [],
            "statistics": {
                "missing_difficulty_level": 0,
                "inconsistent_fields": 0,
                "corrupted_json_state": 0,
                "missing_final_difficulty": 0
            }
        }
        
        for session in sessions:
            session_issues = []
            
            # Check for missing difficulty_level
            if not session.difficulty_level:
                session_issues.append({
                    "severity": ValidationSeverity.ERROR.value,
                    "category": "missing_data",
                    "message": f"Session {session.id} missing difficulty_level",
                    "session_id": session.id
                })
                validation["statistics"]["missing_difficulty_level"] += 1
            
            # Check field consistency
            if (session.current_difficulty_level and 
                session.difficulty_level and 
                session.current_difficulty_level != session.difficulty_level):
                session_issues.append({
                    "severity": ValidationSeverity.WARNING.value,
                    "category": "field_inconsistency",
                    "message": f"Session {session.id} has inconsistent difficulty fields",
                    "details": {
                        "difficulty_level": session.difficulty_level,
                        "current_difficulty_level": session.current_difficulty_level
                    },
                    "session_id": session.id
                })
                validation["statistics"]["inconsistent_fields"] += 1
            
            # Check JSON state integrity
            if session.difficulty_state_json:
                try:
                    json_state = session.difficulty_state_json
                    if not isinstance(json_state, dict) or "session_id" not in json_state:
                        session_issues.append({
                            "severity": ValidationSeverity.ERROR.value,
                            "category": "data_corruption",
                            "message": f"Session {session.id} has corrupted JSON state",
                            "session_id": session.id
                        })
                        validation["statistics"]["corrupted_json_state"] += 1
                except Exception:
                    session_issues.append({
                        "severity": ValidationSeverity.ERROR.value,
                        "category": "data_corruption",
                        "message": f"Session {session.id} has invalid JSON state",
                        "session_id": session.id
                    })
                    validation["statistics"]["corrupted_json_state"] += 1
            
            # Check completed sessions for final difficulty
            if (session.status == "completed" and 
                session.completed_at and 
                not session.final_difficulty_level):
                session_issues.append({
                    "severity": ValidationSeverity.WARNING.value,
                    "category": "missing_finalization",
                    "message": f"Completed session {session.id} missing final_difficulty_level",
                    "session_id": session.id
                })
                validation["statistics"]["missing_final_difficulty"] += 1
            
            if session_issues:
                validation["issues_found"] += 1
                validation["issues"].extend(session_issues)
        
        # Determine overall status
        if validation["statistics"]["corrupted_json_state"] > 0:
            validation["status"] = HealthStatus.UNHEALTHY.value
        elif validation["statistics"]["missing_difficulty_level"] > 0:
            validation["status"] = HealthStatus.DEGRADED.value
        elif validation["issues_found"] > 0:
            validation["status"] = HealthStatus.DEGRADED.value
        
        return validation
    
    def _validate_cache_consistency(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Validate cache consistency with database"""
        
        validation = {
            "status": HealthStatus.HEALTHY.value,
            "sessions_checked": len(sessions),
            "cache_hits": 0,
            "cache_misses": 0,
            "inconsistencies": 0,
            "issues": []
        }
        
        for session in sessions:
            try:
                # Check if session is in cache
                cached_state = self.session_difficulty_service.session_states.get(session.id)
                
                if cached_state:
                    validation["cache_hits"] += 1
                    
                    # Compare cache with database
                    if session.current_difficulty_level:
                        if cached_state.current_difficulty != session.current_difficulty_level:
                            validation["inconsistencies"] += 1
                            validation["issues"].append({
                                "severity": ValidationSeverity.WARNING.value,
                                "category": "cache_inconsistency",
                                "message": f"Session {session.id} cache/database difficulty mismatch",
                                "details": {
                                    "cache_difficulty": cached_state.current_difficulty,
                                    "database_difficulty": session.current_difficulty_level
                                },
                                "session_id": session.id
                            })
                else:
                    validation["cache_misses"] += 1
                    
            except Exception as e:
                validation["issues"].append({
                    "severity": ValidationSeverity.ERROR.value,
                    "category": "cache_error",
                    "message": f"Error checking cache for session {session.id}: {str(e)}",
                    "session_id": session.id
                })
        
        # Determine status
        inconsistency_rate = validation["inconsistencies"] / max(validation["sessions_checked"], 1)
        if inconsistency_rate > self.validation_thresholds["max_cache_inconsistency_rate"]:
            validation["status"] = HealthStatus.DEGRADED.value
        
        return validation
    
    def _validate_state_integrity(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Validate integrity of difficulty state objects"""
        
        validation = {
            "status": HealthStatus.HEALTHY.value,
            "sessions_checked": 0,
            "states_validated": 0,
            "validation_errors": 0,
            "issues": []
        }
        
        for session in sessions:
            try:
                # Try to load or create state
                state = self.session_difficulty_service.get_session_difficulty_state(session.id)
                
                if state:
                    validation["states_validated"] += 1
                    
                    # Validate state integrity
                    state_errors = state.validate_state()
                    if state_errors:
                        validation["validation_errors"] += 1
                        validation["issues"].append({
                            "severity": ValidationSeverity.ERROR.value,
                            "category": "state_validation",
                            "message": f"Session {session.id} state validation failed",
                            "details": {"validation_errors": state_errors},
                            "session_id": session.id
                        })
                
                validation["sessions_checked"] += 1
                
            except Exception as e:
                validation["issues"].append({
                    "severity": ValidationSeverity.ERROR.value,
                    "category": "state_loading",
                    "message": f"Error loading state for session {session.id}: {str(e)}",
                    "session_id": session.id
                })
        
        # Determine status
        error_rate = validation["validation_errors"] / max(validation["sessions_checked"], 1)
        if error_rate > self.validation_thresholds["max_error_rate"]:
            validation["status"] = HealthStatus.UNHEALTHY.value
        elif validation["validation_errors"] > 0:
            validation["status"] = HealthStatus.DEGRADED.value
        
        return validation
    
    def _validate_inheritance_consistency(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Validate practice session inheritance consistency"""
        
        validation = {
            "status": HealthStatus.HEALTHY.value,
            "practice_sessions_checked": 0,
            "inheritance_errors": 0,
            "issues": []
        }
        
        # Create session lookup
        session_map = {s.id: s for s in sessions}
        
        for session in sessions:
            if getattr(session, 'session_mode', None) == "practice_again" and session.parent_session_id:
                validation["practice_sessions_checked"] += 1
                
                parent = session_map.get(session.parent_session_id)
                if not parent:
                    # Try to get parent from database
                    parent = self.db.query(InterviewSession).filter(
                        InterviewSession.id == session.parent_session_id
                    ).first()
                
                if parent:
                    # Check inheritance consistency
                    parent_final = parent.final_difficulty_level or parent.difficulty_level
                    practice_initial = session.initial_difficulty_level or session.difficulty_level
                    
                    if parent_final and practice_initial and parent_final != practice_initial:
                        validation["inheritance_errors"] += 1
                        validation["issues"].append({
                            "severity": ValidationSeverity.ERROR.value,
                            "category": "inheritance_error",
                            "message": f"Practice session {session.id} inheritance mismatch",
                            "details": {
                                "parent_session_id": session.parent_session_id,
                                "parent_final_difficulty": parent_final,
                                "practice_initial_difficulty": practice_initial
                            },
                            "session_id": session.id
                        })
                else:
                    validation["inheritance_errors"] += 1
                    validation["issues"].append({
                        "severity": ValidationSeverity.ERROR.value,
                        "category": "orphaned_practice",
                        "message": f"Practice session {session.id} has missing parent {session.parent_session_id}",
                        "session_id": session.id
                    })
        
        # Determine status
        if validation["inheritance_errors"] > 0:
            validation["status"] = HealthStatus.DEGRADED.value
        
        return validation
    
    def _validate_session_isolation(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Validate that sessions maintain proper isolation"""
        
        validation = {
            "status": HealthStatus.HEALTHY.value,
            "sessions_checked": len(sessions),
            "isolation_violations": 0,
            "issues": []
        }
        
        # Group sessions by user
        user_sessions = {}
        for session in sessions:
            if session.user_id not in user_sessions:
                user_sessions[session.user_id] = []
            user_sessions[session.user_id].append(session)
        
        # Check isolation for each user
        for user_id, user_session_list in user_sessions.items():
            if len(user_session_list) > 1:
                # Check for cross-contamination indicators
                difficulties = [s.difficulty_level for s in user_session_list if s.difficulty_level]
                
                # Look for suspicious patterns that might indicate cross-contamination
                # This is a simplified check - in practice, you'd implement more sophisticated detection
                if len(set(difficulties)) == 1 and len(difficulties) > 3:
                    # All sessions have the same difficulty - might indicate contamination
                    validation["issues"].append({
                        "severity": ValidationSeverity.INFO.value,
                        "category": "potential_contamination",
                        "message": f"User {user_id} has {len(difficulties)} sessions with identical difficulty",
                        "details": {"difficulty": difficulties[0], "session_count": len(difficulties)},
                        "user_id": user_id
                    })
        
        return validation
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health for difficulty-related tables"""
        
        health = {
            "status": HealthStatus.HEALTHY.value,
            "checks_performed": [],
            "issues": [],
            "metrics": {}
        }
        
        try:
            # Check database connectivity
            self.db.execute(text("SELECT 1"))
            health["checks_performed"].append("database_connectivity")
            
            # Check table integrity
            session_count = self.db.query(func.count(InterviewSession.id)).scalar()
            health["metrics"]["total_sessions"] = session_count
            health["checks_performed"].append("table_access")
            
            # Check for recent activity
            recent_sessions = self.db.query(func.count(InterviewSession.id)).filter(
                InterviewSession.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).scalar()
            health["metrics"]["recent_sessions_24h"] = recent_sessions
            
            # Check for corrupted data
            corrupted_json_count = self.db.query(func.count(InterviewSession.id)).filter(
                and_(
                    InterviewSession.difficulty_state_json.isnot(None),
                    InterviewSession.difficulty_state_json == '{}'
                )
            ).scalar()
            health["metrics"]["corrupted_json_states"] = corrupted_json_count
            
            if corrupted_json_count > 0:
                health["issues"].append({
                    "severity": ValidationSeverity.WARNING.value,
                    "message": f"Found {corrupted_json_count} sessions with corrupted JSON state"
                })
            
        except Exception as e:
            health["status"] = HealthStatus.CRITICAL.value
            health["issues"].append({
                "severity": ValidationSeverity.CRITICAL.value,
                "message": f"Database health check failed: {str(e)}"
            })
        
        return health
    
    def _check_cache_health(self) -> Dict[str, Any]:
        """Check cache health and performance"""
        
        health = {
            "status": HealthStatus.HEALTHY.value,
            "checks_performed": [],
            "issues": [],
            "metrics": {}
        }
        
        try:
            # Check cache size
            cache_size = len(self.session_difficulty_service.session_states)
            health["metrics"]["cached_sessions"] = cache_size
            health["checks_performed"].append("cache_size_check")
            
            # Check for stale cache entries
            stale_entries = 0
            current_time = datetime.utcnow()
            
            for session_id, state in self.session_difficulty_service.session_states.items():
                if hasattr(state, 'last_updated'):
                    age = current_time - state.last_updated
                    if age > timedelta(hours=self.validation_thresholds["session_timeout_hours"]):
                        stale_entries += 1
            
            health["metrics"]["stale_cache_entries"] = stale_entries
            health["checks_performed"].append("stale_entry_check")
            
            if stale_entries > 10:
                health["status"] = HealthStatus.DEGRADED.value
                health["issues"].append({
                    "severity": ValidationSeverity.WARNING.value,
                    "message": f"Found {stale_entries} stale cache entries"
                })
            
        except Exception as e:
            health["status"] = HealthStatus.DEGRADED.value
            health["issues"].append({
                "severity": ValidationSeverity.ERROR.value,
                "message": f"Cache health check failed: {str(e)}"
            })
        
        return health
    
    def _check_service_health(self) -> Dict[str, Any]:
        """Check health of difficulty services"""
        
        health = {
            "status": HealthStatus.HEALTHY.value,
            "checks_performed": [],
            "issues": [],
            "services_checked": []
        }
        
        try:
            # Test session difficulty service
            test_state = SessionDifficultyState(999999, "medium")  # Use non-existent session ID
            if test_state.validate_state():
                health["services_checked"].append("SessionDifficultyState")
            
            # Test difficulty mapping service
            mapped_difficulty = self.difficulty_mapping.get_string_level("medium")
            if mapped_difficulty == "medium":
                health["services_checked"].append("DifficultyMappingService")
            
            health["checks_performed"].append("service_functionality")
            
        except Exception as e:
            health["status"] = HealthStatus.DEGRADED.value
            health["issues"].append({
                "severity": ValidationSeverity.ERROR.value,
                "message": f"Service health check failed: {str(e)}"
            })
        
        return health
    
    def _check_data_integrity(self) -> Dict[str, Any]:
        """Check overall data integrity"""
        
        integrity = {
            "status": HealthStatus.HEALTHY.value,
            "checks_performed": [],
            "issues": [],
            "metrics": {}
        }
        
        try:
            # Check for orphaned practice sessions
            orphaned_count = self.db.query(func.count(InterviewSession.id)).filter(
                and_(
                    InterviewSession.parent_session_id.isnot(None),
                    ~InterviewSession.parent_session_id.in_(
                        self.db.query(InterviewSession.id)
                    )
                )
            ).scalar()
            
            integrity["metrics"]["orphaned_practice_sessions"] = orphaned_count
            integrity["checks_performed"].append("orphaned_sessions_check")
            
            if orphaned_count > self.validation_thresholds["max_orphaned_sessions"]:
                integrity["status"] = HealthStatus.DEGRADED.value
                integrity["issues"].append({
                    "severity": ValidationSeverity.WARNING.value,
                    "message": f"Found {orphaned_count} orphaned practice sessions"
                })
            
            # Check for sessions without difficulty levels
            missing_difficulty_count = self.db.query(func.count(InterviewSession.id)).filter(
                InterviewSession.difficulty_level.is_(None)
            ).scalar()
            
            integrity["metrics"]["sessions_missing_difficulty"] = missing_difficulty_count
            integrity["checks_performed"].append("missing_difficulty_check")
            
            if missing_difficulty_count > 0:
                integrity["status"] = HealthStatus.DEGRADED.value
                integrity["issues"].append({
                    "severity": ValidationSeverity.WARNING.value,
                    "message": f"Found {missing_difficulty_count} sessions without difficulty level"
                })
            
        except Exception as e:
            integrity["status"] = HealthStatus.UNHEALTHY.value
            integrity["issues"].append({
                "severity": ValidationSeverity.ERROR.value,
                "message": f"Data integrity check failed: {str(e)}"
            })
        
        return integrity
    
    def _check_performance_metrics(self) -> Dict[str, Any]:
        """Check performance-related metrics"""
        
        performance = {
            "status": HealthStatus.HEALTHY.value,
            "checks_performed": [],
            "issues": [],
            "metrics": {}
        }
        
        try:
            # Measure database query performance
            import time
            start_time = time.time()
            
            recent_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.created_at >= datetime.utcnow() - timedelta(hours=1)
            ).limit(100).all()
            
            query_time = time.time() - start_time
            performance["metrics"]["db_query_time_ms"] = round(query_time * 1000, 2)
            performance["metrics"]["recent_sessions_sample"] = len(recent_sessions)
            performance["checks_performed"].append("database_performance")
            
            # Check if query time is acceptable
            if query_time > 2.0:  # 2 seconds threshold
                performance["status"] = HealthStatus.DEGRADED.value
                performance["issues"].append({
                    "severity": ValidationSeverity.WARNING.value,
                    "message": f"Database query took {query_time:.2f}s (threshold: 2.0s)"
                })
            
            # Test cache performance
            start_time = time.time()
            cache_operations = 0
            
            for session in recent_sessions[:10]:  # Test with first 10 sessions
                state = self.session_difficulty_service.session_states.get(session.id)
                cache_operations += 1
            
            cache_time = time.time() - start_time
            performance["metrics"]["cache_access_time_ms"] = round(cache_time * 1000, 2)
            performance["metrics"]["cache_operations_tested"] = cache_operations
            performance["checks_performed"].append("cache_performance")
            
        except Exception as e:
            performance["status"] = HealthStatus.DEGRADED.value
            performance["issues"].append({
                "severity": ValidationSeverity.ERROR.value,
                "message": f"Performance check failed: {str(e)}"
            })
        
        return performance
    
    def _merge_validation_issues(self, main_result: Dict[str, Any], component_result: Dict[str, Any]) -> None:
        """Merge issues from component validation into main result"""
        
        if "issues" in component_result:
            main_result["issues_found"].extend(component_result["issues"])
            
            # Count issues by severity
            for issue in component_result["issues"]:
                severity = issue.get("severity", ValidationSeverity.INFO.value)
                if severity == ValidationSeverity.CRITICAL.value:
                    main_result["summary"]["critical_issues"] += 1
                elif severity == ValidationSeverity.ERROR.value:
                    main_result["summary"]["critical_issues"] += 1
                elif severity == ValidationSeverity.WARNING.value:
                    main_result["summary"]["warnings"] += 1
                else:
                    main_result["summary"]["info_items"] += 1
                
                # Count sessions with issues
                if "session_id" in issue:
                    main_result["summary"]["sessions_with_issues"] += 1
    
    def _determine_overall_health_status(self, validation_result: Dict[str, Any]) -> str:
        """Determine overall health status from validation results"""
        
        critical_issues = validation_result["summary"]["critical_issues"]
        warnings = validation_result["summary"]["warnings"]
        
        if critical_issues > 0:
            return HealthStatus.UNHEALTHY.value
        elif warnings > 5:
            return HealthStatus.DEGRADED.value
        elif warnings > 0:
            return HealthStatus.DEGRADED.value
        else:
            return HealthStatus.HEALTHY.value
    
    def _determine_overall_health_from_components(self, components: List[Dict[str, Any]]) -> str:
        """Determine overall health from component health checks"""
        
        statuses = [comp.get("status", HealthStatus.HEALTHY.value) for comp in components]
        
        if HealthStatus.CRITICAL.value in statuses:
            return HealthStatus.CRITICAL.value
        elif HealthStatus.UNHEALTHY.value in statuses:
            return HealthStatus.UNHEALTHY.value
        elif HealthStatus.DEGRADED.value in statuses:
            return HealthStatus.DEGRADED.value
        else:
            return HealthStatus.HEALTHY.value
    
    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        
        recommendations = []
        
        # Analyze issues and generate specific recommendations
        critical_issues = validation_result["summary"]["critical_issues"]
        warnings = validation_result["summary"]["warnings"]
        
        if critical_issues > 0:
            recommendations.append("Immediate attention required: Critical difficulty state issues detected")
            recommendations.append("Run recovery operations for affected sessions")
            recommendations.append("Consider temporarily disabling adaptive difficulty features")
        
        if warnings > 10:
            recommendations.append("High number of warnings detected - schedule maintenance window")
            recommendations.append("Review difficulty state management configuration")
        
        # Check specific issue patterns
        issues = validation_result.get("issues_found", [])
        corruption_issues = [i for i in issues if i.get("category") == "data_corruption"]
        cache_issues = [i for i in issues if i.get("category") == "cache_inconsistency"]
        
        if len(corruption_issues) > 0:
            recommendations.append("Data corruption detected - run full recovery process")
            recommendations.append("Backup current state before applying fixes")
        
        if len(cache_issues) > 5:
            recommendations.append("Cache inconsistency detected - consider cache refresh")
            recommendations.append("Monitor cache performance and consider tuning")
        
        if not recommendations:
            recommendations.append("System appears healthy - continue regular monitoring")
        
        return recommendations
    
    def _generate_health_alerts(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate alerts from health check components"""
        
        alerts = []
        
        for component in components:
            component_issues = component.get("issues", [])
            for issue in component_issues:
                if issue.get("severity") in [ValidationSeverity.ERROR.value, ValidationSeverity.CRITICAL.value]:
                    alerts.append({
                        "severity": issue["severity"],
                        "message": issue["message"],
                        "component": component.get("component_name", "unknown"),
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        return alerts
    
    def _generate_health_recommendations(self, health_check: Dict[str, Any]) -> List[str]:
        """Generate recommendations from health check results"""
        
        recommendations = []
        overall_status = health_check["overall_status"]
        
        if overall_status == HealthStatus.CRITICAL.value:
            recommendations.extend([
                "CRITICAL: Immediate intervention required",
                "Stop all difficulty-related operations",
                "Contact system administrator",
                "Review system logs for detailed error information"
            ])
        elif overall_status == HealthStatus.UNHEALTHY.value:
            recommendations.extend([
                "System is unhealthy - schedule immediate maintenance",
                "Run full diagnostic and recovery procedures",
                "Monitor system closely"
            ])
        elif overall_status == HealthStatus.DEGRADED.value:
            recommendations.extend([
                "System performance is degraded",
                "Schedule maintenance during low-usage period",
                "Run validation and cleanup procedures"
            ])
        else:
            recommendations.append("System is healthy - continue regular monitoring")
        
        return recommendations
    
    def _calculate_health_metrics(self) -> Dict[str, Any]:
        """Calculate key health metrics"""
        
        try:
            metrics = {}
            
            # Calculate error rates
            total_sessions = self.db.query(func.count(InterviewSession.id)).scalar()
            sessions_with_issues = self.db.query(func.count(InterviewSession.id)).filter(
                or_(
                    InterviewSession.difficulty_level.is_(None),
                    InterviewSession.difficulty_state_json == '{}'
                )
            ).scalar()
            
            metrics["total_sessions"] = total_sessions
            metrics["sessions_with_issues"] = sessions_with_issues
            metrics["error_rate"] = sessions_with_issues / max(total_sessions, 1)
            
            # Calculate cache metrics
            cache_size = len(self.session_difficulty_service.session_states)
            metrics["cache_size"] = cache_size
            metrics["cache_hit_potential"] = min(cache_size / max(total_sessions, 1), 1.0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating health metrics: {str(e)}")
            return {"error": str(e)}
    
    def _extract_session_info(self, session: InterviewSession) -> Dict[str, Any]:
        """Extract comprehensive session information for diagnostics"""
        
        return {
            "id": session.id,
            "user_id": session.user_id,
            "status": session.status,
            "session_type": session.session_type,
            "target_role": session.target_role,
            "difficulty_level": session.difficulty_level,
            "initial_difficulty_level": getattr(session, 'initial_difficulty_level', None),
            "current_difficulty_level": getattr(session, 'current_difficulty_level', None),
            "final_difficulty_level": getattr(session, 'final_difficulty_level', None),
            "difficulty_changes_count": getattr(session, 'difficulty_changes_count', 0),
            "session_mode": getattr(session, 'session_mode', None),
            "parent_session_id": getattr(session, 'parent_session_id', None),
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "has_json_state": session.difficulty_state_json is not None
        }
    
    def _analyze_session_difficulty_state(self, session: InterviewSession) -> Dict[str, Any]:
        """Analyze difficulty state for a specific session"""
        
        analysis = {
            "state_exists": False,
            "state_valid": False,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Try to get state from service
            state = self.session_difficulty_service.get_session_difficulty_state(session.id)
            
            if state:
                analysis["state_exists"] = True
                
                # Validate state
                validation_errors = state.validate_state()
                if validation_errors:
                    analysis["issues"].extend([
                        {
                            "severity": ValidationSeverity.ERROR.value,
                            "category": "state_validation",
                            "message": f"State validation error: {error}",
                            "session_id": session.id
                        }
                        for error in validation_errors
                    ])
                else:
                    analysis["state_valid"] = True
            else:
                analysis["issues"].append({
                    "severity": ValidationSeverity.WARNING.value,
                    "category": "missing_state",
                    "message": "No difficulty state found for session",
                    "session_id": session.id
                })
                analysis["recommendations"].append("Attempt state recovery")
            
        except Exception as e:
            analysis["issues"].append({
                "severity": ValidationSeverity.ERROR.value,
                "category": "state_analysis_error",
                "message": f"Error analyzing state: {str(e)}",
                "session_id": session.id
            })
        
        return analysis
    
    def _analyze_session_cache_state(self, session_id: int) -> Dict[str, Any]:
        """Analyze cache state for a session"""
        
        analysis = {
            "in_cache": False,
            "cache_valid": False,
            "issues": [],
            "recommendations": []
        }
        
        try:
            cached_state = self.session_difficulty_service.session_states.get(session_id)
            
            if cached_state:
                analysis["in_cache"] = True
                
                # Basic cache validation
                if hasattr(cached_state, 'session_id') and cached_state.session_id == session_id:
                    analysis["cache_valid"] = True
                else:
                    analysis["issues"].append({
                        "severity": ValidationSeverity.ERROR.value,
                        "category": "cache_corruption",
                        "message": "Cached state has incorrect session_id",
                        "session_id": session_id
                    })
                    analysis["recommendations"].append("Clear and reload cache entry")
            else:
                analysis["recommendations"].append("Load state into cache if needed")
            
        except Exception as e:
            analysis["issues"].append({
                "severity": ValidationSeverity.ERROR.value,
                "category": "cache_analysis_error",
                "message": f"Error analyzing cache: {str(e)}",
                "session_id": session_id
            })
        
        return analysis
    
    def _analyze_session_database_state(self, session: InterviewSession) -> Dict[str, Any]:
        """Analyze database state for a session"""
        
        analysis = {
            "database_consistent": True,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Check field consistency
            if not session.difficulty_level:
                analysis["database_consistent"] = False
                analysis["issues"].append({
                    "severity": ValidationSeverity.ERROR.value,
                    "category": "missing_difficulty",
                    "message": "Missing difficulty_level in database",
                    "session_id": session.id
                })
                analysis["recommendations"].append("Set default difficulty level")
            
            # Check JSON state
            if session.difficulty_state_json:
                try:
                    json_state = session.difficulty_state_json
                    if not isinstance(json_state, dict):
                        analysis["database_consistent"] = False
                        analysis["issues"].append({
                            "severity": ValidationSeverity.ERROR.value,
                            "category": "invalid_json",
                            "message": "Invalid JSON state format",
                            "session_id": session.id
                        })
                        analysis["recommendations"].append("Rebuild JSON state from fields")
                except Exception:
                    analysis["database_consistent"] = False
                    analysis["issues"].append({
                        "severity": ValidationSeverity.ERROR.value,
                        "category": "corrupted_json",
                        "message": "Corrupted JSON state",
                        "session_id": session.id
                    })
                    analysis["recommendations"].append("Clear corrupted JSON state")
            
        except Exception as e:
            analysis["issues"].append({
                "severity": ValidationSeverity.ERROR.value,
                "category": "database_analysis_error",
                "message": f"Error analyzing database state: {str(e)}",
                "session_id": session.id
            })
        
        return analysis
    
    def _generate_recovery_options(
        self, 
        session: InterviewSession,
        issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate recovery options based on detected issues"""
        
        recovery_options = []
        
        # Analyze issue types
        has_state_corruption = any(i.get("category") == "state_validation" for i in issues)
        has_missing_state = any(i.get("category") == "missing_state" for i in issues)
        has_cache_issues = any(i.get("category") in ["cache_corruption", "cache_inconsistency"] for i in issues)
        has_database_issues = any(i.get("category") in ["missing_difficulty", "corrupted_json"] for i in issues)
        
        if has_state_corruption or has_missing_state:
            recovery_options.append({
                "option": "full_state_recovery",
                "description": "Attempt full difficulty state recovery using all available methods",
                "risk": "low",
                "estimated_success": "high"
            })
        
        if has_cache_issues:
            recovery_options.append({
                "option": "cache_refresh",
                "description": "Clear cache and reload from database",
                "risk": "very_low",
                "estimated_success": "high"
            })
        
        if has_database_issues:
            recovery_options.append({
                "option": "database_repair",
                "description": "Repair database fields and JSON state",
                "risk": "low",
                "estimated_success": "medium"
            })
        
        # Always offer fallback option
        recovery_options.append({
            "option": "fallback_reset",
            "description": "Reset to safe default state",
            "risk": "very_low",
            "estimated_success": "high",
            "note": "Will lose existing difficulty progression"
        })
        
        return recovery_options
    
    def _generate_diagnostic_recommendations(self, diagnostic_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on diagnostic results"""
        
        recommendations = []
        issues = diagnostic_result.get("issues_detected", [])
        
        if not issues:
            recommendations.append("No issues detected - session appears healthy")
            return recommendations
        
        # Prioritize recommendations by severity
        critical_issues = [i for i in issues if i.get("severity") == ValidationSeverity.CRITICAL.value]
        error_issues = [i for i in issues if i.get("severity") == ValidationSeverity.ERROR.value]
        
        if critical_issues:
            recommendations.append("CRITICAL: Immediate action required")
            recommendations.append("Consider stopping operations for this session")
        
        if error_issues:
            recommendations.append("Run recovery procedures for this session")
            recommendations.append("Monitor session closely after recovery")
        
        # Specific recommendations based on issue categories
        issue_categories = [i.get("category") for i in issues]
        
        if "state_validation" in issue_categories:
            recommendations.append("Rebuild difficulty state from database fields")
        
        if "cache_corruption" in issue_categories:
            recommendations.append("Clear cache entry and reload from database")
        
        if "missing_difficulty" in issue_categories:
            recommendations.append("Set default difficulty level for session")
        
        return recommendations
    
    def _perform_soft_reset(self, session: InterviewSession) -> bool:
        """Perform soft reset (clear cache, keep database)"""
        try:
            # Clear from cache
            if session.id in self.session_difficulty_service.session_states:
                del self.session_difficulty_service.session_states[session.id]
            
            logger.info(f"Performed soft reset for session {session.id}")
            return True
        except Exception as e:
            logger.error(f"Error in soft reset for session {session.id}: {str(e)}")
            return False
    
    def _perform_hard_reset(self, session: InterviewSession) -> bool:
        """Perform hard reset (clear cache and reset database fields)"""
        try:
            # Clear from cache
            if session.id in self.session_difficulty_service.session_states:
                del self.session_difficulty_service.session_states[session.id]
            
            # Reset database fields to defaults
            session.difficulty_level = session.difficulty_level or "medium"
            session.initial_difficulty_level = session.difficulty_level
            session.current_difficulty_level = session.difficulty_level
            session.final_difficulty_level = None
            session.difficulty_changes_count = 0
            session.difficulty_state_json = None
            
            self.db.commit()
            
            logger.info(f"Performed hard reset for session {session.id}")
            return True
        except Exception as e:
            logger.error(f"Error in hard reset for session {session.id}: {str(e)}")
            self.db.rollback()
            return False
    
    def _perform_cache_only_reset(self, session: InterviewSession) -> bool:
        """Perform cache-only reset"""
        try:
            # Only clear from cache
            if session.id in self.session_difficulty_service.session_states:
                del self.session_difficulty_service.session_states[session.id]
            
            logger.info(f"Performed cache-only reset for session {session.id}")
            return True
        except Exception as e:
            logger.error(f"Error in cache-only reset for session {session.id}: {str(e)}")
            return False
    
    def _create_validation_error_response(
        self, 
        error: Exception,
        session_id: Optional[int],
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """Create error response for validation failures"""
        
        return {
            "validation_id": f"error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "success": False,
            "error": str(error),
            "scope": {
                "session_id": session_id,
                "user_id": user_id
            },
            "overall_status": HealthStatus.CRITICAL.value,
            "summary": {
                "total_sessions_checked": 0,
                "sessions_with_issues": 0,
                "critical_issues": 1,
                "warnings": 0,
                "info_items": 0
            },
            "issues_found": [{
                "severity": ValidationSeverity.CRITICAL.value,
                "category": "validation_error",
                "message": f"Validation process failed: {str(error)}"
            }],
            "recommendations": [
                "Check system logs for detailed error information",
                "Contact system administrator",
                "Retry validation after resolving underlying issues"
            ]
        }
    
    def _create_health_check_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create error response for health check failures"""
        
        return {
            "check_id": f"error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "success": False,
            "error": str(error),
            "overall_status": HealthStatus.CRITICAL.value,
            "components": {},
            "alerts": [{
                "severity": ValidationSeverity.CRITICAL.value,
                "message": f"Health check process failed: {str(error)}",
                "timestamp": datetime.utcnow().isoformat()
            }],
            "recommendations": [
                "CRITICAL: Health check system is not functioning",
                "Check system logs immediately",
                "Contact system administrator",
                "Manual system inspection required"
            ],
            "metrics": {"error": str(error)}
        }
    
    def _create_diagnostic_error_response(self, error: Exception, session_id: int) -> Dict[str, Any]:
        """Create error response for diagnostic failures"""
        
        return {
            "session_id": session_id,
            "diagnosis_id": f"error_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "success": False,
            "error": str(error),
            "session_found": False,
            "issues_detected": [{
                "severity": ValidationSeverity.CRITICAL.value,
                "category": "diagnostic_error",
                "message": f"Diagnostic process failed: {str(error)}",
                "impact": "Cannot determine session health status"
            }],
            "recommended_actions": [
                "Check system logs for detailed error information",
                "Verify session exists in database",
                "Contact system administrator if problem persists"
            ]
        }