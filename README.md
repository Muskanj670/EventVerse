# EventVerse

EventVerse is a Django-based event management system for discovering events, publishing them, managing bookings, and tracking organizer/admin analytics. The project supports three user perspectives:

- `Attendee`: signs up with email OTP verification, browses events, books seats, manages reminders, and reviews booking history.
- `Organizer`: creates and manages events, uploads event media, and monitors event performance.
- `Admin`: has organizer-level visibility plus platform-wide analytics, data oversight, and CSV export support.

## Project Overview

The application is built as a multi-app Django project with separate concerns for authentication, public pages, event management, and dashboards. It includes:

- Email OTP-based signup and email verification
- Role-aware account and profile flows
- Login form password show/hide toggle
- Event listing, search, filtering, and sorting
- Event creation, editing, deletion, and media uploads
- Seat booking, cancellation, and reminder toggles
- Organizer/admin analytics dashboards
- CSV export for registration data
- Email notifications for signup verification, bookings, cancellations, and reminders

## Core Functionality

### Attendee Features

- Create an account with username, email, role, city, and password
- Verify email with OTP before signup completes
- Log in and view a personal profile page
- Browse published events only
- Search events by title or description
- Filter events by category, city, and timing
- Sort events by date, recent uploads, popularity, title, or price
- View attendee-friendly event detail pages with availability and media carousel
- Book one or more seats for a published upcoming event
- Cancel all or part of an existing booking
- Enable or disable reminder emails for a booking
- View booking history, confirmed seats, and cancelled seats from the profile page

### Organizer Features

- Sign up as an organizer
- Create events with venue, city, dates, times, price, capacity, status, and Google Maps link
- Use an existing category or create a custom category during event creation
- Upload multiple images and videos for an event carousel
- Edit or delete owned events
- View organizer-specific dashboard analytics
- See event totals, upcoming events, past events, confirmed registrations, estimated revenue, and chart data
- Review a pie chart for category distribution, a line chart for monthly registration trends, a bar chart for per-event registration volumes, and a gauge chart for seat occupancy percentage
- Manage upcoming events from the profile workspace and dashboard

### Admin Features

- Access all organizer-style dashboard analytics across the platform
- View and manage data through Django admin
- Export all registration records as CSV from the dashboard
- Access admin-focused profile workspace summaries

## User Flows

### Signup and Verification

1. A user fills the signup form with username, email, role, city, and password.
2. The frontend validates username, email, and password in real time.
3. The user requests an email OTP.
4. The system stores a `VerificationOTP` record and sends the OTP by email.
5. After OTP verification, signup succeeds and the linked `UserProfile` is marked `email_verified=True`.

### Login Experience

- The login form includes a password visibility toggle so users can switch between hidden and visible password input before submitting.

### Profile Completion and Booking Readiness

To book an event, an attendee must have:

- A valid account
- A verified email address
- A city set on the profile

If a user changes their email in the profile edit page, the profile becomes unverified until the new email is confirmed via OTP.

### Event Discovery

Attendees can use:

- The home page for featured events
- The event list page for filters and sorting
- The search page for keyword-based lookup

Organizers and admins can see non-published events in management contexts, while regular attendees only see published events.

### Booking and Cancellation

1. The attendee opens a published upcoming event.
2. The system checks that the user is authenticated, not an organizer/admin, profile-ready, and that seats are available.
3. A confirmed `Registration` is created or increased if the attendee already has the same booking.
4. A booking confirmation email is sent when email is configured.
5. The attendee can later cancel some or all booked seats.
6. Cancellation updates seat counts and can fully mark a booking as cancelled.
7. Cancellation emails are sent to the attendee and organizer when email delivery is available.

### Reminders

- Confirmed bookings have reminder support.
- Attendees can toggle reminders on or off per booking.
- A management command sends reminder emails for upcoming confirmed bookings inside a configurable time window.

## App Architecture

### `accounts/`

Responsible for authentication and profile-related behavior.

- `models.py`: `UserProfile` and `VerificationOTP`
- `forms.py`: signup, login, and profile update forms
- `views.py`: signup, login/logout, OTP endpoints, profile page, profile edit page, validation endpoints
- `utils.py`: OTP generation/verification helpers, role helpers, booking-readiness checks, email notification helpers
- `context_processors.py`: exposes the current user role to templates
- `admin.py`: admin registration for profile data
- `tests.py`: account, signup, profile, and related integration tests

### `events/`

Responsible for event data and booking operations.

- `models.py`: categories, events, media, tickets, registrations, payments, notifications
- `forms.py`: event form, media upload handling, booking form, cancellation form
- `views.py`: event list/detail/create/update/delete plus booking, cancellation, and reminder toggles
- `management/commands/send_event_reminders.py`: sends reminder emails for upcoming bookings
- `admin.py`: admin interfaces for event-related models
- `tests.py`: event listing, creation, booking, cancellation, and reminder tests

### `dashboard/`

Responsible for organizer/admin analytics and export behavior.

- `views.py`: dashboard summary metrics, chart datasets for category mix, registration trends, event volumes, seat occupancy, paginated event list, registration export
- `urls.py`: dashboard landing page and CSV export route

### `core/`

Responsible for public-facing top-level pages.

- `views.py`: home page and search results
- `urls.py`: root home route and search route

### `EventVerse/`

Project configuration layer.

- `settings.py`: installed apps, middleware, templates, static/media setup, auth redirects, email config, dotenv loading
- `urls.py`: root route registration for `core`, `accounts`, `events`, `dashboard`, and Django admin

## Project Structure

```text
EventVerse/
|-- EventVerse/                Project settings and root URLs
|-- accounts/                  Authentication, profiles, OTPs, role helpers
|-- core/                      Home page and search
|-- dashboard/                 Organizer/admin analytics and exports
|-- events/                    Events, media, bookings, reminders, notifications
|-- media/                     Uploaded event files in development
|-- static/                    Static assets
|-- templates/                 Shared and app-level templates
|-- .env                       Local environment variables
|-- .env.example               Example environment configuration
|-- build.sh                   Deployment/build helper
|-- db.sqlite3                 SQLite database
|-- manage.py                  Django management entry point
|-- README.md
`-- requirements.txt
```

## Data Model Summary

### `accounts` models

- `UserProfile`: one-to-one extension of Django `User`; stores role, city, email verification status, created timestamp, and a legacy phone field still present in the schema
- `VerificationOTP`: stores OTP target, channel, purpose, code, verification status, expiry, and timestamps

### `events` models

- `Category`: reusable event grouping
- `Event`: main event record with organizer, schedule, venue, capacity, price, status, slug, and optional legacy image
- `EventMedia`: uploaded images and videos tied to an event
- `Ticket`: default ticket model synced to each event
- `Registration`: attendee booking record with seat counts, status, cancellation tracking, and reminder state
- `Payment`: payment metadata placeholder for extended payment workflows
- `Notification`: in-app notification record

## Important Business Rules

- Signup requires verified email OTP
- Email addresses and usernames must be unique
- Only organizers and admins can create/edit/delete events
- Organizers and admins cannot book seats through the attendee booking flow
- Attendees can only book published events that have not ended
- Booked seats cannot exceed available seats
- Cancellation cannot exceed currently booked seats
- Event reminders only apply to confirmed bookings
- Admin registration export is restricted to admin users only

## Main Routes

### Public and Core

- `/` -> home page
- `/search/` -> search results
- `/events/` -> event listing
- `/events/<id>/` -> event detail

### Accounts

- `/accounts/signup/`
- `/accounts/login/`
- `/accounts/logout/`
- `/accounts/profile/`
- `/accounts/profile/edit/`
- `/accounts/send-email-otp/`
- `/accounts/verify-email-otp/`
- `/accounts/profile/send-email-otp/`
- `/accounts/profile/verify-email-otp/`
- `/accounts/validate-email/`
- `/accounts/validate-username/`
- `/accounts/validate-password/`

### Event Management

- `/events/create/`
- `/events/<id>/edit/`
- `/events/<id>/delete/`
- `/events/<id>/book/`
- `/events/<id>/cancel/`
- `/events/<id>/reminders/`

### Dashboard and Admin

- `/dashboard/`
- `/dashboard/registrations/export/`
- `/admin/`

The dashboard includes:

- A pie chart for event category distribution
- A line chart for monthly confirmed registration trends
- A bar chart for confirmed registration volume by event
- A gauge chart for overall seat occupancy percentage

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

3. Copy the example environment file:

```bash
copy .env.example .env
```

4. Update `.env` with the values you want to use.
5. Apply migrations:

```bash
python manage.py migrate
```

6. Create an admin user if needed:

```bash
python manage.py createsuperuser
```

7. Start the development server:

```bash
python manage.py runserver
```

8. Open `http://127.0.0.1:8000/`

## Environment Variables

The project loads `.env` automatically at startup from `EventVerse/settings.py`.

### General settings

- `DEBUG`: enables development debug mode
- `ALLOWED_HOSTS`: comma-separated allowed hosts

### Email settings

- `EMAIL_BACKEND`: backend for email delivery
- `EMAIL_HOST`: SMTP host
- `EMAIL_PORT`: SMTP port
- `EMAIL_HOST_USER`: SMTP username
- `EMAIL_HOST_PASSWORD`: SMTP password or app password
- `EMAIL_USE_TLS`: enable TLS
- `EMAIL_USE_SSL`: enable SSL
- `EMAIL_TIMEOUT`: timeout in seconds
- `DEFAULT_FROM_EMAIL`: sender identity

If SMTP credentials are not provided, the app falls back to Django's console email backend, which is useful in local development.

### Example `.env`

```env
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_char_app_password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_TIMEOUT=30
DEFAULT_FROM_EMAIL=EventVerse <your_email@gmail.com>
```

## Static and Media Handling

- Static assets are served from `static/`
- `WhiteNoise` is configured for static file serving
- Uploaded event files are stored under `media/`
- In development, media files are served by Django when `DEBUG=True`

## Email and Notifications

The system can send:

- Signup OTP emails
- Profile email verification OTP emails
- Booking confirmation emails
- Booking cancellation emails
- Organizer cancellation notices
- Upcoming event reminder emails

## Testing

Run all tests:

```bash
python manage.py test
```

Run focused suites:

```bash
python manage.py test accounts.tests
python manage.py test events.tests
```

## Reminder Command

Send reminders for events starting within the next 24 hours:

```bash
python manage.py send_event_reminders
```

Send reminders with a custom time window:

```bash
python manage.py send_event_reminders --hours 36
```

## Current Limitations

- Payments are modeled but not connected to a real payment gateway yet
- The schema still contains legacy phone-related fields that are no longer part of the active signup flow
- Email delivery quality depends on SMTP configuration in `.env`
- SQLite is used by default, which is simple for development but not ideal for larger production workloads

## Summary

EventVerse is organized as a clear Django multi-app project with role-based access, verified-email onboarding, event publishing, attendee booking flows, organizer/admin analytics, CSV export, and reminder automation. This repository is well-suited for demonstrating full-stack Django fundamentals across authentication, CRUD workflows, media uploads, booking logic, dashboarding, and email-driven interactions.
