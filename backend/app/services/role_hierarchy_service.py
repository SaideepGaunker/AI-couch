"""
Role Hierarchy Service for managing hierarchical role data and question filtering
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import RoleHierarchy, Question
from app.schemas.role_hierarchy import HierarchicalRole

logger = logging.getLogger(__name__)


class RoleHierarchyService:
    """Service for managing role hierarchy operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self._role_cache = {}
    
    def get_role_hierarchy(self, version: str = "1.0") -> List[Dict[str, Any]]:
        """
        Get the complete role hierarchy structure
        
        Args:
            version: Version of hierarchy to retrieve
            
        Returns:
            List of hierarchical role data
        """
        
        try:
            logger.info(f"Getting role hierarchy for version: {version}")
            
            # Check cache first
            cache_key = f"hierarchy_{version}"
            if cache_key in self._role_cache:
                logger.info("Retrieved role hierarchy from cache")
                return self._role_cache[cache_key]
            
            # Query database
            roles = self.db.query(RoleHierarchy).filter(
                and_(
                    RoleHierarchy.version == version,
                    RoleHierarchy.is_active == True
                )
            ).all()
            
            if not roles:
                logger.warning(f"No role hierarchy found for version {version}")
                return []
            
            # Organize into hierarchical structure
            hierarchy = self._organize_hierarchy(roles)
            
            # Cache the result
            self._role_cache[cache_key] = hierarchy
            
            logger.info(f"Retrieved {len(hierarchy)} main roles from hierarchy")
            return hierarchy
            
        except Exception as e:
            logger.error(f"Error getting role hierarchy: {str(e)}")
            return []
    
    def _organize_hierarchy(self, roles: List[RoleHierarchy]) -> List[Dict[str, Any]]:
        """
        Organize flat role list into hierarchical structure
        """
        
        hierarchy = {}
        
        for role in roles:
            main_role = role.main_role
            sub_role = role.sub_role or "General"
            specialization = role.specialization
            
            # Initialize main role if not exists
            if main_role not in hierarchy:
                hierarchy[main_role] = {
                    "main_role": main_role,
                    "sub_roles": {}
                }
            
            # Initialize sub role if not exists
            if sub_role not in hierarchy[main_role]["sub_roles"]:
                hierarchy[main_role]["sub_roles"][sub_role] = {
                    "sub_role": sub_role,
                    "specializations": [],
                    "tech_stacks": role.tech_stack or [],
                    "question_tags": role.question_tags or []
                }
            
            # Add specialization if it exists and not already added
            if specialization and specialization not in hierarchy[main_role]["sub_roles"][sub_role]["specializations"]:
                hierarchy[main_role]["sub_roles"][sub_role]["specializations"].append(specialization)
            
            # Merge tech stacks and question tags
            existing_tech = hierarchy[main_role]["sub_roles"][sub_role]["tech_stacks"]
            existing_tags = hierarchy[main_role]["sub_roles"][sub_role]["question_tags"]
            
            if role.tech_stack:
                for tech in role.tech_stack:
                    if tech not in existing_tech:
                        existing_tech.append(tech)
            
            if role.question_tags:
                for tag in role.question_tags:
                    if tag not in existing_tags:
                        existing_tags.append(tag)
        
        # Convert to list format
        result = []
        for main_role, main_data in hierarchy.items():
            sub_roles_list = []
            for sub_role, sub_data in main_data["sub_roles"].items():
                sub_roles_list.append(sub_data)
            
            result.append({
                "main_role": main_role,
                "sub_roles": sub_roles_list
            })
        
        return result
    
    def validate_role_combination(
        self,
        main_role: str,
        sub_role: Optional[str] = None,
        specialization: Optional[str] = None,
        version: str = "1.0"
    ) -> bool:
        """
        Validate if a role combination exists in the hierarchy
        """
        
        try:
            logger.info(f"Validating role combination: {main_role}/{sub_role}/{specialization}")
            
            query = self.db.query(RoleHierarchy).filter(
                and_(
                    RoleHierarchy.main_role == main_role,
                    RoleHierarchy.version == version,
                    RoleHierarchy.is_active == True
                )
            )
            
            if sub_role:
                query = query.filter(RoleHierarchy.sub_role == sub_role)
            
            if specialization:
                query = query.filter(RoleHierarchy.specialization == specialization)
            
            role_exists = query.first() is not None
            
            logger.info(f"Role combination validation result: {role_exists}")
            return role_exists
            
        except Exception as e:
            logger.error(f"Error validating role combination: {str(e)}")
            return False
    
    def get_sub_roles_for_main_role(
        self,
        main_role: str,
        version: str = "1.0"
    ) -> List[str]:
        """
        Get all sub-roles for a given main role
        """
        
        try:
            logger.info(f"Getting sub-roles for main role: {main_role}")
            
            roles = self.db.query(RoleHierarchy.sub_role).filter(
                and_(
                    RoleHierarchy.main_role == main_role,
                    RoleHierarchy.version == version,
                    RoleHierarchy.is_active == True,
                    RoleHierarchy.sub_role.isnot(None)
                )
            ).distinct().all()
            
            sub_roles = [role.sub_role for role in roles if role.sub_role]
            
            logger.info(f"Found {len(sub_roles)} sub-roles for {main_role}")
            return sub_roles
            
        except Exception as e:
            logger.error(f"Error getting sub-roles: {str(e)}")
            return []
    
    def get_specializations_for_sub_role(
        self,
        main_role: str,
        sub_role: str,
        version: str = "1.0"
    ) -> List[str]:
        """
        Get all specializations for a given main role and sub role combination
        """
        
        try:
            logger.info(f"Getting specializations for {main_role}/{sub_role}")
            
            roles = self.db.query(RoleHierarchy.specialization).filter(
                and_(
                    RoleHierarchy.main_role == main_role,
                    RoleHierarchy.sub_role == sub_role,
                    RoleHierarchy.version == version,
                    RoleHierarchy.is_active == True,
                    RoleHierarchy.specialization.isnot(None)
                )
            ).distinct().all()
            
            specializations = [role.specialization for role in roles if role.specialization]
            
            logger.info(f"Found {len(specializations)} specializations")
            return specializations
            
        except Exception as e:
            logger.error(f"Error getting specializations: {str(e)}")
            return []
    
    def get_tech_stacks_for_role(
        self,
        main_role: str,
        sub_role: Optional[str] = None,
        version: str = "1.0"
    ) -> List[str]:
        """
        Get tech stacks associated with a role combination
        """
        
        try:
            logger.info(f"Getting tech stacks for {main_role}/{sub_role}")
            
            query = self.db.query(RoleHierarchy).filter(
                and_(
                    RoleHierarchy.main_role == main_role,
                    RoleHierarchy.version == version,
                    RoleHierarchy.is_active == True
                )
            )
            
            if sub_role:
                query = query.filter(RoleHierarchy.sub_role == sub_role)
            
            roles = query.all()
            
            # Collect all unique tech stacks
            tech_stacks = set()
            for role in roles:
                if role.tech_stack:
                    tech_stacks.update(role.tech_stack)
            
            tech_stack_list = list(tech_stacks)
            
            logger.info(f"Found {len(tech_stack_list)} tech stacks")
            return tech_stack_list
            
        except Exception as e:
            logger.error(f"Error getting tech stacks: {str(e)}")
            return []
    
    def get_question_tags_for_role(
        self,
        main_role: str,
        sub_role: Optional[str] = None,
        specialization: Optional[str] = None,
        version: str = "1.0"
    ) -> List[str]:
        """
        Get question tags associated with a role combination
        """
        
        try:
            logger.info(f"Getting question tags for {main_role}/{sub_role}/{specialization}")
            
            query = self.db.query(RoleHierarchy).filter(
                and_(
                    RoleHierarchy.main_role == main_role,
                    RoleHierarchy.version == version,
                    RoleHierarchy.is_active == True
                )
            )
            
            if sub_role:
                query = query.filter(RoleHierarchy.sub_role == sub_role)
            
            if specialization:
                query = query.filter(RoleHierarchy.specialization == specialization)
            
            roles = query.all()
            
            # Collect all unique question tags
            question_tags = set()
            for role in roles:
                if role.question_tags:
                    question_tags.update(role.question_tags)
            
            tags_list = list(question_tags)
            
            logger.info(f"Found {len(tags_list)} question tags")
            return tags_list
            
        except Exception as e:
            logger.error(f"Error getting question tags: {str(e)}")
            return []
    
    def filter_questions_by_role(
        self,
        role_data: HierarchicalRole,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Question]:
        """
        Filter questions based on hierarchical role data
        """
        
        try:
            logger.info(f"Filtering questions for role: {role_data.main_role}/{role_data.sub_role}")
            
            # Get question tags for this role combination
            question_tags = self.get_question_tags_for_role(
                role_data.main_role,
                role_data.sub_role,
                role_data.specialization
            )
            
            # Build query
            query = self.db.query(Question)
            
            # Filter by role category (fallback to main role)
            role_filter = or_(
                Question.role_category == role_data.main_role,
                Question.role_category == f"{role_data.main_role} - {role_data.sub_role}" if role_data.sub_role else False
            )
            query = query.filter(role_filter)
            
            # Filter by difficulty if specified
            if difficulty:
                query = query.filter(Question.difficulty_level == difficulty)
            
            # Filter by question type if specified
            if question_type:
                query = query.filter(Question.question_type == question_type)
            
            # Filter by question tags if available
            if question_tags:
                # Check if any of the question's difficulty tags match our role tags
                tag_conditions = []
                for tag in question_tags:
                    tag_conditions.append(Question.question_difficulty_tags.contains([tag]))
                
                if tag_conditions:
                    query = query.filter(or_(*tag_conditions))
            
            questions = query.limit(limit).all()
            
            logger.info(f"Found {len(questions)} questions matching role criteria")
            return questions
            
        except Exception as e:
            logger.error(f"Error filtering questions by role: {str(e)}")
            return []
    
    def seed_role_hierarchy(self) -> int:
        """
        Seed the database with initial role hierarchy data
        """
        
        try:
            logger.info("Seeding role hierarchy data")
            
            # Define the role hierarchy structure - same as CRUD for consistency
            hierarchy_data = [
                # Software Developer roles
                {
                    "main_role": "Software Developer",
                    "sub_role": "Frontend Developer",
                    "specialization": "React Developer",
                    "tech_stacks": ["React", "JavaScript", "TypeScript", "HTML", "CSS"],
                    "question_tags": ["react", "frontend", "javascript", "ui-ux"]
                },
                {
                    "main_role": "Software Developer",
                    "sub_role": "Mobile Developer",
                    "specialization": "iOS Developer",
                    "tech_stacks": ["Swift", "Objective-C", "Xcode", "iOS SDK", "Core Data"],
                    "question_tags": ["ios", "mobile", "swift", "app-development"]
                },
                
                # Data Scientist roles
                {
                    "main_role": "Data Scientist",
                    "sub_role": "ML Engineer",
                    "specialization": "Computer Vision Engineer",
                    "tech_stacks": ["Python", "TensorFlow", "OpenCV", "PyTorch", "Scikit-learn"],
                    "question_tags": ["machine-learning", "computer-vision", "deep-learning", "image-processing"]
                },
                
                # Product Manager roles
                {
                    "main_role": "Product Manager",
                    "sub_role": "Technical Product Manager",
                    "specialization": "API Product Manager",
                    "tech_stacks": ["Jira", "Confluence", "Figma", "SQL", "Python"],
                    "question_tags": ["product-management", "technical-pm", "api-strategy", "roadmapping"]
                },
                
                # DevOps Engineer roles
                {
                    "main_role": "DevOps Engineer",
                    "sub_role": "Site Reliability Engineer",
                    "specialization": "Platform SRE",
                    "tech_stacks": ["Kubernetes", "Docker", "Prometheus", "Grafana", "Terraform"],
                    "question_tags": ["sre", "reliability", "monitoring", "incident-response"]
                },
                
                # UX/UI Designer roles
                {
                    "main_role": "UX/UI Designer",
                    "sub_role": "UX Designer",
                    "specialization": "User Researcher",
                    "tech_stacks": ["Figma", "Sketch", "Adobe XD", "Miro", "UserTesting"],
                    "question_tags": ["ux-design", "user-research", "usability", "design-thinking"]
                },
                
                # Cybersecurity Specialist roles
                {
                    "main_role": "Cybersecurity Specialist",
                    "sub_role": "Security Analyst",
                    "specialization": "SOC Analyst",
                    "tech_stacks": ["SIEM Tools", "Splunk", "Wireshark", "Nessus", "Metasploit"],
                    "question_tags": ["security-analysis", "soc", "incident-response", "threat-hunting"]
                },
                
                # Business Analyst roles
                {
                    "main_role": "Business Analyst",
                    "sub_role": "Systems Analyst",
                    "specialization": "ERP Analyst",
                    "tech_stacks": ["SQL", "Excel", "Tableau", "SAP", "Oracle"],
                    "question_tags": ["systems-analysis", "erp", "business-processes", "requirements-gathering"]
                },
                
                # Sales Representative roles
                {
                    "main_role": "Sales Representative",
                    "sub_role": "Inside Sales",
                    "specialization": "SaaS Sales Specialist",
                    "tech_stacks": ["Salesforce", "HubSpot", "Outreach", "LinkedIn Sales Navigator", "Zoom"],
                    "question_tags": ["inside-sales", "saas-sales", "lead-generation", "crm"]
                }
            ]
            
            created_count = 0
            
            for role_data in hierarchy_data:
                try:
                    # Check if role combination already exists
                    existing = self.db.query(RoleHierarchy).filter(
                        and_(
                            RoleHierarchy.main_role == role_data["main_role"],
                            RoleHierarchy.sub_role == role_data["sub_role"],
                            RoleHierarchy.specialization == role_data.get("specialization"),
                            RoleHierarchy.version == "1.0"
                        )
                    ).first()
                    
                    if not existing:
                        db_role = RoleHierarchy(
                            main_role=role_data["main_role"],
                            sub_role=role_data["sub_role"],
                            specialization=role_data.get("specialization"),
                            tech_stack=role_data["tech_stacks"],
                            question_tags=role_data["question_tags"],
                            version="1.0",
                            is_active=True
                        )
                        self.db.add(db_role)
                        created_count += 1
                        
                except Exception as e:
                    logger.error(f"Error creating role hierarchy entry: {str(e)}")
                    continue
            
            self.db.commit()
            
            # Clear cache after seeding
            self._role_cache.clear()
            
            logger.info(f"Successfully seeded {created_count} role hierarchy entries")
            return created_count
            
        except Exception as e:
            logger.error(f"Error seeding role hierarchy: {str(e)}")
            self.db.rollback()
            return 0
    
    def clear_cache(self):
        """Clear the role hierarchy cache"""
        self._role_cache.clear()
        logger.info("Role hierarchy cache cleared")