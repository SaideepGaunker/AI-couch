#!/usr/bin/env python3
"""
Automated Database Setup Script for Interview Prep AI Coach
This script will automatically create the database and user for the application.
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
import getpass
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path("backend/.env")
    env_vars = {}
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    return env_vars

def update_env_file(mysql_password):
    """Update .env file with the correct database URL"""
    env_path = Path("backend/.env")
    
    if not env_path.exists():
        print("❌ .env file not found in backend directory!")
        return False
    
    # Read current .env content
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Update DATABASE_URL
    new_database_url = f"mysql+pymysql://root:{mysql_password}@localhost/interview_prep_db"
    
    # Replace the DATABASE_URL line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('DATABASE_URL='):
            lines[i] = f"DATABASE_URL={new_database_url}"
            break
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print("✅ Updated .env file with database credentials")
    return True

def create_database_and_user(mysql_password):
    """Create database and user automatically"""
    try:
        print("🔄 Connecting to MySQL...")
        
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=mysql_password
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            print("✅ Connected to MySQL successfully!")
            
            # Create database
            print("🔄 Creating database 'interview_prep_db'...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS interview_prep_db")
            print("✅ Database 'interview_prep_db' created successfully!")
            
            # Create user (optional - using root for simplicity)
            print("🔄 Setting up database permissions...")
            cursor.execute("FLUSH PRIVILEGES")
            print("✅ Database permissions configured!")
            
            # Show databases to confirm
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            
            db_exists = False
            for db in databases:
                if 'interview_prep_db' in db:
                    db_exists = True
                    break
            
            if db_exists:
                print("✅ Database setup completed successfully!")
                return True
            else:
                print("❌ Database creation failed!")
                return False
                
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        if "Access denied" in str(e):
            print("💡 Please check your MySQL password and try again.")
        return False
        
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def run_database_migrations():
    """Run Alembic migrations to create tables"""
    try:
        print("🔄 Running database migrations...")
        
        # Change to backend directory
        os.chdir("backend")
        
        # Check if virtual environment exists
        if os.path.exists("venv"):
            print("✅ Virtual environment found")
            
            # Activate virtual environment and run migrations
            if os.name == 'nt':  # Windows
                activate_cmd = "venv\\Scripts\\activate && alembic upgrade head"
            else:  # macOS/Linux
                activate_cmd = "source venv/bin/activate && alembic upgrade head"
            
            result = os.system(activate_cmd)
            
            if result == 0:
                print("✅ Database migrations completed successfully!")
                return True
            else:
                print("❌ Database migrations failed!")
                print("💡 You may need to run 'alembic upgrade head' manually in the backend directory")
                return False
        else:
            print("❌ Virtual environment not found!")
            print("💡 Please create virtual environment first: python -m venv venv")
            return False
            
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return False
    finally:
        # Change back to root directory
        os.chdir("..")

def main():
    """Main setup function"""
    print("🚀 Interview Prep AI Coach - Automated Database Setup")
    print("=" * 60)
    
    # Get MySQL password
    mysql_password = getpass.getpass("🔑 Enter your MySQL root password: ")
    
    if not mysql_password:
        print("❌ Password cannot be empty!")
        sys.exit(1)
    
    print("\n📋 Starting automated database setup...")
    
    # Step 1: Update .env file
    print("\n1️⃣ Updating environment configuration...")
    if not update_env_file(mysql_password):
        print("❌ Failed to update .env file!")
        sys.exit(1)
    
    # Step 2: Create database
    print("\n2️⃣ Creating database and user...")
    if not create_database_and_user(mysql_password):
        print("❌ Failed to create database!")
        sys.exit(1)
    
    # Step 3: Run migrations
    print("\n3️⃣ Running database migrations...")
    if not run_database_migrations():
        print("⚠️ Migrations failed, but you can run them manually later")
    
    print("\n🎉 Database setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Get your Gemini API key from: https://makersuite.google.com/app/apikey")
    print("2. Update GEMINI_API_KEY in backend/.env file")
    print("3. Run the application using: start.bat (Windows) or ./start.sh (macOS/Linux)")
    print("\n✅ Your Interview Prep AI Coach is ready to run!")

if __name__ == "__main__":
    main()