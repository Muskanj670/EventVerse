# 🌟 EventVerse – Smart Event Management System

EventVerse is a full-featured event management platform built using Django. It enables users to create, manage, and attend events with ease, offering powerful tools for organizers, attendees, and administrators.

---

## 🚀 Key Highlights

- 🔐 Role-based authentication system
- 📅 Complete event lifecycle management
- 🎟️ Advanced ticketing & registration
- 📊 Analytics dashboard for insights
- 🔎 Smart search and filtering
- 💳 Payment tracking system
- 🔔 Notification system

---

## 👥 User Roles

### 👤 Attendees

- Browse and search events
- Register for events
- View event details and tickets

### 🎯 Organizers

- Create and manage events
- Track registrations and revenue
- Access dashboard analytics

### 🛠️ Admins

- Full system control via admin panel
- Manage users, events, and categories
- Monitor overall platform activity

---

## ⚙️ Features

### 🔐 User Management

- Secure authentication system
- Role-based access control
- Profile management (phone, city)

### 📅 Event Management

- Create, edit, delete events
- Event categories and filtering
- Event status:
  - Draft
  - Published
  - Cancelled
  - Completed
- Image uploads and venue details
- Timezone-aware scheduling

### 🎟️ Ticketing System

- Multiple ticket types per event
- Pricing and capacity limits
- Registration tracking

### 📊 Dashboard & Analytics

- Organizer and admin dashboards
- Event statistics (upcoming, past, revenue)
- Category and monthly insights

### 🔍 Search & Discovery

- Search by title, description, city
- Filter by category and status
- Featured events

### 💳 Payment System

- Transaction ID tracking
- Status:
  - Pending
  - Success
  - Failed
  - Refunded

### 🔔 Notifications

- User notification system
- Read/unread tracking

---

## 🛠️ Tech Stack

- Backend: Django
- Frontend: HTML, CSS, Django Templates
- Database: SQLite
- ORM: Django ORM

---

## 📦 Installation

### Prerequisites

- Python 3.8+
- pip

---

### Setup

```bash
# Clone repository
git clone <repository-url>
cd EventVerse

# Create virtual environment
python -m venv venv

# Activate environment
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install django

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver

# Open in browser:
http://127.0.0.1:8000/

# 📁 Project Structure
EventVerse/
│
├── accounts/        # User authentication
├── core/            # Homepage & search
├── dashboard/       # Analytics
├── events/          # Event management
│
├── templates/       # HTML files
├── static/          # CSS & assets
│
├── EventVerse/      # Settings & URLs
├── db.sqlite3
└── manage.py
```
