# RideSync
A bike rental management system designed to simplify campus mobility through easy booking and efficient fleet management, developed using DevOps and SCM practices.

## Account recovery setup

Registration requires a unique email address and mobile number. Enter mobile
numbers in international E.164 format, such as `+14155552671`. Users can log in
with either their username or email address. Password recovery sends a
time-limited, six-digit code to the registered email or mobile number.

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
The app adds the mobile-number column to existing SQLite databases when it
initializes. By default, it opens `ridesync.db` next to `app.py`, regardless of
the directory from which the app is launched. Set `RIDESYNC_DATABASE` to use a
different database file.
