#!/usr/bin/env python3
"""
Learning Resources Seed Data Script
Populates the learning_resources table with comprehensive data
"""
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import LearningResource
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Learning resources data organized by category and difficulty
LEARNING_RESOURCES = [
    # BEHAVIORAL INTERVIEW RESOURCES
    # Beginner Level
    {
        "title": "STAR Method Basics for Behavioral Interviews",
        "description": "Learn the fundamental STAR (Situation, Task, Action, Result) method for answering behavioral questions effectively.",
        "type": "video",
        "category": "behavioral",
        "difficulty_level": "beginner",
        "provider": "YouTube",
        "url": "https://www.youtube.com/watch?v=example1",
        "duration_minutes": 15,
        "ranking_weight": 0.9,
        "tags": ["star-method", "behavioral", "basics", "interview-prep"]
    },
    {
        "title": "Common Behavioral Interview Questions and Answers",
        "description": "Comprehensive guide to the most frequently asked behavioral interview questions with sample answers.",
        "type": "article",
        "category": "behavioral",
        "difficulty_level": "beginner",
        "provider": "LinkedIn Learning",
        "url": "https://www.linkedin.com/learning/example1",
        "duration_minutes": 30,
        "ranking_weight": 0.85,
        "tags": ["behavioral-questions", "sample-answers", "preparation"]
    },
    {
        "title": "Behavioral Interview Preparation Course",
        "description": "Complete course covering all aspects of behavioral interviews from preparation to execution.",
        "type": "course",
        "category": "behavioral",
        "difficulty_level": "beginner",
        "provider": "Coursera",
        "url": "https://www.coursera.org/learn/behavioral-interviews",
        "duration_minutes": 120,
        "ranking_weight": 0.95,
        "tags": ["comprehensive", "behavioral", "course", "certification"]
    },
    {
        "title": "Body Language in Interviews",
        "description": "Master non-verbal communication and body language techniques for successful interviews.",
        "type": "video",
        "category": "behavioral",
        "difficulty_level": "beginner",
        "provider": "Udemy",
        "url": "https://www.udemy.com/course/body-language-interviews",
        "duration_minutes": 45,
        "ranking_weight": 0.8,
        "tags": ["body-language", "non-verbal", "communication"]
    },
    {
        "title": "Interview Confidence Building",
        "description": "Techniques and strategies to build confidence and reduce anxiety during interviews.",
        "type": "article",
        "category": "behavioral",
        "difficulty_level": "beginner",
        "provider": "Harvard Business Review",
        "url": "https://hbr.org/interview-confidence",
        "duration_minutes": 20,
        "ranking_weight": 0.75,
        "tags": ["confidence", "anxiety", "mindset", "preparation"]
    },

    # Intermediate Level
    {
        "title": "Advanced STAR Method Techniques",
        "description": "Advanced strategies for using the STAR method in complex behavioral scenarios and leadership questions.",
        "type": "course",
        "category": "behavioral",
        "difficulty_level": "intermediate",
        "provider": "LinkedIn Learning",
        "url": "https://www.linkedin.com/learning/advanced-star-method",
        "duration_minutes": 90,
        "ranking_weight": 0.9,
        "tags": ["advanced-star", "leadership", "complex-scenarios"]
    },
    {
        "title": "Handling Difficult Behavioral Questions",
        "description": "Strategies for answering challenging behavioral questions about failures, conflicts, and weaknesses.",
        "type": "video",
        "category": "behavioral",
        "difficulty_level": "intermediate",
        "provider": "YouTube",
        "url": "https://www.youtube.com/watch?v=difficult-questions",
        "duration_minutes": 25,
        "ranking_weight": 0.85,
        "tags": ["difficult-questions", "failures", "conflicts", "weaknesses"]
    },
    {
        "title": "Leadership Behavioral Interview Guide",
        "description": "Comprehensive guide for answering leadership-focused behavioral questions with real examples.",
        "type": "article",
        "category": "behavioral",
        "difficulty_level": "intermediate",
        "provider": "McKinsey & Company",
        "url": "https://www.mckinsey.com/leadership-interviews",
        "duration_minutes": 35,
        "ranking_weight": 0.95,
        "tags": ["leadership", "management", "team-building"]
    },
    {
        "title": "Cultural Fit Interview Preparation",
        "description": "Understanding company culture and preparing for culture-fit behavioral questions.",
        "type": "course",
        "category": "behavioral",
        "difficulty_level": "intermediate",
        "provider": "Coursera",
        "url": "https://www.coursera.org/learn/cultural-fit",
        "duration_minutes": 60,
        "ranking_weight": 0.8,
        "tags": ["cultural-fit", "company-culture", "values"]
    },
    {
        "title": "Storytelling for Interviews",
        "description": "Master the art of storytelling to make your behavioral interview answers more compelling and memorable.",
        "type": "video",
        "category": "behavioral",
        "difficulty_level": "intermediate",
        "provider": "TED-Ed",
        "url": "https://ed.ted.com/storytelling-interviews",
        "duration_minutes": 18,
        "ranking_weight": 0.75,
        "tags": ["storytelling", "narrative", "compelling-answers"]
    },

    # Advanced Level
    {
        "title": "Executive-Level Behavioral Interviews",
        "description": "Advanced behavioral interview techniques for C-suite and executive positions.",
        "type": "course",
        "category": "behavioral",
        "difficulty_level": "advanced",
        "provider": "Harvard Business School",
        "url": "https://www.hbs.edu/executive-interviews",
        "duration_minutes": 180,
        "ranking_weight": 0.95,
        "tags": ["executive", "c-suite", "senior-leadership"]
    },
    {
        "title": "Crisis Management Interview Questions",
        "description": "How to handle behavioral questions about crisis management, decision-making under pressure, and strategic thinking.",
        "type": "article",
        "category": "behavioral",
        "difficulty_level": "advanced",
        "provider": "MIT Sloan",
        "url": "https://mitsloan.mit.edu/crisis-management-interviews",
        "duration_minutes": 40,
        "ranking_weight": 0.9,
        "tags": ["crisis-management", "pressure", "strategic-thinking"]
    },
    {
        "title": "Board-Level Interview Preparation",
        "description": "Specialized preparation for board member and director-level behavioral interviews.",
        "type": "video",
        "category": "behavioral",
        "difficulty_level": "advanced",
        "provider": "Wharton Executive Education",
        "url": "https://executiveeducation.wharton.upenn.edu/board-interviews",
        "duration_minutes": 75,
        "ranking_weight": 0.85,
        "tags": ["board-level", "director", "governance"]
    },
    {
        "title": "International Business Behavioral Interviews",
        "description": "Cultural considerations and strategies for behavioral interviews in international business contexts.",
        "type": "course",
        "category": "behavioral",
        "difficulty_level": "advanced",
        "provider": "INSEAD",
        "url": "https://www.insead.edu/international-interviews",
        "duration_minutes": 120,
        "ranking_weight": 0.8,
        "tags": ["international", "cross-cultural", "global-business"]
    },
    {
        "title": "Mergers & Acquisitions Interview Scenarios",
        "description": "Advanced behavioral scenarios related to M&A, restructuring, and organizational change.",
        "type": "article",
        "category": "behavioral",
        "difficulty_level": "advanced",
        "provider": "Bain & Company",
        "url": "https://www.bain.com/ma-interviews",
        "duration_minutes": 50,
        "ranking_weight": 0.75,
        "tags": ["mergers", "acquisitions", "change-management"]
    },

    # TECHNICAL INTERVIEW RESOURCES
    # Beginner Level
    {
        "title": "Programming Interview Fundamentals",
        "description": "Essential programming concepts and problem-solving techniques for technical interviews.",
        "type": "course",
        "category": "technical",
        "difficulty_level": "beginner",
        "provider": "Codecademy",
        "url": "https://www.codecademy.com/programming-interviews",
        "duration_minutes": 150,
        "ranking_weight": 0.95,
        "tags": ["programming", "algorithms", "data-structures", "fundamentals"]
    },
    {
        "title": "Data Structures and Algorithms Basics",
        "description": "Introduction to essential data structures and algorithms commonly asked in technical interviews.",
        "type": "video",
        "category": "technical",
        "difficulty_level": "beginner",
        "provider": "YouTube",
        "url": "https://www.youtube.com/playlist?list=data-structures-basics",
        "duration_minutes": 120,
        "ranking_weight": 0.9,
        "tags": ["data-structures", "algorithms", "arrays", "linked-lists"]
    },
    {
        "title": "SQL Interview Questions for Beginners",
        "description": "Common SQL queries and database concepts frequently tested in technical interviews.",
        "type": "article",
        "category": "technical",
        "difficulty_level": "beginner",
        "provider": "W3Schools",
        "url": "https://www.w3schools.com/sql/sql_interview.asp",
        "duration_minutes": 45,
        "ranking_weight": 0.85,
        "tags": ["sql", "database", "queries", "joins"]
    },
    {
        "title": "JavaScript Coding Interview Prep",
        "description": "JavaScript-specific coding problems and solutions for web development interviews.",
        "type": "course",
        "category": "technical",
        "difficulty_level": "beginner",
        "provider": "freeCodeCamp",
        "url": "https://www.freecodecamp.org/javascript-interviews",
        "duration_minutes": 180,
        "ranking_weight": 0.8,
        "tags": ["javascript", "web-development", "coding-problems"]
    },
    {
        "title": "System Design Interview Basics",
        "description": "Introduction to system design concepts and basic architecture patterns for interviews.",
        "type": "video",
        "category": "technical",
        "difficulty_level": "beginner",
        "provider": "Educative",
        "url": "https://www.educative.io/system-design-basics",
        "duration_minutes": 90,
        "ranking_weight": 0.75,
        "tags": ["system-design", "architecture", "scalability", "basics"]
    },

    # Intermediate Level
    {
        "title": "Advanced Algorithms and Complexity Analysis",
        "description": "Deep dive into advanced algorithms, time complexity, and space complexity analysis.",
        "type": "course",
        "category": "technical",
        "difficulty_level": "intermediate",
        "provider": "MIT OpenCourseWare",
        "url": "https://ocw.mit.edu/advanced-algorithms",
        "duration_minutes": 300,
        "ranking_weight": 0.95,
        "tags": ["advanced-algorithms", "complexity", "optimization"]
    },
    {
        "title": "Dynamic Programming Interview Problems",
        "description": "Comprehensive guide to dynamic programming problems commonly asked in technical interviews.",
        "type": "article",
        "category": "technical",
        "difficulty_level": "intermediate",
        "provider": "GeeksforGeeks",
        "url": "https://www.geeksforgeeks.org/dynamic-programming",
        "duration_minutes": 120,
        "ranking_weight": 0.9,
        "tags": ["dynamic-programming", "optimization", "recursion"]
    },
    {
        "title": "System Design: Scalable Web Applications",
        "description": "Design scalable web applications covering load balancing, caching, and database sharding.",
        "type": "video",
        "category": "technical",
        "difficulty_level": "intermediate",
        "provider": "System Design Interview",
        "url": "https://www.systemdesigninterview.com/scalable-apps",
        "duration_minutes": 150,
        "ranking_weight": 0.85,
        "tags": ["system-design", "scalability", "load-balancing", "caching"]
    },
    {
        "title": "Machine Learning Interview Preparation",
        "description": "ML algorithms, model evaluation, and practical implementation questions for data science roles.",
        "type": "course",
        "category": "technical",
        "difficulty_level": "intermediate",
        "provider": "Coursera",
        "url": "https://www.coursera.org/learn/ml-interviews",
        "duration_minutes": 240,
        "ranking_weight": 0.8,
        "tags": ["machine-learning", "data-science", "algorithms", "statistics"]
    },
    {
        "title": "API Design and RESTful Services",
        "description": "Best practices for designing APIs and RESTful web services in technical interviews.",
        "type": "article",
        "category": "technical",
        "difficulty_level": "intermediate",
        "provider": "REST API Tutorial",
        "url": "https://restapitutorial.com/interview-prep",
        "duration_minutes": 60,
        "ranking_weight": 0.75,
        "tags": ["api-design", "rest", "web-services", "http"]
    },

    # Advanced Level
    {
        "title": "Distributed Systems Design",
        "description": "Advanced system design covering distributed systems, microservices, and fault tolerance.",
        "type": "course",
        "category": "technical",
        "difficulty_level": "advanced",
        "provider": "Stanford Online",
        "url": "https://online.stanford.edu/distributed-systems",
        "duration_minutes": 400,
        "ranking_weight": 0.95,
        "tags": ["distributed-systems", "microservices", "fault-tolerance"]
    },
    {
        "title": "Advanced Data Engineering Concepts",
        "description": "Big data processing, stream processing, and data pipeline design for senior engineering roles.",
        "type": "video",
        "category": "technical",
        "difficulty_level": "advanced",
        "provider": "DataCamp",
        "url": "https://www.datacamp.com/advanced-data-engineering",
        "duration_minutes": 300,
        "ranking_weight": 0.9,
        "tags": ["data-engineering", "big-data", "stream-processing", "pipelines"]
    },
    {
        "title": "Security Architecture Interview Guide",
        "description": "Cybersecurity principles, threat modeling, and secure system design for security roles.",
        "type": "article",
        "category": "technical",
        "difficulty_level": "advanced",
        "provider": "OWASP",
        "url": "https://owasp.org/security-interviews",
        "duration_minutes": 180,
        "ranking_weight": 0.85,
        "tags": ["cybersecurity", "threat-modeling", "secure-design"]
    },
    {
        "title": "Cloud Architecture Patterns",
        "description": "Advanced cloud architecture patterns, serverless computing, and multi-cloud strategies.",
        "type": "course",
        "category": "technical",
        "difficulty_level": "advanced",
        "provider": "AWS Training",
        "url": "https://aws.amazon.com/training/cloud-architecture",
        "duration_minutes": 360,
        "ranking_weight": 0.8,
        "tags": ["cloud-architecture", "serverless", "aws", "multi-cloud"]
    },
    {
        "title": "Performance Optimization and Profiling",
        "description": "Advanced techniques for performance optimization, profiling, and scalability engineering.",
        "type": "video",
        "category": "technical",
        "difficulty_level": "advanced",
        "provider": "Google Developers",
        "url": "https://developers.google.com/performance-optimization",
        "duration_minutes": 200,
        "ranking_weight": 0.75,
        "tags": ["performance", "optimization", "profiling", "scalability"]
    },

    # HR INTERVIEW RESOURCES
    # Beginner Level
    {
        "title": "HR Interview Basics: What to Expect",
        "description": "Complete guide to HR interview process, common questions, and professional etiquette.",
        "type": "article",
        "category": "hr",
        "difficulty_level": "beginner",
        "provider": "Indeed Career Guide",
        "url": "https://www.indeed.com/career-advice/hr-interviews",
        "duration_minutes": 25,
        "ranking_weight": 0.9,
        "tags": ["hr-basics", "interview-process", "etiquette", "preparation"]
    },
    {
        "title": "Salary Negotiation for Beginners",
        "description": "Learn how to research, prepare for, and conduct salary negotiations effectively.",
        "type": "video",
        "category": "hr",
        "difficulty_level": "beginner",
        "provider": "Harvard Business Review",
        "url": "https://hbr.org/salary-negotiation-basics",
        "duration_minutes": 30,
        "ranking_weight": 0.85,
        "tags": ["salary-negotiation", "compensation", "benefits"]
    },
    {
        "title": "Professional References and Background Checks",
        "description": "How to prepare references and what to expect during background verification processes.",
        "type": "article",
        "category": "hr",
        "difficulty_level": "beginner",
        "provider": "LinkedIn",
        "url": "https://www.linkedin.com/advice/references-background-checks",
        "duration_minutes": 20,
        "ranking_weight": 0.8,
        "tags": ["references", "background-checks", "verification"]
    },
    {
        "title": "Company Research and Culture Fit",
        "description": "Strategies for researching companies and demonstrating cultural alignment during interviews.",
        "type": "course",
        "category": "hr",
        "difficulty_level": "beginner",
        "provider": "Glassdoor",
        "url": "https://www.glassdoor.com/company-research-guide",
        "duration_minutes": 45,
        "ranking_weight": 0.75,
        "tags": ["company-research", "culture-fit", "preparation"]
    },
    {
        "title": "Interview Follow-up Best Practices",
        "description": "Professional follow-up strategies and thank-you note templates for after interviews.",
        "type": "video",
        "category": "hr",
        "difficulty_level": "beginner",
        "provider": "CareerBuilder",
        "url": "https://www.careerbuilder.com/interview-follow-up",
        "duration_minutes": 15,
        "ranking_weight": 0.7,
        "tags": ["follow-up", "thank-you-notes", "professional-communication"]
    }
]


def seed_learning_resources():
    """Seed the learning_resources table with comprehensive data"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if resources already exist
        existing_count = db.query(LearningResource).count()
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing learning resources. Skipping seed.")
            return
        
        logger.info("Starting to seed learning resources...")
        
        # Create learning resources
        resources_created = 0
        for resource_data in LEARNING_RESOURCES:
            try:
                resource = LearningResource(**resource_data)
                db.add(resource)
                resources_created += 1
                
                if resources_created % 10 == 0:
                    logger.info(f"Created {resources_created} resources...")
                    
            except Exception as e:
                logger.error(f"Error creating resource '{resource_data.get('title', 'Unknown')}': {str(e)}")
                continue
        
        # Commit all resources
        db.commit()
        logger.info(f"Successfully seeded {resources_created} learning resources")
        
        # Verify seeding
        total_count = db.query(LearningResource).count()
        logger.info(f"Total learning resources in database: {total_count}")
        
        # Show breakdown by category and difficulty
        categories = db.query(LearningResource.category).distinct().all()
        for (category,) in categories:
            category_count = db.query(LearningResource).filter(
                LearningResource.category == category
            ).count()
            logger.info(f"  {category}: {category_count} resources")
            
            # Breakdown by difficulty within category
            difficulties = db.query(LearningResource.difficulty_level).filter(
                LearningResource.category == category
            ).distinct().all()
            
            for (difficulty,) in difficulties:
                diff_count = db.query(LearningResource).filter(
                    LearningResource.category == category,
                    LearningResource.difficulty_level == difficulty
                ).count()
                logger.info(f"    {difficulty}: {diff_count} resources")
        
    except Exception as e:
        logger.error(f"Error seeding learning resources: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def verify_seed_data():
    """Verify the integrity of seeded data"""
    
    db = next(get_db())
    
    try:
        logger.info("Verifying seed data integrity...")
        
        # Check total count
        total_resources = db.query(LearningResource).count()
        expected_count = len(LEARNING_RESOURCES)
        
        if total_resources != expected_count:
            logger.warning(f"Expected {expected_count} resources, found {total_resources}")
        else:
            logger.info(f"✓ Total resource count matches: {total_resources}")
        
        # Check required fields
        resources_with_missing_fields = db.query(LearningResource).filter(
            (LearningResource.title.is_(None)) |
            (LearningResource.category.is_(None)) |
            (LearningResource.difficulty_level.is_(None)) |
            (LearningResource.type.is_(None))
        ).count()
        
        if resources_with_missing_fields > 0:
            logger.warning(f"Found {resources_with_missing_fields} resources with missing required fields")
        else:
            logger.info("✓ All resources have required fields")
        
        # Check URL validity (basic check)
        resources_with_invalid_urls = db.query(LearningResource).filter(
            ~LearningResource.url.like('http%')
        ).count()
        
        if resources_with_invalid_urls > 0:
            logger.warning(f"Found {resources_with_invalid_urls} resources with potentially invalid URLs")
        else:
            logger.info("✓ All resources have valid URL format")
        
        # Check ranking weights
        resources_with_invalid_weights = db.query(LearningResource).filter(
            (LearningResource.ranking_weight < 0) |
            (LearningResource.ranking_weight > 1)
        ).count()
        
        if resources_with_invalid_weights > 0:
            logger.warning(f"Found {resources_with_invalid_weights} resources with invalid ranking weights")
        else:
            logger.info("✓ All ranking weights are valid (0-1)")
        
        logger.info("Seed data verification completed")
        
    except Exception as e:
        logger.error(f"Error verifying seed data: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed learning resources data")
    parser.add_argument("--verify", action="store_true", help="Verify seed data integrity")
    parser.add_argument("--force", action="store_true", help="Force re-seeding (delete existing data)")
    
    args = parser.parse_args()
    
    if args.verify:
        verify_seed_data()
    else:
        if args.force:
            # Delete existing data
            db = next(get_db())
            try:
                deleted_count = db.query(LearningResource).delete()
                db.commit()
                logger.info(f"Deleted {deleted_count} existing learning resources")
            except Exception as e:
                logger.error(f"Error deleting existing data: {str(e)}")
                db.rollback()
            finally:
                db.close()
        
        seed_learning_resources()
        verify_seed_data()