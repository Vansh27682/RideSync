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

Signed-in users can view the seeded fleet at `/vehicles`. On startup, the application creates the vehicle table and seeds the default fleet if it is empty.

Run:

```bash
python seed_vehicles.py
```

to safely add any missing default vehicles.

## Account Recovery Setup

Registration requires a unique email address and Indian mobile number.

Enter the 10-digit number starting with 6-9, either by itself, for example:

```text
9876543210
```

or prefixed with `+91`, for example:

```text
+919876543210
```

Numbers are stored with the `+91` prefix, so both formats are treated as the same number.

Users can log in with either their username or email address. Password recovery sends a time-limited, six-digit code to the registered email or mobile number.

### Email Configuration

Email delivery uses an SMTP account. Set these environment variables before running the application:

| Variable | Purpose |
| --- | --- |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port; defaults to `587` (`465` uses SSL) |
| `SMTP_USERNAME` | SMTP login |
| `SMTP_PASSWORD` | SMTP password or app password |
| `SMTP_FROM` | Verified sender email address |

### SMS Configuration

Mobile delivery uses Twilio. Set these variables to enable SMS:

| Variable | Purpose |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Twilio number that sends the code |

Keep these values in the deployment environment and do not commit them to the repository.

Set `RIDESYNC_SECRET_KEY` to a private random value before deploying.

On startup, the application safely migrates older SQLite `users` tables in place, adding the authentication columns and deriving unique usernames for existing accounts.

Existing password hashes are retained. Legacy plaintext passwords, if present, are hashed during migration. Existing account records are not deleted.

By default, the application opens `ridesync.db` next to `app.py`, regardless of the directory from which the application is launched.

Set `RIDESYNC_DATABASE` to use a different database file when required.

## Admin Vehicle Management

Users whose existing `users.role` is exactly `admin` can open `/admin` to manage the fleet.

Admins can:

- Add vehicles
- Edit vehicle information
- Delete eligible vehicles
- Set vehicle status to `available` or `unavailable`

Registration numbers must be unique.

Vehicles with booking history cannot be deleted so that booking records remain intact.

New public registrations continue to receive the regular student role.

Admin access must be granted by a trusted operator. There is no public admin registration or role-promotion page.

For local testing, register an account and use a database client to update that account's `users.role` to `admin` before signing in again.

---

## Installation and Setup

Follow these steps to run RideSync locally.

### 1. Clone the Repository

```bash
git clone https://github.com/Vansh27682/RideSync.git
cd RideSync
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment on macOS/Linux:

```bash
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs the Python packages required by RideSync, including Flask, testing dependencies, and database connectivity packages.

### 4. Configure Environment Variables

Set the required application secrets and database configuration through environment variables.

Example:

```bash
export RIDESYNC_SECRET_KEY="your-secret-key"
```

Additional SMTP and Twilio environment variables can be configured when email or SMS-based account recovery is required.

Database-specific environment variables should be configured according to the development or deployment environment.

### 5. Initialize Vehicle Data

Default vehicle data can be added using:

```bash
python seed_vehicles.py
```

### 6. Run the Application

Start the Flask application:

```bash
python app.py
```

The local development server can then be accessed from the address displayed in the terminal, typically:

```text
http://127.0.0.1:5000
```

### 7. Run Automated Tests

Run the complete automated test suite using:

```bash
pytest -v
```

These tests help verify authentication, booking, vehicle management, admin functionality, and other application behavior before changes are integrated.

---

## DevOps and SCM Workflow

RideSync follows a collaborative development workflow based on DevOps and Source Code Management (SCM) practices.

Git and GitHub are used to manage source code, isolate feature development, review changes, and integrate contributions from multiple developers.

### Development Workflow

The team follows this workflow for implementing changes:

```text
Requirement / GitHub Issue
          ↓
Create Feature Branch
          ↓
Develop Feature
          ↓
Stage Changes
          ↓
Commit Changes
          ↓
Push to GitHub
          ↓
Create Pull Request
          ↓
GitHub Actions CI/CD
          ↓
Automated Testing
          ↓
Peer Review
          ↓
Fix Issues if Required
          ↓
Approval
          ↓
Merge into Main
```

### Branching Strategy

Development is performed using separate feature and fix branches instead of making changes directly on `main`.

Examples used during RideSync development include:

- `feature/admin-vehicle-management`
- `feature/bike-booking`
- `feature/postgresql-support`
- `feature/admin-registration`
- `fix/dashboard`
- `fix/ridesync-gui-styling`
- `docs/readme-subhasmita`

This approach allows multiple developers to work independently while keeping the main branch stable.

### Pull Requests and Peer Review

After completing work on a branch, developers push their commits to GitHub and create a Pull Request (PR).

Pull Requests are used to:

- Review code before integration
- Discuss implementation changes
- Detect integration problems
- Run automated checks
- Request modifications when necessary
- Approve changes before merging into `main`

Peer review helps maintain code quality and supports collaborative development.

### Continuous Integration and CI/CD

RideSync uses GitHub Actions to automate validation of repository changes.

When configured GitHub events such as pushes or Pull Requests occur, the workflow can automatically:

1. Set up the required environment.
2. Install project dependencies.
3. Execute automated tests.
4. Report whether the workflow passed or failed.
5. Provide feedback before changes are integrated.

Failed workflow runs help identify problems early, while successful runs provide confidence that the integrated application continues to work correctly.

### Automated Testing

RideSync uses `pytest` for automated testing.

The test suite covers important application areas such as:

- User registration
- Authentication and login
- Vehicle functionality
- Bike booking
- Admin vehicle management
- Authorization and access control

Automated tests are integrated with the development workflow so that application changes can be validated consistently.

### Source Code Management Practices

The project applies the following SCM practices:

- Git-based version control
- Remote repository management using GitHub
- Feature and fix branches
- Meaningful commits
- Pull Requests
- Peer reviews
- Merge conflict resolution
- Automated testing
- GitHub Actions integration
- Controlled integration into the main branch

These practices allow the RideSync team to develop features collaboratively while maintaining a traceable and organized project history.

## Team Collaboration

RideSync was developed collaboratively by team members working on different areas of the application.

- **Subhasmita:** Backend development and backend feature implementation
- **Vansh:** Backend development, CI/CD pipeline, Pull Request reviews, and branching strategy
- **Jatin:** GUI and frontend development

The team's work was integrated through Git branches, commits, Pull Requests, peer reviews, automated tests, and GitHub Actions.

## Repository

GitHub Repository:

https://github.com/Vansh27682/RideSync