"""
Email configuration template.
Copy this file to config.py and fill in your details.

=== SETUP INSTRUCTIONS ===

1. Copy this file:
   cp config_template.py config.py

2. Edit config.py with your email credentials

3. For Gmail (recommended):
   - Go to https://myaccount.google.com/apppasswords
   - Sign in to your Google account
   - Select "Mail" as the app and your device
   - Click "Generate"
   - Copy the 16-character password (spaces are OK)
   - Use that as your sender_password below

4. For iCloud:
   - Go to https://appleid.apple.com/account/manage
   - Sign in and go to "App-Specific Passwords"
   - Generate a new password
   - Use that password below

=== SMTP SERVER SETTINGS ===

Gmail:    smtp.gmail.com, port 587
iCloud:   smtp.mail.me.com, port 587
Outlook:  smtp-mail.outlook.com, port 587
Yahoo:    smtp.mail.yahoo.com, port 587

=== SECURITY NOTE ===

NEVER commit config.py to git or share it publicly.
It contains your email credentials.
The .gitignore file should already exclude it.
"""

EMAIL_CONFIG = {
    # SMTP server settings
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,

    # Your email address (sender)
    "sender_email": "your.email@gmail.com",

    # App password (NOT your regular password)
    # For Gmail: 16 characters, spaces OK (e.g., "abcd efgh ijkl mnop")
    "sender_password": "xxxx xxxx xxxx xxxx",

    # Where to send briefings (can be same as sender)
    "recipient_email": "your.email@gmail.com",
}
