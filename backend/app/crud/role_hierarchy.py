"""
CRUD operations for Role Hierarchy
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime

from app.db.models import RoleHierarchy, User
from app.schemas.role_hierarchy import RoleHierarchyCreate, UserRoleUpdate


def create_role_hierarchy_entry(
    db: Session, 
    role_data: RoleHierarchyCreate
) -> RoleHierarchy:
    """Create new role hierarchy entry"""
    
    # Check if entry already exists
    existing = db.query(RoleHierarchy).filter(
        and_(
            RoleHierarchy.main_role == role_data.main_role,
            RoleHierarchy.sub_role == role_data.sub_role,
            RoleHierarchy.specialization == role_data.specialization,
            RoleHierarchy.version == role_data.version
        )
    ).first()
    
    if existing:
        return existing
    
    db_role = RoleHierarchy(
        main_role=role_data.main_role,
        sub_role=role_data.sub_role,
        specialization=role_data.specialization,
        tech_stack=role_data.tech_stack or [],
        question_tags=role_data.question_tags or [],
        version=role_data.version or "1.0",
        is_active=role_data.is_active if role_data.is_active is not None else True
    )
    
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


def get_role_hierarchy_entry(
    db: Session, 
    entry_id: int
) -> Optional[RoleHierarchy]:
    """Get role hierarchy entry by ID"""
    return db.query(RoleHierarchy).filter(RoleHierarchy.id == entry_id).first()


def get_role_hierarchy_entries(
    db: Session,
    main_role: Optional[str] = None,
    sub_role: Optional[str] = None,
    version: str = "1.0",
    is_active: bool = True,
    skip: int = 0,
    limit: int = 100
) -> List[RoleHierarchy]:
    """Get role hierarchy entries with optional filtering"""
    query = db.query(RoleHierarchy)
    
    if main_role:
        query = query.filter(RoleHierarchy.main_role == main_role)
    if sub_role:
        query = query.filter(RoleHierarchy.sub_role == sub_role)
    if version:
        query = query.filter(RoleHierarchy.version == version)
    if is_active is not None:
        query = query.filter(RoleHierarchy.is_active == is_active)
    
    return query.order_by(
        RoleHierarchy.main_role,
        RoleHierarchy.sub_role,
        RoleHierarchy.specialization
    ).offset(skip).limit(limit).all()


def update_role_hierarchy_entry(
    db: Session,
    entry_id: int,
    update_data: Dict[str, Any]
) -> Optional[RoleHierarchy]:
    """Update role hierarchy entry"""
    entry = get_role_hierarchy_entry(db, entry_id)
    if not entry:
        return None
    
    for field, value in update_data.items():
        if hasattr(entry, field):
            setattr(entry, field, value)
    
    db.commit()
    db.refresh(entry)
    return entry


def delete_role_hierarchy_entry(db: Session, entry_id: int) -> bool:
    """Delete role hierarchy entry (soft delete by setting is_active=False)"""
    entry = get_role_hierarchy_entry(db, entry_id)
    if not entry:
        return False
    
    # Soft delete by setting is_active to False
    entry.is_active = False
    db.commit()
    return True


def get_main_roles(db: Session, version: str = "1.0") -> List[str]:
    """Get all unique main roles"""
    roles = db.query(RoleHierarchy.main_role).filter(
        and_(
            RoleHierarchy.version == version,
            RoleHierarchy.is_active == True
        )
    ).distinct().all()
    
    return [role.main_role for role in roles if role.main_role]


def get_sub_roles_for_main_role(
    db: Session, 
    main_role: str, 
    version: str = "1.0"
) -> List[str]:
    """Get all sub-roles for a given main role"""
    roles = db.query(RoleHierarchy.sub_role).filter(
        and_(
            RoleHierarchy.main_role == main_role,
            RoleHierarchy.version == version,
            RoleHierarchy.is_active == True,
            RoleHierarchy.sub_role.isnot(None)
        )
    ).distinct().all()
    
    return [role.sub_role for role in roles if role.sub_role]


def get_specializations_for_role(
    db: Session,
    main_role: str,
    sub_role: Optional[str] = None,
    version: str = "1.0"
) -> List[str]:
    """Get all specializations for a given role combination"""
    query = db.query(RoleHierarchy.specialization).filter(
        and_(
            RoleHierarchy.main_role == main_role,
            RoleHierarchy.version == version,
            RoleHierarchy.is_active == True,
            RoleHierarchy.specialization.isnot(None)
        )
    )
    
    if sub_role:
        query = query.filter(RoleHierarchy.sub_role == sub_role)
    
    roles = query.distinct().all()
    return [role.specialization for role in roles if role.specialization]


def get_tech_stacks_for_role(
    db: Session,
    main_role: str,
    sub_role: Optional[str] = None,
    version: str = "1.0"
) -> List[str]:
    """Get all tech stacks for a given role combination"""
    query = db.query(RoleHierarchy).filter(
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
    
    return list(tech_stacks)


def get_question_tags_for_role(
    db: Session,
    main_role: str,
    sub_role: Optional[str] = None,
    specialization: Optional[str] = None,
    version: str = "1.0"
) -> List[str]:
    """Get all question tags for a given role combination"""
    query = db.query(RoleHierarchy).filter(
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
    
    return list(question_tags)


def update_user_role(
    db: Session,
    user_id: int,
    role_update: UserRoleUpdate
) -> Optional[User]:
    """Update user's hierarchical role information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    # Update only provided fields
    if role_update.main_role is not None:
        user.main_role = role_update.main_role
    if role_update.sub_role is not None:
        user.sub_role = role_update.sub_role
    if role_update.specialization is not None:
        user.specialization = role_update.specialization
    
    db.commit()
    db.refresh(user)
    return user


def get_user_role(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's current hierarchical role information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    return {
        "user_id": user.id,
        "main_role": user.main_role,
        "sub_role": user.sub_role,
        "specialization": user.specialization
    }


def validate_role_combination(
    db: Session,
    main_role: str,
    sub_role: Optional[str] = None,
    specialization: Optional[str] = None,
    version: str = "1.0"
) -> bool:
    """Validate if a role combination exists in the hierarchy"""
    query = db.query(RoleHierarchy).filter(
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
    
    return query.first() is not None


def get_complete_role_hierarchy_structure(db: Session, version: str = "1.0") -> Dict[str, Any]:
    """Get complete role hierarchy structure as nested dictionary for frontend"""
    try:
        # Get all role hierarchy entries
        entries = db.query(RoleHierarchy).filter(
            RoleHierarchy.version == version
        ).all()
        
        if not entries:
            # Return default structure if no data exists
            return {
                "Software Developer": {
                    "Frontend Developer": {
                        "specializations": ["React Developer", "Angular Developer", "Vue.js Developer"],
                        "tech_stacks": ["React", "Angular", "Vue.js", "JavaScript", "TypeScript"]
                    },
                    "Backend Developer": {
                        "specializations": ["Node.js Developer", "Python Developer", "Java Developer"],
                        "tech_stacks": ["Node.js", "Python", "Java", "Spring Boot", "Express.js"]
                    },
                    "Full Stack Developer": {
                        "specializations": ["MEAN Stack", "MERN Stack", "Django Full Stack"],
                        "tech_stacks": ["React", "Node.js", "Python", "MongoDB", "PostgreSQL"]
                    }
                },
                "Data Scientist": {
                    "ML Engineer": {
                        "specializations": ["Computer Vision", "NLP Specialist", "Deep Learning"],
                        "tech_stacks": ["Python", "TensorFlow", "PyTorch", "Scikit-learn"]
                    },
                    "Data Analyst": {
                        "specializations": ["Business Intelligence", "Statistical Analysis"],
                        "tech_stacks": ["Python", "R", "SQL", "Tableau", "Power BI"]
                    }
                },
                "Marketing Manager": {
                    "Digital Marketing": {
                        "specializations": ["SEO Specialist", "Social Media Manager", "Content Marketing"],
                        "tech_stacks": ["Google Analytics", "Facebook Ads", "SEMrush"]
                    },
                    "Performance Marketing": {
                        "specializations": ["PPC Specialist", "Growth Hacker"],
                        "tech_stacks": ["Google Ads", "Facebook Ads", "Analytics"]
                    }
                }
            }
        
        # Build structure from database entries
        structure = {}
        for entry in entries:
            main_role = entry.main_role
            sub_role = entry.sub_role
            
            if main_role not in structure:
                structure[main_role] = {}
            
            if sub_role not in structure[main_role]:
                structure[main_role][sub_role] = {
                    "specializations": [],
                    "tech_stacks": []
                }
            
            # Add specialization if it exists and isn't already in the list
            if entry.specialization and entry.specialization not in structure[main_role][sub_role]["specializations"]:
                structure[main_role][sub_role]["specializations"].append(entry.specialization)
            
            # Merge tech stacks
            if entry.tech_stack:
                for tech in entry.tech_stack:
                    if tech not in structure[main_role][sub_role]["tech_stacks"]:
                        structure[main_role][sub_role]["tech_stacks"].append(tech)
        
        return structure
        
    except Exception as e:
        # Return default structure on error
        return {
            "Software Developer": {
                "Frontend Developer": {
                    "specializations": ["React Developer", "Angular Developer", "Vue.js Developer"],
                    "tech_stacks": ["React", "Angular", "Vue.js", "JavaScript", "TypeScript"]
                },
                "Backend Developer": {
                    "specializations": ["Node.js Developer", "Python Developer", "Java Developer"],
                    "tech_stacks": ["Node.js", "Python", "Java", "Spring Boot", "Express.js"]
                }
            }
        }


def get_role_hierarchy_statistics(db: Session, version: str = "1.0") -> Dict[str, Any]:
    """Get statistics about the role hierarchy"""
    
    # Count total entries
    total_entries = db.query(func.count(RoleHierarchy.id)).filter(
        and_(
            RoleHierarchy.version == version,
            RoleHierarchy.is_active == True
        )
    ).scalar()
    
    # Count main roles
    main_roles_count = db.query(func.count(func.distinct(RoleHierarchy.main_role))).filter(
        and_(
            RoleHierarchy.version == version,
            RoleHierarchy.is_active == True
        )
    ).scalar()
    
    # Count sub roles
    sub_roles_count = db.query(func.count(func.distinct(RoleHierarchy.sub_role))).filter(
        and_(
            RoleHierarchy.version == version,
            RoleHierarchy.is_active == True,
            RoleHierarchy.sub_role.isnot(None)
        )
    ).scalar()
    
    # Count specializations
    specializations_count = db.query(func.count(func.distinct(RoleHierarchy.specialization))).filter(
        and_(
            RoleHierarchy.version == version,
            RoleHierarchy.is_active == True,
            RoleHierarchy.specialization.isnot(None)
        )
    ).scalar()
    
    # Get role distribution
    role_distribution = db.query(
        RoleHierarchy.main_role,
        func.count(RoleHierarchy.id)
    ).filter(
        and_(
            RoleHierarchy.version == version,
            RoleHierarchy.is_active == True
        )
    ).group_by(RoleHierarchy.main_role).all()
    
    distribution_dict = {role: count for role, count in role_distribution}
    
    return {
        "total_entries": total_entries,
        "main_roles_count": main_roles_count,
        "sub_roles_count": sub_roles_count,
        "specializations_count": specializations_count,
        "role_distribution": distribution_dict,
        "version": version
    }


def create_new_version(
    db: Session,
    source_version: str = "1.0",
    target_version: str = "2.0"
) -> int:
    """Create a new version of the role hierarchy by copying from existing version"""
    
    # Get all entries from source version
    source_entries = db.query(RoleHierarchy).filter(
        and_(
            RoleHierarchy.version == source_version,
            RoleHierarchy.is_active == True
        )
    ).all()
    
    created_count = 0
    
    for source_entry in source_entries:
        # Check if entry already exists in target version
        existing = db.query(RoleHierarchy).filter(
            and_(
                RoleHierarchy.main_role == source_entry.main_role,
                RoleHierarchy.sub_role == source_entry.sub_role,
                RoleHierarchy.specialization == source_entry.specialization,
                RoleHierarchy.version == target_version
            )
        ).first()
        
        if not existing:
            new_entry = RoleHierarchy(
                main_role=source_entry.main_role,
                sub_role=source_entry.sub_role,
                specialization=source_entry.specialization,
                tech_stack=source_entry.tech_stack.copy() if source_entry.tech_stack else [],
                question_tags=source_entry.question_tags.copy() if source_entry.question_tags else [],
                version=target_version,
                is_active=True
            )
            db.add(new_entry)
            created_count += 1
    
    db.commit()
    return created_count


def deactivate_version(db: Session, version: str) -> int:
    """Deactivate all entries in a specific version"""
    updated_count = db.query(RoleHierarchy).filter(
        RoleHierarchy.version == version
    ).update({"is_active": False})
    
    db.commit()
    return updated_count


# Alias functions for API compatibility
def create_role_hierarchy(db: Session, role_data: RoleHierarchyCreate) -> RoleHierarchy:
    """Alias for create_role_hierarchy_entry"""
    return create_role_hierarchy_entry(db, role_data)


def get_role_hierarchy(db: Session, entry_id: int) -> Optional[RoleHierarchy]:
    """Alias for get_role_hierarchy_entry"""
    return get_role_hierarchy_entry(db, entry_id)


def get_role_hierarchies(
    db: Session,
    main_role: Optional[str] = None,
    sub_role: Optional[str] = None,
    is_active: Optional[bool] = None,
    version: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[RoleHierarchy]:
    """Alias for get_role_hierarchy_entries with optional parameters"""
    return get_role_hierarchy_entries(
        db=db,
        main_role=main_role,
        sub_role=sub_role,
        version=version or "1.0",
        is_active=is_active if is_active is not None else True,
        skip=skip,
        limit=limit
    )


def update_role_hierarchy(
    db: Session,
    entry_id: int,
    update_data: Dict[str, Any]
) -> Optional[RoleHierarchy]:
    """Alias for update_role_hierarchy_entry"""
    return update_role_hierarchy_entry(db, entry_id, update_data)


def delete_role_hierarchy(db: Session, entry_id: int) -> bool:
    """Alias for delete_role_hierarchy_entry"""
    return delete_role_hierarchy_entry(db, entry_id)


def seed_role_hierarchy(db: Session) -> int:
    """Seed the database with initial role hierarchy data"""
    
    # Define the role hierarchy structure
    hierarchy_data = [
        # Software Developer roles
        {
            "main_role": "Software Developer",
            "sub_role": "Frontend Developer",
            "specialization": "React Developer",
            "tech_stack": ["React", "JavaScript", "TypeScript", "HTML", "CSS"],
            "question_tags": ["react", "frontend", "javascript", "ui-ux"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Frontend Developer",
            "specialization": "Angular Developer",
            "tech_stack": ["Angular", "TypeScript", "JavaScript", "HTML", "CSS"],
            "question_tags": ["angular", "frontend", "typescript", "ui-ux"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Frontend Developer",
            "specialization": "Vue Developer",
            "tech_stack": ["Vue.js", "JavaScript", "TypeScript", "HTML", "CSS"],
            "question_tags": ["vue", "frontend", "javascript", "ui-ux"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Backend Developer",
            "specialization": "Node.js Developer",
            "tech_stack": ["Node.js", "JavaScript", "Express", "MongoDB", "PostgreSQL"],
            "question_tags": ["nodejs", "backend", "javascript", "api"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Backend Developer",
            "specialization": "Python Developer",
            "tech_stack": ["Python", "Django", "Flask", "PostgreSQL", "Redis"],
            "question_tags": ["python", "backend", "django", "api"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Backend Developer",
            "specialization": "Rust Developer",
            "tech_stack": ["Rust", "Actix", "Tokio", "PostgreSQL"],
            "question_tags": ["rust", "backend", "systems", "performance"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Full Stack Developer",
            "specialization": None,
            "tech_stack": ["JavaScript", "Python", "React", "Node.js", "PostgreSQL"],
            "question_tags": ["fullstack", "javascript", "python", "web-development"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Mobile Developer",
            "specialization": "iOS Developer",
            "tech_stack": ["Swift", "Objective-C", "Xcode", "iOS SDK", "Core Data"],
            "question_tags": ["ios", "mobile", "swift", "app-development"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Mobile Developer",
            "specialization": "Android Developer",
            "tech_stack": ["Kotlin", "Java", "Android Studio", "Android SDK", "Firebase"],
            "question_tags": ["android", "mobile", "kotlin", "app-development"]
        },
        {
            "main_role": "Software Developer",
            "sub_role": "Mobile Developer",
            "specialization": "React Native Developer",
            "tech_stack": ["React Native", "JavaScript", "TypeScript", "Expo", "Redux"],
            "question_tags": ["react-native", "mobile", "cross-platform", "javascript"]
        },
        
        # Data Scientist roles
        {
            "main_role": "Data Scientist",
            "sub_role": "ML Engineer",
            "specialization": "Computer Vision Engineer",
            "tech_stack": ["Python", "TensorFlow", "OpenCV", "PyTorch", "Scikit-learn"],
            "question_tags": ["machine-learning", "computer-vision", "deep-learning", "image-processing"]
        },
        {
            "main_role": "Data Scientist",
            "sub_role": "AI Researcher",
            "specialization": None,
            "tech_stack": ["Python", "PyTorch", "TensorFlow", "Jupyter", "CUDA"],
            "question_tags": ["ai", "research", "deep-learning", "neural-networks"]
        },
        {
            "main_role": "Data Scientist",
            "sub_role": "Data Analyst",
            "specialization": "Business Intelligence Analyst",
            "tech_stack": ["Python", "R", "SQL", "Tableau", "Power BI"],
            "question_tags": ["data-analysis", "business-intelligence", "sql", "visualization"]
        },
        {
            "main_role": "Data Scientist",
            "sub_role": "NLP Specialist",
            "specialization": None,
            "tech_stack": ["Python", "NLTK", "spaCy", "Transformers", "PyTorch"],
            "question_tags": ["nlp", "text-processing", "transformers", "language-models"]
        },
        {
            "main_role": "Data Scientist",
            "sub_role": "Data Engineer",
            "specialization": "Big Data Engineer",
            "tech_stack": ["Apache Spark", "Hadoop", "Kafka", "Python", "Scala"],
            "question_tags": ["data-engineering", "big-data", "etl", "distributed-systems"]
        },
        
        # Marketing Manager roles
        {
            "main_role": "Marketing Manager",
            "sub_role": "SEO Specialist",
            "specialization": "Technical SEO",
            "tech_stack": ["Google Analytics", "SEMrush", "Ahrefs", "Google Search Console"],
            "question_tags": ["seo", "technical-seo", "search-optimization", "analytics"]
        },
        {
            "main_role": "Marketing Manager",
            "sub_role": "Performance Marketing",
            "specialization": "PPC Specialist",
            "tech_stack": ["Google Ads", "Facebook Ads", "Google Analytics", "Conversion Tracking"],
            "question_tags": ["performance-marketing", "ppc", "paid-ads", "conversion"]
        },
        {
            "main_role": "Marketing Manager",
            "sub_role": "Content Marketing",
            "specialization": "Content Strategist",
            "tech_stack": ["WordPress", "HubSpot", "Mailchimp", "Canva"],
            "question_tags": ["content-marketing", "content-strategy", "copywriting", "brand-strategy"]
        },
        {
            "main_role": "Marketing Manager",
            "sub_role": "Social Media Marketing",
            "specialization": "Community Manager",
            "tech_stack": ["Hootsuite", "Buffer", "Sprout Social", "Facebook Business"],
            "question_tags": ["social-media", "community-management", "brand-engagement", "viral-marketing"]
        },
        {
            "main_role": "Marketing Manager",
            "sub_role": "Digital Marketing",
            "specialization": "Growth Hacker",
            "tech_stack": ["Google Analytics", "Mixpanel", "Amplitude", "A/B Testing Tools"],
            "question_tags": ["growth-hacking", "digital-marketing", "analytics", "conversion-optimization"]
        },
        
        # Product Manager roles
        {
            "main_role": "Product Manager",
            "sub_role": "Technical Product Manager",
            "specialization": "API Product Manager",
            "tech_stack": ["Jira", "Confluence", "Figma", "SQL", "Python"],
            "question_tags": ["product-management", "technical-pm", "api-strategy", "roadmapping"]
        },
        {
            "main_role": "Product Manager",
            "sub_role": "Growth Product Manager",
            "specialization": "User Acquisition PM",
            "tech_stack": ["Amplitude", "Mixpanel", "Google Analytics", "A/B Testing", "SQL"],
            "question_tags": ["growth-pm", "user-acquisition", "metrics", "experimentation"]
        },
        {
            "main_role": "Product Manager",
            "sub_role": "Platform Product Manager",
            "specialization": "Developer Tools PM",
            "tech_stack": ["Jira", "GitHub", "Postman", "Docker", "Kubernetes"],
            "question_tags": ["platform-pm", "developer-tools", "apis", "infrastructure"]
        },
        {
            "main_role": "Product Manager",
            "sub_role": "Consumer Product Manager",
            "specialization": "Mobile Product Manager",
            "tech_stack": ["Figma", "App Store Connect", "Firebase", "Amplitude", "UserVoice"],
            "question_tags": ["consumer-pm", "mobile-products", "user-experience", "app-strategy"]
        },
        
        # DevOps Engineer roles
        {
            "main_role": "DevOps Engineer",
            "sub_role": "Site Reliability Engineer",
            "specialization": "Platform SRE",
            "tech_stack": ["Kubernetes", "Docker", "Prometheus", "Grafana", "Terraform"],
            "question_tags": ["sre", "reliability", "monitoring", "incident-response"]
        },
        {
            "main_role": "DevOps Engineer",
            "sub_role": "Cloud Engineer",
            "specialization": "AWS Solutions Architect",
            "tech_stack": ["AWS", "Terraform", "CloudFormation", "Docker", "Kubernetes"],
            "question_tags": ["cloud-engineering", "aws", "infrastructure", "scalability"]
        },
        {
            "main_role": "DevOps Engineer",
            "sub_role": "Cloud Engineer",
            "specialization": "Azure DevOps Engineer",
            "tech_stack": ["Azure", "Azure DevOps", "ARM Templates", "PowerShell", "Terraform"],
            "question_tags": ["azure", "devops", "ci-cd", "infrastructure-as-code"]
        },
        {
            "main_role": "DevOps Engineer",
            "sub_role": "Security Engineer",
            "specialization": "DevSecOps Engineer",
            "tech_stack": ["Docker", "Kubernetes", "Vault", "SAST Tools", "DAST Tools"],
            "question_tags": ["devsecops", "security", "compliance", "vulnerability-management"]
        },
        {
            "main_role": "DevOps Engineer",
            "sub_role": "Infrastructure Engineer",
            "specialization": "Network Engineer",
            "tech_stack": ["Terraform", "Ansible", "Cisco", "Linux", "Networking"],
            "question_tags": ["infrastructure", "networking", "automation", "systems-administration"]
        },
        
        # UX/UI Designer roles
        {
            "main_role": "UX/UI Designer",
            "sub_role": "UX Designer",
            "specialization": "User Researcher",
            "tech_stack": ["Figma", "Sketch", "Adobe XD", "Miro", "UserTesting"],
            "question_tags": ["ux-design", "user-research", "usability", "design-thinking"]
        },
        {
            "main_role": "UX/UI Designer",
            "sub_role": "UI Designer",
            "specialization": "Visual Designer",
            "tech_stack": ["Figma", "Adobe Creative Suite", "Sketch", "Principle", "Framer"],
            "question_tags": ["ui-design", "visual-design", "prototyping", "design-systems"]
        },
        {
            "main_role": "UX/UI Designer",
            "sub_role": "Product Designer",
            "specialization": "Design Systems Designer",
            "tech_stack": ["Figma", "Storybook", "Abstract", "Zeplin", "InVision"],
            "question_tags": ["product-design", "design-systems", "component-libraries", "design-ops"]
        },
        {
            "main_role": "UX/UI Designer",
            "sub_role": "Interaction Designer",
            "specialization": "Motion Designer",
            "tech_stack": ["After Effects", "Principle", "Framer", "Lottie", "Figma"],
            "question_tags": ["interaction-design", "motion-design", "micro-interactions", "animation"]
        },
        
        # Cybersecurity Specialist roles
        {
            "main_role": "Cybersecurity Specialist",
            "sub_role": "Security Analyst",
            "specialization": "SOC Analyst",
            "tech_stack": ["SIEM Tools", "Splunk", "Wireshark", "Nessus", "Metasploit"],
            "question_tags": ["security-analysis", "soc", "incident-response", "threat-hunting"]
        },
        {
            "main_role": "Cybersecurity Specialist",
            "sub_role": "Penetration Tester",
            "specialization": "Web Application Tester",
            "tech_stack": ["Burp Suite", "OWASP ZAP", "Metasploit", "Nmap", "Kali Linux"],
            "question_tags": ["penetration-testing", "web-security", "vulnerability-assessment", "ethical-hacking"]
        },
        {
            "main_role": "Cybersecurity Specialist",
            "sub_role": "Security Engineer",
            "specialization": "Application Security Engineer",
            "tech_stack": ["SAST Tools", "DAST Tools", "Docker", "Kubernetes", "Security Frameworks"],
            "question_tags": ["application-security", "secure-coding", "security-architecture", "compliance"]
        },
        {
            "main_role": "Cybersecurity Specialist",
            "sub_role": "Compliance Officer",
            "specialization": "GDPR Compliance Specialist",
            "tech_stack": ["GRC Tools", "Risk Assessment", "Audit Tools", "Documentation", "Training"],
            "question_tags": ["compliance", "gdpr", "risk-management", "audit", "governance"]
        },
        
        # Business Analyst roles
        {
            "main_role": "Business Analyst",
            "sub_role": "Systems Analyst",
            "specialization": "ERP Analyst",
            "tech_stack": ["SQL", "Excel", "Tableau", "SAP", "Oracle"],
            "question_tags": ["systems-analysis", "erp", "business-processes", "requirements-gathering"]
        },
        {
            "main_role": "Business Analyst",
            "sub_role": "Data Analyst",
            "specialization": "Financial Analyst",
            "tech_stack": ["Excel", "SQL", "Tableau", "Power BI", "Python"],
            "question_tags": ["financial-analysis", "data-analysis", "reporting", "forecasting"]
        },
        {
            "main_role": "Business Analyst",
            "sub_role": "Process Analyst",
            "specialization": "Workflow Optimization Specialist",
            "tech_stack": ["Visio", "Lucidchart", "Process Mining Tools", "Six Sigma", "Lean"],
            "question_tags": ["process-analysis", "workflow-optimization", "business-improvement", "lean-six-sigma"]
        },
        {
            "main_role": "Business Analyst",
            "sub_role": "Requirements Analyst",
            "specialization": "Agile Business Analyst",
            "tech_stack": ["Jira", "Confluence", "User Story Mapping", "Wireframing Tools", "SQL"],
            "question_tags": ["requirements-analysis", "agile", "user-stories", "stakeholder-management"]
        },
        
        # Sales Representative roles
        {
            "main_role": "Sales Representative",
            "sub_role": "Inside Sales",
            "specialization": "SaaS Sales Specialist",
            "tech_stack": ["Salesforce", "HubSpot", "Outreach", "LinkedIn Sales Navigator", "Zoom"],
            "question_tags": ["inside-sales", "saas-sales", "lead-generation", "crm"]
        },
        {
            "main_role": "Sales Representative",
            "sub_role": "Field Sales",
            "specialization": "Enterprise Sales Manager",
            "tech_stack": ["Salesforce", "Microsoft Dynamics", "DocuSign", "Proposal Software", "CRM"],
            "question_tags": ["field-sales", "enterprise-sales", "relationship-building", "negotiation"]
        },
        {
            "main_role": "Sales Representative",
            "sub_role": "Account Manager",
            "specialization": "Customer Success Manager",
            "tech_stack": ["Salesforce", "Gainsight", "ChurnZero", "Intercom", "Analytics Tools"],
            "question_tags": ["account-management", "customer-success", "retention", "upselling"]
        },
        {
            "main_role": "Sales Representative",
            "sub_role": "Sales Development",
            "specialization": "SDR Specialist",
            "tech_stack": ["Outreach", "SalesLoft", "LinkedIn Sales Navigator", "ZoomInfo", "Calendly"],
            "question_tags": ["sales-development", "prospecting", "lead-qualification", "cold-outreach"]
        }
    ]
    
    created_count = 0
    
    for role_data in hierarchy_data:
        try:
            # Check if role combination already exists
            existing = db.query(RoleHierarchy).filter(
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
                    tech_stack=role_data["tech_stack"],
                    question_tags=role_data["question_tags"],
                    version="1.0",
                    is_active=True
                )
                db.add(db_role)
                created_count += 1
                
        except Exception as e:
            continue
    
    db.commit()
    return created_count