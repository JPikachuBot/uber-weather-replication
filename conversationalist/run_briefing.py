#!/usr/bin/env python3
"""
Full Briefing Pipeline
Runs: fetch data → generate prompt → Claude → email

Usage:
    python3 run_briefing.py --user "Jackson"
    python3 run_briefing.py --user "Jackson" --no-email
    python3 run_briefing.py --user "Jackson" --contact "Matt"
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_generate_briefing(user: str, contact: str = None) -> str:
    """
    Run generate_briefing.py and return the path to the generated prompt file.
    """
    script_dir = Path(__file__).parent
    cmd = ["python3", str(script_dir / "generate_briefing.py"), "--user", user]

    if contact:
        cmd.extend(["--contact", contact])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir)

    if result.returncode != 0:
        print(f"ERROR generating briefing:")
        print(result.stderr or result.stdout)
        sys.exit(1)

    # Print the output (shows fetching progress)
    if result.stdout:
        # Extract just the progress lines, not the full prompt
        for line in result.stdout.split("\n"):
            if line.startswith("Generating") or line.startswith("  -") or line.startswith("+"):
                print(line)

    # Find the most recent prompt file
    output_dir = script_dir / "output"
    prompt_files = sorted(output_dir.glob("briefing_prompt_*.txt"), reverse=True)

    if not prompt_files:
        print("ERROR: No prompt file generated")
        sys.exit(1)

    return str(prompt_files[0])


def find_claude_cli() -> str:
    """
    Find the Claude CLI executable.
    Returns the path to claude, or exits with helpful error if not found.
    """
    import shutil

    # Check if claude is in PATH
    claude_path = shutil.which("claude")
    if claude_path:
        return claude_path

    # Check common installation locations
    common_paths = [
        Path.home() / ".npm-global" / "bin" / "claude",
        Path.home() / ".local" / "bin" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/opt/homebrew/bin/claude"),
    ]

    for path in common_paths:
        if path.exists():
            return str(path)

    # Not found - print helpful error
    print("ERROR: Claude CLI not found.")
    print()
    print("To install Claude CLI:")
    print("  npm install -g @anthropic-ai/claude-code")
    print()
    print("Or if already installed, make sure it's in your PATH.")
    sys.exit(1)


def run_claude_on_prompt(prompt_file: str) -> str:
    """
    Run Claude CLI on the prompt file and return path to final briefing.
    """
    script_dir = Path(__file__).parent

    # Find Claude CLI
    claude_cmd = find_claude_cli()

    # Read the prompt
    with open(prompt_file, "r") as f:
        prompt_content = f.read()

    # Generate output filename
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = script_dir / "output" / f"briefing_final_{today}.txt"

    # Run Claude CLI
    print("Running Claude to generate briefings...")

    try:
        result = subprocess.run(
            [claude_cmd, "-p", prompt_content],
            capture_output=True,
            text=True,
            cwd=script_dir,
        )
    except FileNotFoundError:
        print("ERROR: Claude CLI not found or not executable.")
        print("Install: npm install -g @anthropic-ai/claude-code")
        sys.exit(1)

    if result.returncode != 0:
        print(f"ERROR running Claude CLI:")
        print(result.stderr or "Unknown error")
        print()
        print("Make sure Claude CLI is authenticated.")
        print("Run: claude auth login")
        sys.exit(1)

    # Save output
    with open(output_file, "w") as f:
        f.write(result.stdout)

    return str(output_file)


def send_email(briefing_file: str):
    """
    Run send_email.py to email the briefing.
    """
    script_dir = Path(__file__).parent

    result = subprocess.run(
        ["python3", str(script_dir / "send_email.py"), "--file", briefing_file],
        capture_output=True,
        text=True,
        cwd=script_dir,
    )

    if result.returncode != 0:
        print(f"ERROR sending email:")
        print(result.stderr or result.stdout)
        sys.exit(1)

    # Print success message
    if result.stdout:
        print(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(
        description="Run the full Conversationalist briefing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 run_briefing.py --user "Jackson"
    python3 run_briefing.py --user "Jackson" --no-email
    python3 run_briefing.py --user "Jackson" --contact "Matt"

Cron setup (run daily at 7am):
    0 7 * * * cd ~/conversationalist && python3 run_briefing.py --user "Jackson" >> logs/cron.log 2>&1
        """,
    )
    parser.add_argument(
        "--user", default="Jackson", help="User to generate briefings for (default: Jackson)"
    )
    parser.add_argument("--contact", help="Generate for specific contact only")
    parser.add_argument(
        "--no-email", action="store_true", help="Skip sending email (for testing)"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("Conversationalist Briefing Pipeline")
    print("=" * 50)
    print(f"User: {args.user}")
    if args.contact:
        print(f"Contact: {args.contact}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    # Step 1: Generate prompt
    print("Step 1: Fetching data and generating prompt...")
    prompt_file = run_generate_briefing(args.user, args.contact)
    print(f"+ Prompt saved to {prompt_file}")
    print()

    # Step 2: Run Claude
    print("Step 2: Generating briefings via Claude...")
    briefing_file = run_claude_on_prompt(prompt_file)
    print(f"+ Briefing saved to {briefing_file}")
    print()

    # Step 3: Email (optional)
    if not args.no_email:
        print("Step 3: Sending email...")
        send_email(briefing_file)
    else:
        print("Step 3: Skipping email (--no-email flag)")

    print()
    print("=" * 50)
    print("Pipeline complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
