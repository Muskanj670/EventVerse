# EventVerse

EventVerse is a Django-based event management system for attendees, organizers, and admins. It supports event discovery, event publishing, organizer analytics, seat booking, attendee booking history, and media-rich event pages with image/video carousels.

## What the Project Does

- Attendees can browse published events, search by keyword, filter by category/city, view attendee-focused event details, book seats, and review booking history from their profile page.
- Organizers can create, edit, and delete events, add multiple images and videos for a carousel, share a Google Maps venue link, set event capacity and price, and use either an existing category or a custom one.
- Admins inherit organizer visibility and can manage platform data through Django admin.

## Core Features

- Role-based authentication with attendee, organizer, and admin flows
- Public event listing, featured events, search, and filtering
- Event creation and editing with title, description, venue, city, schedule, capacity, price, status, Google Maps venue link, and multiple image/video uploads
- Existing or custom category creation during event setup
- Event detail carousel for uploaded media
- Seat availability tracking based on confirmed bookings
- Seat booking from the attendee-facing event detail page
- Profile page with booking history and total booked seats
- Organizer/admin dashboard with event analytics and managed event listings
- Admin support for categories, events, event media, tickets, registrations, payments, and notifications

## Apps and Responsibilities

- `accounts/`: signup, login, logout, profile roles, email validation, and booking history page
- `core/`: home page and search
- `dashboard/`: organizer/admin analytics and event management summary
- `events/`: events, categories, media gallery, ticket defaults, registrations, payments, and notifications
- `EventVerse/`: settings and root URL configuration

## Directory Overview

```text
EventVerse/
|-- EventVerse/                Django project settings and URL config
|-- accounts/                  Authentication, profiles, and profile page
|-- core/                      Home page and search
|-- dashboard/                 Organizer/admin analytics
|-- events/                    Events, media, booking, payments, notifications
|-- static/
|   `-- css/                   Shared styling
|-- templates/
|   |-- accounts/              Login, signup, profile
|   |-- core/                  Home and search pages
|   |-- dashboard/             Dashboard UI
|   |-- events/                Event list/detail/form/delete pages
|   `-- partials/              Shared pagination partial
|-- build.sh                   Deployment/build helper
|-- db.sqlite3                 SQLite database
|-- manage.py                  Django management entry point
|-- README.md
`-- requirements.txt
```

## Data Model Summary

- `Category`: reusable event categories
- `Event`: main event record with organizer, schedule, capacity, pricing, status, Google Maps URL, and legacy cover image support
- `EventMedia`: multiple uploaded image/video assets for each event
- `Ticket`: default `General Admission` ticket synced to event capacity and price
- `Registration`: attendee bookings, booking status, and number of seats booked
- `Payment`: payment metadata for future or extended payment workflows
- `Notification`: in-app notification records
- `UserProfile`: attendee/organizer role, phone, city, and profile metadata

## Tech Stack

- Python
- Django 6
- SQLite
- Django Templates
- Bootstrap 5
- Pillow
- WhiteNoise

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Apply migrations:

```bash
python manage.py migrate
```

4. Create an admin user if needed:

```bash
python manage.py createsuperuser
```

5. Start the development server:

```bash
python manage.py runserver
```

6. Open `http://127.0.0.1:8000/`

## Test Suite

Run the project tests with:

```bash
python manage.py test
```

## Notes

- Media uploads are served through Django in development when `DEBUG=True`.
- Published events are visible to attendees; organizers/admins can also manage draft, cancelled, and completed events.
- Existing single-image events still render correctly, while newly uploaded image/video sets appear as a carousel.
