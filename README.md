# RideSync
A bike rental management system designed to simplify campus mobility through easy booking and efficient fleet management, developed using DevOps and SCM practices.

## Vehicles

Signed-in users can view the seeded fleet at `/vehicles`. On startup, the
application creates the vehicle table and seeds the default fleet if it is
empty. Run `python seed_vehicles.py` to safely add any missing default vehicles.

## Account recovery setup

Registration requires a unique email address and Indian mobile number. Enter
the 10-digit number starting with 6-9, either by itself (for example,
`9876543210`) or prefixed with `+91` (for example, `+919876543210`). Numbers
are stored with the `+91` prefix, so both formats are treated as the same
number. Users can log in with either their username or email address. Password
recovery sends a time-limited, six-digit code to the registered email or mobile
number.

Email delivery uses an SMTP account. Set these environment variables before
running the application:

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

Keep these values in the deployment environment and do not commit them to the
repository. Set `RIDESYNC_SECRET_KEY` to a private random value before deploying.
On startup, the app safely migrates older SQLite `users` tables in place,
adding the authentication columns and deriving unique usernames for existing
accounts. Existing password hashes are retained; legacy plaintext passwords,
if present, are hashed during migration. Existing account records are not
deleted. By default, the app opens `ridesync.db` next to `app.py`, regardless
of the directory from which the app is launched. Set `RIDESYNC_DATABASE` to
use a different database file.
