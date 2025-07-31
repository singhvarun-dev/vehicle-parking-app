# Vehicle Parking App

A web application for managing parking lots, parking spots, and reservations with two user roles: Admin and User. Built using Flask, SQLite, SQLAlchemy, WTForms, and Bootstrap 5. Users can register, login, book parking spots for specified durations and vehicle types, view their history and feedback, and get QR codes for their active bookings. Admins can manage lots, edit/delete lots, see booking analytics, and review feedback.

## Features

- Admin:
  - Add/edit/delete parking lots (parking spots auto-created per lot).
  - View/manage all lots and spot statuses.
  - Search/filter lots by location/spot/availability.
  - View all users and reservations.
  - See spot utilization analytics (charts).
  - See feedback from users for each lot.

- User:
  - Register/login/logout.
  - View lots, free/occupied spot count, and lot vehicle support.
  - Book a parking spot (first available, specify vehicle type and duration).
  - Release (vacate) spot, with fee calculation.
  - View history, reservation cost chart, QR booking code.
  - Edit own profile and reset password.
  - Submit feedback/rating for any lot.
  - FAQ/help section.

## Tech Stack

- **Backend:** Python (Flask), Flask-SQLAlchemy (ORM), SQLite3 database
- **Frontend:** Jinja2 templating, Bootstrap 5 CSS
- **Other:** Chart.js (charts)

## Setup Instructions

1. **Clone/download this repository**

2. **Install requirements:** pip install -r requirements.txt


## ER Diagram (summary)

- **User** 1--* Reservation *--1 **ParkingSpot** *--1 **Mall**
- **User** 1--* Feedback *--1 **Mall**
- **Mall** (lot) 1--* ParkingSpot

## API Endpoints (for analytics)

- `/admin/chart_data` — GET, parking lot utilization (JSON)
- `/user/chart_data` — GET, individual user costs (JSON)

---



