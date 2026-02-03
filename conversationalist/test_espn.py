#!/usr/bin/env python3
"""
Test script for ESPN fetcher.
Verifies all teams from contacts.json can be fetched.
"""

import time
from fetchers.espn import fetch_team_schedule, format_for_briefing, get_supported_teams

TEST_TEAMS = [
    "liverpool",      # Matt's always interest
    "juventus",       # Kyle (assistant) interest
    "knicks",         # NYC sports
    "giants",         # Kyle's always interest
    "duke",           # Kyle's always interest
    "eagles",         # Kyle's hate interest (still want the data!)
]


def main():
    print("ESPN Sports Fetcher Test")
    print("=" * 60)
    print(f"\nTesting {len(TEST_TEAMS)} teams...")

    errors = []
    successes = []

    for i, team in enumerate(TEST_TEAMS):
        print(f"\n{'=' * 60}")
        print(f"Testing: {team}")
        print("=" * 60)

        data = fetch_team_schedule(team)

        if "error" in data:
            print(f"ERROR: {data['error']}")
            errors.append(team)
        else:
            print(format_for_briefing(data))
            successes.append(team)

        # Rate limit between requests
        if i < len(TEST_TEAMS) - 1:
            time.sleep(0.5)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Successful: {len(successes)}/{len(TEST_TEAMS)}")
    if successes:
        print(f"  - {', '.join(successes)}")
    if errors:
        print(f"Failed: {len(errors)}/{len(TEST_TEAMS)}")
        print(f"  - {', '.join(errors)}")

    print("\n" + "=" * 60)
    print("Supported teams:")
    print(", ".join(get_supported_teams()))

    print("\n" + "=" * 60)
    print("Testing complete!")

    return len(errors) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
