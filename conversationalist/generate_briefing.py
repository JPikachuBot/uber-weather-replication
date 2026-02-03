#!/usr/bin/env python3
"""
Briefing Generator
Generates a Claude prompt with fetched sports data for contact briefings.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fetchers.espn import fetch_team_schedule, format_for_briefing, get_supported_teams


# Team name normalization mapping
TEAM_ALIASES = {
    # Soccer
    "liverpool fc": "liverpool",
    "liverpool": "liverpool",
    "chelsea fc": "chelsea",
    "chelsea": "chelsea",
    "manchester united": "manchester united",
    "man united": "manchester united",
    "man utd": "manchester united",
    "tottenham hotspur": "tottenham",
    "tottenham": "tottenham",
    "spurs": "tottenham",
    "arsenal fc": "arsenal",
    "arsenal": "arsenal",
    "manchester city": "manchester city",
    "man city": "manchester city",
    "juventus fc": "juventus",
    "juventus": "juventus",
    "juve": "juventus",
    "ac milan": "ac milan",
    "milan": "ac milan",
    "inter milan": "inter milan",
    "inter": "inter milan",

    # NFL
    "ny giants": "giants",
    "new york giants": "giants",
    "giants": "giants",
    "philadelphia eagles": "eagles",
    "philadelphia eagles hate": "eagles",  # Special case - hate interest
    "philly eagles": "eagles",
    "eagles": "eagles",

    # NBA
    "ny knicks": "knicks",
    "new york knicks": "knicks",
    "knicks": "knicks",

    # College Basketball
    "duke basketball": "duke",
    "duke blue devils": "duke",
    "duke": "duke",
    "march madness": None,  # Not a specific team - skip

    # Competitions (not directly fetchable as teams)
    "champions league": None,  # League, not a team
    "sports betting lines": None,  # Not a team
}


def load_contacts(filepath: str = "contacts.json") -> dict:
    """Load and parse the contacts JSON file."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def get_user_contacts(data: dict, user_name: str) -> list:
    """Get all contacts for a specific user."""
    for user in data.get("users", []):
        if user.get("name", "").lower() == user_name.lower():
            return user.get("contacts", [])
    return []


def normalize_team_name(topic: str) -> Optional[str]:
    """
    Normalize a topic/team name to match ESPN fetcher keys.
    Returns None if the topic should be skipped (not a fetchable team).
    """
    normalized = topic.lower().strip()

    # Check direct alias mapping
    if normalized in TEAM_ALIASES:
        return TEAM_ALIASES[normalized]  # May be None for skipped topics

    # Try removing common suffixes
    for suffix in [" fc", " sc", " cf"]:
        if normalized.endswith(suffix):
            base = normalized[:-len(suffix)]
            if base in TEAM_ALIASES:
                return TEAM_ALIASES[base]

    return normalized


def extract_espn_interests(contact: dict) -> list:
    """
    Parse a contact's always_interests and sometimes_interests.
    Return a list of teams/topics that can be fetched via ESPN.
    """
    interests = []
    supported_teams = set(get_supported_teams())

    # Process always_interests
    for interest in contact.get("always_interests", []):
        if interest.get("type") == "sports":
            topic = interest.get("topic", "")
            normalized = normalize_team_name(topic)

            # Skip if None (not a fetchable team) or not supported
            if normalized is None:
                continue

            # Check if it's a supported team
            if normalized in supported_teams or normalized in TEAM_ALIASES.values():
                interests.append({
                    "team": normalized,
                    "original_topic": topic,
                    "priority": "always",
                    "note": interest.get("note", ""),
                    "related": interest.get("related", []),
                })

    # Process sometimes_interests
    for interest in contact.get("sometimes_interests", []):
        if interest.get("type") == "sports":
            topic = interest.get("topic", "")
            normalized = normalize_team_name(topic)

            # Skip if None (not a fetchable team) or not supported
            if normalized is None:
                continue

            # Check if it's a supported team
            if normalized in supported_teams or normalized in TEAM_ALIASES.values():
                interests.append({
                    "team": normalized,
                    "original_topic": topic,
                    "priority": "sometimes",
                    "note": interest.get("note", ""),
                    "related": interest.get("related", []),
                })

    return interests


def fetch_contact_content(contact: dict, verbose: bool = True) -> dict:
    """
    Fetch all relevant ESPN content for a contact.
    """
    contact_name = contact.get("name", "Unknown")
    interests = extract_espn_interests(contact)

    if verbose:
        if interests:
            teams = [i["team"] for i in interests]
            print(f"  - {contact_name}: fetching {', '.join(teams)}...")
        else:
            print(f"  - {contact_name}: no ESPN sports found, skipping")

    sports_content = []

    for interest in interests:
        team = interest["team"]

        # Fetch data from ESPN
        data = fetch_team_schedule(team)

        sports_content.append({
            "team": interest["original_topic"],
            "team_key": team,
            "priority": interest["priority"],
            "note": interest["note"],
            "related": interest["related"],
            "data": data,
        })

        # Rate limiting
        time.sleep(0.5)

    return {
        "contact_name": contact_name,
        "location": contact.get("location", ""),
        "notes": contact.get("notes", ""),
        "sports_content": sports_content,
    }


def format_contact_section(contact_content: dict) -> str:
    """Format a single contact's content for the prompt."""
    lines = []

    lines.append("=" * 60)
    lines.append(f"CONTACT: {contact_content['contact_name']}")
    if contact_content["location"]:
        lines.append(f"Location: {contact_content['location']}")
    if contact_content["notes"]:
        lines.append(f"Notes: {contact_content['notes']}")
    lines.append("=" * 60)

    # Group by priority
    always_interests = [s for s in contact_content["sports_content"] if s["priority"] == "always"]
    sometimes_interests = [s for s in contact_content["sports_content"] if s["priority"] == "sometimes"]

    if always_interests:
        lines.append("")
        lines.append("--- ALWAYS INTERESTS ---")
        for item in always_interests:
            lines.append("")
            lines.append(f"[{item['team'].upper()} - PRIORITY: ALWAYS]")
            if item["note"]:
                lines.append(f"Note: {item['note']}")
            if item["related"]:
                lines.append(f"Related topics: {', '.join(item['related'][:5])}")
            lines.append("")
            lines.append(format_for_briefing(item["data"], verbosity="detailed"))

    if sometimes_interests:
        lines.append("")
        lines.append("--- SOMETIMES INTERESTS ---")
        for item in sometimes_interests:
            lines.append("")
            lines.append(f"[{item['team'].upper()} - PRIORITY: SOMETIMES]")
            if item["note"]:
                lines.append(f"Note: {item['note']}")
            if item["related"]:
                lines.append(f"Related topics: {', '.join(item['related'][:5])}")
            lines.append("")
            lines.append(format_for_briefing(item["data"], verbosity="normal"))

    return "\n".join(lines)


def format_as_claude_prompt(user_name: str, contacts_content: list) -> str:
    """
    Take all fetched content and format it as a prompt for Claude.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("BRIEFING GENERATION PROMPT")
    lines.append(f"Generated: {timestamp}")
    lines.append(f"User: {user_name}")
    lines.append("=" * 60)
    lines.append("")

    # Instructions
    lines.append("I need you to write personalized conversation briefings for me. I have meetings/interactions with the people below, and I want to be prepared with relevant talking points based on their interests.")
    lines.append("")
    lines.append("For each person, write a warm, natural-sounding briefing that:")
    lines.append("- Covers their \"always\" interests with enough detail to have a conversation")
    lines.append("- Only mentions \"sometimes\" interests if something genuinely notable happened (big win, major news, upset, drama)")
    lines.append("- Feels like a friend catching me up, not a sports ticker")
    lines.append("- Is concise: 3-5 short paragraphs per person")
    lines.append("- Highlights narratives and storylines, not just scores")
    lines.append("")
    lines.append("Here is the raw data for each contact:")
    lines.append("")

    # Contact sections
    for contact_content in contacts_content:
        if contact_content["sports_content"]:  # Only include contacts with sports content
            lines.append(format_contact_section(contact_content))
            lines.append("")

    # Footer
    lines.append("=" * 60)
    lines.append("END OF DATA")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Now write the briefings. Format your response as:")
    lines.append("")
    lines.append("---")
    lines.append("BRIEFING FOR: [Contact Name]")
    lines.append("---")
    lines.append("[Your conversational briefing here]")
    lines.append("")
    lines.append("---")
    lines.append("BRIEFING FOR: [Next Contact]")
    lines.append("---")
    lines.append("[...]")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate conversation briefings from contacts and sports data"
    )
    parser.add_argument(
        "--user",
        type=str,
        help="User name to generate briefings for (default: first user in contacts.json)"
    )
    parser.add_argument(
        "--contact",
        type=str,
        help="Generate briefing for a specific contact only"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: output/briefing_prompt_YYYY-MM-DD.txt)"
    )

    args = parser.parse_args()

    # Load contacts
    script_dir = Path(__file__).parent
    contacts_path = script_dir / "contacts.json"
    data = load_contacts(str(contacts_path))

    # Get user name
    user_name = args.user
    if not user_name:
        # Default to first user
        users = data.get("users", [])
        if not users:
            print("Error: No users found in contacts.json")
            sys.exit(1)
        user_name = users[0].get("name", "Unknown")

    print(f"Generating briefing for {user_name}...")

    # Get contacts
    contacts = get_user_contacts(data, user_name)
    if not contacts:
        print(f"Error: No contacts found for user '{user_name}'")
        sys.exit(1)

    # Filter to specific contact if requested
    if args.contact:
        contacts = [c for c in contacts if args.contact.lower() in c.get("name", "").lower()]
        if not contacts:
            print(f"Error: No contact matching '{args.contact}' found")
            sys.exit(1)

    # Fetch content for each contact
    contacts_content = []
    for contact in contacts:
        content = fetch_contact_content(contact)
        contacts_content.append(content)

    # Generate prompt
    prompt = format_as_claude_prompt(user_name, contacts_content)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = script_dir / "output"
        output_dir.mkdir(exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_path = output_dir / f"briefing_prompt_{date_str}.txt"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to file
    with open(output_path, "w") as f:
        f.write(prompt)

    # Print prompt to terminal
    print("")
    print(prompt)
    print("")

    # Summary
    contacts_with_sports = sum(1 for c in contacts_content if c["sports_content"])
    print(f"+ Briefing prompt generated for {contacts_with_sports} contacts with sports interests")
    print(f"+ Saved to: {output_path}")
    print(f"+ Copy the above and paste into Claude chat to generate your briefings")


if __name__ == "__main__":
    main()
