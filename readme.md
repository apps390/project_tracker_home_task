# Project Tracker - Django REST API

## Overview
A comprehensive project and task management system built with Django REST Framework featuring role-based access control, JWT authentication, and email-based user verification.

## Technology Stack
- Backend Framework: Django 5.2.7
- REST API: Django REST Framework 3.16.1
- Authentication: JWT (djangorestframework-simplejwt 5.5.1)
- Database: PostgreSQL (psycopg2-binary 2.9.11)
- Task Queue: Celery 5.5.3 with Redis 7.0.1
- Caching: Redis with django-redis 6.0.0
- CORS: django-cors-headers 4.9.0

## Prerequisites
- Python 3.8+
- PostgreSQL 12+ (with database and user created)
- Redis Server
- SMTP Server (for email functionality)

## Installation and Setup

### 1. Database Configuration
Create a PostgreSQL database and update your Django settings:

```
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'project_tracker',
        'USER': 'project_user',
        'PASSWORD': 'your_secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 2. Environment Setup
```
# Clone the repository
git clone <repository-url>
cd project-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### 3. Redis and Celery Setup
```
# Start Redis server
redis-server

# Start Celery worker (in separate terminal)
celery -A your_project_name worker --loglevel=info

# Start Celery beat for scheduled tasks (optional)
celery -A your_project_name beat --loglevel=info
```

## Project Management System

### Core Models
- **Project**: Main project entity with status tracking and member management
- **Task**: Individual tasks within projects with assignment capabilities
- **Contributor**: User profile extending base user model with project relationships
- **ProjectInvite**: Invitation system for adding members to projects

### Key Features
- Role-based project access (Manager/Member)
- Project invitation system with email notifications
- Task assignment and status tracking
- Automated overdue status detection
- Soft delete functionality for data integrity
- Caching for improved performance
- Real-time cache invalidation using Django signals
- Automated email notifications for overdue projects and tasks

## API Endpoints

### Authentication Endpoints
- POST /api/auth/send-otp/ - Send OTP to email for verification
- POST /api/auth/verify-otp/ - Verify OTP and generate email token
- POST /api/auth/register/manager/ - Register new manager account
- POST /api/auth/login/ - User login with email/password
- POST /api/auth/token/refresh/ - Refresh JWT access token

### Project Management Endpoints
- POST /api/projects/create/ - Create new project (Manager only)
- GET/PATCH /api/projects/<slug>/edit/ - Retrieve/Update project details
- DELETE /api/projects/<slug>/delete/ - Soft delete project
- GET /api/projects/ - List user's projects with pagination
- POST /api/projects/<slug>/invite/ - Invite members to project
- GET /api/projects/<slug>/members/ - Get project members list

### Task Management Endpoints
- POST /api/projects/<slug>/tasks/add/ - Create new task
- GET/PATCH /api/tasks/<slug>/edit/ - Retrieve/Update task details
- DELETE /api/tasks/<slug>/delete/ - Soft delete task
- GET /api/projects/<slug>/task_list/ - List project tasks with pagination

### Invitation Endpoints
- POST /api/invites/accept/<token>/ - Accept project invitation and register

## Database Design

### Core Tables
- **CustomUser**: Extended user model with role-based permissions
- **EmailOTP**: OTP storage with expiration and usage tracking
- **Project**: Project management with status and member relationships
- **Task**: Task management with assignment and due date tracking
- **Contributor**: User profile for project participation
- **ProjectInvite**: Invitation system with token-based authentication

### Key Design Decisions
1. **Email as Username**: Eliminates username conflicts and simplifies authentication
2. **Role-Based Access**: Clear separation between Manager and Member permissions
3. **OTP Verification**: Prevents duplicate registrations and ensures email validity
4. **JWT Authentication**: Stateless authentication suitable for REST APIs
5. **PostgreSQL**: Robust relational database with excellent Django support
6. **Soft Delete**: Maintains data integrity while allowing record removal
7. **Slug-based URLs**: User-friendly and SEO-optimized resource identifiers
8. **Caching Strategy**: Redis-based caching with automatic invalidation

## Caching Strategy
- Redis used for session storage and caching
- Project and task list caching with 5-minute timeout
- Automatic cache invalidation using Django signals
- Thread-based asynchronous cache clearing
- Pattern-based cache key management
- Celery task results caching
- OTP temporary storage with automatic expiration

## Automated Features

### Celery Scheduled Tasks
- **Daily Notifications**: Runs at 12:00 AM IST
- **Project Overdue Check**: Runs at 1:00 AM IST
- **Task Overdue Check**: Runs at 1:00 AM IST

### Automated Notifications
- Project overdue status detection and email alerts
- Task due today reminders
- Task overdue notifications
- HTML email templates for professional communication

### Cache Management
- Real-time cache invalidation on data changes
- Asynchronous cache clearing for better performance
- Comprehensive cache pattern matching for related data

## Security Features
- JWT token-based authentication
- Password hashing using Django's built-in hashers
- OTP-based email verification
- CORS configuration for frontend integration
- Role-based permission system
- Project access validation for all operations
- Secure invitation tokens with expiration
- Input validation and error handling

## Environment Variables
Configure the following environment variables:
- DATABASE_URL: PostgreSQL connection string
- REDIS_URL: Redis connection string
- EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD: SMTP settings
- SECRET_KEY: Django secret key
- BASE_URL: Application base URL for invitation links

## URL Structure
```
/
/projects/ - Projects management interface
/tasks/ - Tasks management interface  
/invite_register/ - Invitation acceptance page
/api/ - REST API endpoints
/api/auth/ - Authentication endpoints
/admin/ - Django admin interface
```

## Usage Notes
- Managers have full CRUD permissions for projects and tasks
- Members can view and update assigned tasks
- Project invitations expire after 48 hours
- All delete operations are soft deletes for data preservation
- API responses follow consistent JSON format with success/error handling
- Automated email notifications for project and task deadlines
- Real-time cache ensures optimal performance
- Scheduled tasks run daily for maintenance and notifications

## Monitoring and Logging
- Comprehensive logging for all operations
- Error tracking and exception handling
- Performance monitoring through cache metrics
- Email notification delivery tracking

This complete system provides a robust project management solution with automated notifications, efficient caching, and secure access control.