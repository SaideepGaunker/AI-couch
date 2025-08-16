Create a .env file in backend/ with the following keys (copy from this template):

APP_NAME=Interview Prep AI Coach
DEBUG=true
DATABASE_URL=mysql+pymysql://root:password@localhost/interview_prep_db
SECRET_KEY=change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ALLOWED_HOSTS=http://localhost:4200,http://localhost:3000
GEMINI_API_KEY=
HUGGINGFACE_API_KEY=
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=no-reply@example.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_TLS=true
MAIL_SSL=false
MAX_FILE_SIZE=10485760
UPLOAD_DIR=uploads

Place this file at backend/.env (same directory as main.py).

