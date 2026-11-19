# RideSync

A bike rental management system designed to simplify campus mobility through easy booking and efficient fleet management, developed using DevOps and SCM practices.

## Project Overview

RideSync is a campus-focused bike rental management system that provides a simple and organized way for students to access shared mobility services. The application brings user authentication, vehicle availability, bike booking, rental management, and administrative fleet control into a single platform.

The project was developed collaboratively using DevOps and Source Code Management (SCM) practices. Git and GitHub are used for version control and collaboration, while feature branches, pull requests, peer reviews, automated testing, and GitHub Actions support a structured development workflow.

## Project Objectives

- Provide a simple platform for campus bike rental and booking.
- Allow users to securely register, log in, and manage their bookings.
- Display available vehicles and maintain their rental status.
- Provide administrators with tools to manage the vehicle fleet.
- Maintain application data through a structured database system.
- Apply Git and GitHub for collaborative source code management.
- Follow feature-branch and pull-request based development.
- Use automated testing to identify regressions and integration problems.
- Integrate CI/CD practices using GitHub Actions.

## Key Features

### Student Features

- Secure user registration and login
- Login using username or email
- View available bikes and vehicles
- Book available vehicles
- View and manage current bookings
- Cancel or complete rentals
- Secure session and logout functionality

### Admin Features

- Role-based admin access
- Dedicated admin dashboard
- View and manage the vehicle fleet
- Add new vehicles
- Edit existing vehicle information
- Update vehicle availability status
- Delete eligible vehicles
- Prevent unauthorized student access to admin routes

## Technology Stack

| Technology | Purpose |
| --- | --- |
| Python | Core backend programming language |
| Flask | Web application framework and routing |
| PostgreSQL / SQLite | Application data storage and database management |
| HTML | Structure of web pages |
| CSS | User interface styling |
| JavaScript | Client-side interactions |
| pytest | Automated application testing |
| Git | Version control and Source Code Management |
| GitHub | Remote repository and team collaboration |
| GitHub Actions | Continuous Integration and CI/CD automation |

## Vehicles

Signed-in users can view the seeded fleet at `/vehicles`. On startup, the application creates the vehicle table and seeds the default fleet if it is empty. Run `python seed_vehicles.py` to safely add any missing default vehicles.

## Account Recovery Setup

Registration requires a unique email address and Indian mobile number. Enter the 10-digit number starting with 6-9, either by itself (for example, `9876543210`) or prefixed with `+91` (for example, `+919876543210`). Numbers are stored with the `+91` prefix, so both formats are treated as the same number.

Users can log in with either their username or email address. Password recovery sends a time-limited, six-digit code to the registered email or mobile number.

Email delivery uses an SMTP account. Set these environment variables before running the application:

| Variable | Purpose |
| --- | --- |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port; defaults to `587` (`465` uses SSL) |
| `SMTP_USERNAME` | SMTP login |
| `SMTP_PASSWORD` | SMTP password or app password |
| `SMTP_FROM` | Verified sender email address |

Mobile delivery uses Twilio. Set these variables to enable SMS:

| Variable | Purpose |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Twilio number that sends the code |

Keep these values in the deployment environment and do not commit them to the repository.

Set `RIDESYNC_SECRET_KEY` to a private random value before deploying.

On startup, the app safely migrates older SQLite `users` tables in place, adding the authentication columns and deriving unique usernames for existing accounts. Existing password hashes are retained; legacy plaintext passwords, if present, are hashed during migration. Existing account records are not deleted.

By default, the app opens `ridesync.db` next to `app.py`, regardless of the directory from which the app is launched. Set `RIDESYNC_DATABASE` to use a different database file.

## Admin Vehicle Management

Users whose existing `users.role` is exactly `admin` can open `/admin` to manage the fleet.

Admins can:

- Add vehicles
- Edit vehicle information
- Delete eligible vehicles
- Set vehicle status to `available` or `unavailable`

Registration numbers must be unique. Vehicles with booking history cannot be deleted so that booking records remain intact.

New public registrations continue to receive the regular student role.

Admin access must be granted by a trusted operator; there is no public admin registration or role-promotion page. For local testing, register an account, then use a database client to update that account's `users.role` to `admin` before signing in again.

## Installation and Setup

Follow these steps to run RideSync locally.

### 1. Clone the Repository

```bash
git clone https://github.com/Vansh27682/RideSync.git
cd RideSync