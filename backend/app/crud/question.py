"""
CRUD operations for Question model
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.db.models import Question
from app.schemas.question import QuestionCreate


def create_question(db: Session, question: QuestionCreate) -> Question:
    """Create new question (with duplicate check)"""
    # Check for exact duplicate first
    existing = db.query(Question).filter(
        Question.content.ilike(question.content.strip())
    ).first()
    
    if existing:
        raise ValueError(f"Question already exists with ID: {existing.id}")
    
    # Check for similar questions in same role/type
    similar = db.query(Question).filter(
        Question.role_category == question.role_category,
        Question.question_type == question.question_type
    ).all()
    
    # Simple similarity check
    normalized_new = _normalize_content(question.content)
    for existing_q in similar:
        normalized_existing = _normalize_content(existing_q.content)
        if _calculate_text_similarity(normalized_new, normalized_existing) > 0.75:
            raise ValueError(f"Similar question already exists with ID: {existing_q.id}")
    
    db_question = Question(
        content=question.content.strip(),
        question_type=question.question_type,
        role_category=question.role_category,
        difficulty_level=question.difficulty_level,
        expected_duration=question.expected_duration,
        generated_by=question.generated_by
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


def create_question_safe(db: Session, question: QuestionCreate) -> Optional[Question]:
    """Create new question safely (returns None if duplicate)"""
    try:
        return create_question(db, question)
    except ValueError as e:
        if "already exists" in str(e):
            return None
        raise e


def get_question(db: Session, question_id: int) -> Optional[Question]:
    """Get question by ID"""
    return db.query(Question).filter(Question.id == question_id).first()


def get_questions_filtered(
    db: Session,
    role_category: Optional[str] = None,
    question_type: Optional[str] = None,
    difficulty_level: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Question]:
    """Get questions with filtering"""
    query = db.query(Question)
    
    if role_category:
        query = query.filter(Question.role_category == role_category)
    if question_type:
        query = query.filter(Question.question_type == question_type)
    if difficulty_level:
        query = query.filter(Question.difficulty_level == difficulty_level)
    
    return query.offset(offset).limit(limit).all()


def search_questions_by_content(db: Session, search_query: str, limit: int = 20) -> List[Question]:
    """Search questions by content"""
    return db.query(Question).filter(
        Question.content.ilike(f"%{search_query}%")
    ).limit(limit).all()


def update_question(db: Session, question_id: int, update_data: Dict[str, Any]) -> Optional[Question]:
    """Update question"""
    question = get_question(db, question_id)
    if not question:
        return None
    
    for field, value in update_data.items():
        if hasattr(question, field):
            setattr(question, field, value)
    
    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, question_id: int) -> bool:
    """Delete question"""
    question = get_question(db, question_id)
    if not question:
        return False
    
    db.delete(question)
    db.commit()
    return True


def get_questions_by_role(db: Session, role_category: str, limit: int = 10) -> List[Question]:
    """Get questions for specific role"""
    return db.query(Question).filter(
        Question.role_category == role_category
    ).limit(limit).all()


def get_random_questions(
    db: Session,
    role_category: Optional[str] = None,
    question_type: Optional[str] = None,
    difficulty_level: Optional[str] = None,
    count: int = 5
) -> List[Question]:
    """Get random questions with filters"""
    query = db.query(Question)
    
    if role_category:
        query = query.filter(Question.role_category == role_category)
    if question_type:
        query = query.filter(Question.question_type == question_type)
    if difficulty_level:
        query = query.filter(Question.difficulty_level == difficulty_level)
    
    return query.order_by(func.random()).limit(count).all()


def get_question_statistics(db: Session) -> Dict[str, Any]:
    """Get question database statistics"""
    total = db.query(Question).count()
    
    # Group by categories
    role_stats = db.query(
        Question.role_category,
        func.count(Question.id).label('count')
    ).group_by(Question.role_category).all()
    
    type_stats = db.query(
        Question.question_type,
        func.count(Question.id).label('count')
    ).group_by(Question.question_type).all()
    
    difficulty_stats = db.query(
        Question.difficulty_level,
        func.count(Question.id).label('count')
    ).group_by(Question.difficulty_level).all()
    
    return {
        "total": total,
        "by_role": dict(role_stats),
        "by_type": dict(type_stats),
        "by_difficulty": dict(difficulty_stats)
    }


def check_question_duplicate(db: Session, content: str, role_category: str = None, question_type: str = None) -> Optional[Question]:
    """Check if a question already exists (exact or similar)"""
    # Check exact match first
    exact_match = db.query(Question).filter(
        Question.content.ilike(content.strip())
    ).first()
    
    if exact_match:
        return exact_match
    
    # Check similar questions if role/type provided
    if role_category and question_type:
        similar_questions = db.query(Question).filter(
            Question.role_category == role_category,
            Question.question_type == question_type
        ).all()
        
        normalized_new = _normalize_content(content)
        for existing_q in similar_questions:
            normalized_existing = _normalize_content(existing_q.content)
            if _calculate_text_similarity(normalized_new, normalized_existing) > 0.75:
                return existing_q
    
    return None


def _normalize_content(content: str) -> str:
    """Normalize question content for duplicate detection"""
    import re
    
    # Convert to lowercase and strip
    normalized = content.lower().strip()
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Remove punctuation that doesn't affect meaning
    normalized = re.sub(r'[.!?;,]', '', normalized)
    
    # Remove common question starters
    starters = [
        'can you ', 'could you ', 'would you ', 'will you ',
        'please ', 'tell me ', 'describe ', 'explain ',
        'what is ', 'what are ', 'how do ', 'how would ',
        'why do ', 'why would ', 'when do ', 'where do '
    ]
    
    for starter in starters:
        if normalized.startswith(starter):
            normalized = normalized[len(starter):]
            break
    
    return normalized.strip()


def _calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts using multiple methods"""
    if not text1 or not text2:
        return 0.0
    
    # Method 1: Word-based Jaccard similarity
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    jaccard_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
    
    # Method 2: Character-based similarity (for catching minor variations)
    # Remove spaces and compare character sets
    chars1 = set(text1.replace(' ', ''))
    chars2 = set(text2.replace(' ', ''))
    char_similarity = len(chars1.intersection(chars2)) / len(chars1.union(chars2)) if chars1.union(chars2) else 0
    
    # Method 3: Length-based similarity check
    len1, len2 = len(text1), len(text2)
    length_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 0
    
    # Method 4: Common substring check
    # Check if one text contains most of the other
    shorter, longer = (text1, text2) if len1 < len2 else (text2, text1)
    substring_ratio = 0
    if len(shorter) > 10:  # Only for meaningful length texts
        # Count how many words from shorter text appear in longer text
        shorter_words = shorter.split()
        longer_words = longer.split()
        common_words = sum(1 for word in shorter_words if word in longer_words)
        substring_ratio = common_words / len(shorter_words) if shorter_words else 0
    
    # Combine similarities with weights
    # Jaccard gets highest weight, then substring, then character, then length
    combined_similarity = (
        jaccard_similarity * 0.4 +
        substring_ratio * 0.3 +
        char_similarity * 0.2 +
        length_ratio * 0.1
    )
    
    return combined_similarity