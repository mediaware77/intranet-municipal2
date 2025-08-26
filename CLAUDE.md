# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django 4.2.7 project named "intranet-municipal2" that implements a simple user management CRUD admin panel with SQLite database.

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Database Operations
```bash
# Create new migrations after model changes
python manage.py makemigrations

# Apply migrations to database
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

### Running the Server
```bash
# Start development server (default port 8000)
python manage.py runserver

# Start on alternative port (e.g., 8001)
python manage.py runserver 8001
```

### Django Shell
```bash
# Access Django shell for database operations
python manage.py shell
```

## Architecture

### Core Structure
- **intranet/**: Main Django project configuration
  - `settings.py`: Django settings with SQLite configured, pt-br locale, America/Sao_Paulo timezone
  - `urls.py`: URL routing, currently only admin interface at `/admin/`
  
- **usuarios/**: Main application for user management
  - `models.py`: Contains `Usuario` model with fields: nome, email, telefone, ativo, data_criacao, data_atualizacao
  - `admin.py`: Django Admin configuration with list display, filters, search, and inline editing

### Database
- Uses SQLite3 (file: `db.sqlite3`)
- Single custom model: `Usuario` for user management

### Admin Interface
- Access at `/admin/` 
- Provides full CRUD operations for Usuario model
- Features: search by name/email, filter by status/date, inline editing of 'ativo' field

## Important Notes
- Virtual environment must be activated before running any Django commands
- Default admin credentials created: username=`admin`, password=`admin123`
- Port 8000 might be occupied, use alternative ports like 8001 if needed