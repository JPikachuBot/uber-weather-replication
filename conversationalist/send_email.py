#!/usr/bin/env python3
"""
Email sender for Conversationalist briefings.
Uses SMTP to send briefing emails.
"""

import argparse
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Import config (will error helpfully if not set up)
try:
    from config import EMAIL_CONFIG
except ImportError:
    print("ERROR: config.py not found.")
    print("")
    print("To set up email sending:")
    print("  1. Copy the template:  cp config_template.py config.py")
    print("  2. Edit config.py with your email credentials")
    print("  3. For Gmail, create an App Password at:")
    print("     https://myaccount.google.com/apppasswords")
    print("")
    print("See config_template.py for detailed instructions.")
    sys.exit(1)


def send_email(subject: str, body: str) -> bool:
    """
    Send an email using SMTP.

    Args:
        subject: Email subject line
        body: Email body text

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["sender_email"]
        msg["To"] = EMAIL_CONFIG["recipient_email"]
        msg["Subject"] = subject

        # Attach body as plain text
        msg.attach(MIMEText(body, "plain"))

        # Connect to SMTP server
        server = smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.starttls()  # Enable TLS encryption

        # Login
        server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])

        # Send
        server.sendmail(
            EMAIL_CONFIG["sender_email"],
            EMAIL_CONFIG["recipient_email"],
            msg.as_string(),
        )

        # Cleanup
        server.quit()

        return True

    except smtplib.SMTPAuthenticationError:
        print("ERROR: Authentication failed.")
        print("")
        print("Check your email and password in config.py")
        print("")
        print("For Gmail, you MUST use an App Password (not your regular password):")
        print("  1. Go to https://myaccount.google.com/apppasswords")
        print("  2. Generate a password for 'Mail'")
        print("  3. Use that 16-character password in config.py")
        return False

    except smtplib.SMTPException as e:
        print(f"ERROR: SMTP error: {e}")
        return False

    except ConnectionRefusedError:
        print("ERROR: Could not connect to email server.")
        print(f"Check your SMTP settings: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
        return False

    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False


def get_latest_briefing_file(output_dir: str = "output") -> str:
    """
    Find the most recent briefing file in the output directory.

    Args:
        output_dir: Directory to search for briefing files

    Returns:
        Path to the most recent file

    Raises:
        FileNotFoundError: If no briefing files found
    """
    script_dir = Path(__file__).parent
    output_path = script_dir / output_dir

    if not output_path.exists():
        raise FileNotFoundError(
            f"Output directory '{output_dir}' not found.\n"
            f"Run 'python3 generate_briefing.py' first to create a briefing."
        )

    files = list(output_path.glob("briefing_prompt_*.txt"))

    if not files:
        raise FileNotFoundError(
            f"No briefing files found in '{output_dir}'.\n"
            f"Run 'python3 generate_briefing.py' first to create a briefing."
        )

    # Return most recently modified file
    latest = max(files, key=lambda f: f.stat().st_mtime)
    return str(latest)


def main():
    """Parse arguments and send the email."""
    parser = argparse.ArgumentParser(
        description="Send Conversationalist briefing emails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 send_email.py --latest                    Send most recent briefing
  python3 send_email.py --file output/briefing.txt  Send specific file
  python3 send_email.py --latest --subject "Monday" Send with custom subject
  echo "Test" | python3 send_email.py --stdin       Send text from stdin
        """,
    )
    parser.add_argument("--file", help="Path to briefing file to send")
    parser.add_argument("--subject", help="Email subject line")
    parser.add_argument(
        "--stdin", action="store_true", help="Read email body from stdin"
    )
    parser.add_argument(
        "--latest", action="store_true", help="Send most recent briefing from output/"
    )

    args = parser.parse_args()

    # Determine email body
    if args.stdin:
        body = sys.stdin.read()
        if not body.strip():
            print("ERROR: No input received from stdin")
            sys.exit(1)

    elif args.latest:
        try:
            filepath = get_latest_briefing_file()
            print(f"Sending: {filepath}")
            with open(filepath, "r") as f:
                body = f.read()
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    elif args.file:
        try:
            with open(args.file, "r") as f:
                body = f.read()
        except FileNotFoundError:
            print(f"ERROR: File not found: {args.file}")
            sys.exit(1)

    else:
        print("ERROR: Must specify --file, --latest, or --stdin")
        print("Use --help for usage information.")
        sys.exit(1)

    # Determine subject
    if args.subject:
        subject = args.subject
    else:
        subject = f"Conversationalist Briefing - {datetime.now().strftime('%B %d, %Y')}"

    # Send it
    success = send_email(subject, body)

    if success:
        print(f"+ Email sent successfully to {EMAIL_CONFIG['recipient_email']}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
