"""
Database configuration and session management
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Optimized database engine with proper connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    # Connection pool settings
    poolclass=QueuePool,
    pool_size=20,  # Number of connections to maintain
    max_overflow=30,  # Additional connections beyond pool_size
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections every hour
    pool_timeout=30,  # Timeout for getting connection from pool
    
    # Performance settings
    echo=settings.DEBUG,
    echo_pool=settings.DEBUG,
    
    # Connection arguments for MySQL optimization
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
        "connect_timeout": 60,
        "read_timeout": 30,
        "write_timeout": 30,
    }
)

# Add connection event listeners for optimization
@event.listens_for(engine, "connect")
def set_mysql_pragma(dbapi_connection, connection_record):
    """Set MySQL session variables for optimization"""
    try:
        with dbapi_connection.cursor() as cursor:
            # Optimize MySQL settings
            cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 50")
            cursor.execute("SET SESSION wait_timeout = 28800")
            cursor.execute("SET SESSION interactive_timeout = 28800")
    except Exception as e:
        logger.warning(f"Failed to set MySQL session variables: {e}")

# Create session factory with optimized settings
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Keep objects accessible after commit
)

# Create base class for models
Base = declarative_base()

# Dependency to get database session with proper error handling
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Health check function
def check_database_health():
    """Check if database is accessible"""
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False