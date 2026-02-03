"""
ESPN Sports Fetcher
Fetches scores, schedules, and standings from ESPN's public API.
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional


# Team ID mappings for ESPN API
TEAM_IDS = {
    # Soccer - Premier League (eng.1)
    "liverpool": {"id": "364", "league": "eng.1", "sport": "soccer"},
    "chelsea": {"id": "363", "league": "eng.1", "sport": "soccer"},
    "manchester united": {"id": "360", "league": "eng.1", "sport": "soccer"},
    "man united": {"id": "360", "league": "eng.1", "sport": "soccer"},
    "tottenham": {"id": "367", "league": "eng.1", "sport": "soccer"},
    "arsenal": {"id": "359", "league": "eng.1", "sport": "soccer"},
    "manchester city": {"id": "382", "league": "eng.1", "sport": "soccer"},
    "man city": {"id": "382", "league": "eng.1", "sport": "soccer"},

    # Soccer - Serie A (ita.1)
    "juventus": {"id": "111", "league": "ita.1", "sport": "soccer"},
    "ac milan": {"id": "103", "league": "ita.1", "sport": "soccer"},
    "inter milan": {"id": "110", "league": "ita.1", "sport": "soccer"},

    # NFL
    "giants": {"id": "19", "league": "nfl", "sport": "football"},
    "ny giants": {"id": "19", "league": "nfl", "sport": "football"},
    "new york giants": {"id": "19", "league": "nfl", "sport": "football"},
    "eagles": {"id": "21", "league": "nfl", "sport": "football"},
    "philadelphia eagles": {"id": "21", "league": "nfl", "sport": "football"},

    # NBA
    "knicks": {"id": "18", "league": "nba", "sport": "basketball"},
    "ny knicks": {"id": "18", "league": "nba", "sport": "basketball"},
    "new york knicks": {"id": "18", "league": "nba", "sport": "basketball"},

    # College Basketball
    "duke": {"id": "150", "league": "mens-college-basketball", "sport": "basketball"},
    "duke blue devils": {"id": "150", "league": "mens-college-basketball", "sport": "basketball"},
}

# League display names
LEAGUE_NAMES = {
    "eng.1": "Premier League",
    "ita.1": "Serie A",
    "uefa.champions": "Champions League",
    "nfl": "NFL",
    "nba": "NBA",
    "mens-college-basketball": "NCAA Men's Basketball",
}


def _build_api_url(sport: str, league: str, team_id: str, endpoint: str = "schedule") -> str:
    """Construct ESPN API URL for a given sport, league, and team."""
    base = "https://site.api.espn.com/apis/site/v2/sports"

    if sport == "soccer":
        return f"{base}/soccer/{league}/teams/{team_id}/{endpoint}"
    elif sport == "football":
        return f"{base}/football/{league}/teams/{team_id}/{endpoint}"
    elif sport == "basketball":
        if league == "nba":
            return f"{base}/basketball/nba/teams/{team_id}/{endpoint}"
        else:
            return f"{base}/basketball/{league}/teams/{team_id}/{endpoint}"

    return ""


def _build_scoreboard_url(sport: str, league: str) -> str:
    """Construct ESPN API URL for league scoreboard."""
    base = "https://site.api.espn.com/apis/site/v2/sports"

    if sport == "soccer":
        return f"{base}/soccer/{league}/scoreboard"
    elif sport == "football":
        return f"{base}/football/{league}/scoreboard"
    elif sport == "basketball":
        if league == "nba":
            return f"{base}/basketball/nba/scoreboard"
        else:
            return f"{base}/basketball/{league}/scoreboard"

    return ""


def _build_news_url(sport: str, league: str, team_id: str = None, limit: int = 5) -> str:
    """Construct ESPN API URL for news."""
    base = "https://site.api.espn.com/apis/site/v2/sports"

    if sport == "soccer":
        url = f"{base}/soccer/{league}/news"
    elif sport == "football":
        url = f"{base}/football/{league}/news"
    elif sport == "basketball":
        if league == "nba":
            url = f"{base}/basketball/nba/news"
        else:
            url = f"{base}/basketball/{league}/news"
    else:
        return ""

    params = [f"limit={limit}"]
    if team_id:
        params.append(f"team={team_id}")

    return f"{url}?{'&'.join(params)}"


def _parse_news_response(data: dict, limit: int = 5) -> list[dict]:
    """Parse ESPN news API response into article list."""
    articles = []

    for article in data.get("articles", [])[:limit]:
        headline = article.get("headline", "")
        description = article.get("description", "")
        published = article.get("published", "")
        links = article.get("links", {})

        # Get the web link
        link = ""
        if "web" in links:
            link = links["web"].get("href", "")

        if headline:
            articles.append({
                "headline": headline,
                "description": description,
                "published": published,
                "link": link,
            })

    return articles


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return None
    except json.JSONDecodeError:
        return None
    except Exception:
        return None


def _format_date(iso_date: str) -> str:
    """Convert ISO date to friendly format (e.g., 'Feb 1')."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%b %d").replace(" 0", " ")
    except (ValueError, AttributeError):
        return iso_date[:10] if iso_date else "TBD"


def _determine_result(our_score: int, their_score: int, sport: str) -> str:
    """Determine win/loss/draw based on scores."""
    if our_score > their_score:
        return "win"
    elif our_score < their_score:
        return "loss"
    else:
        return "draw" if sport == "soccer" else "tie"


def _parse_schedule_response(data: dict, team_info: dict, team_name: str) -> dict:
    """Parse ESPN schedule API response into our standard format."""
    result = {
        "team": team_name.title(),
        "sport": team_info["sport"],
        "league": LEAGUE_NAMES.get(team_info["league"], team_info["league"]),
        "recent_results": [],
        "upcoming": [],
        "standings": None,
    }

    # Get team display name from response if available
    if "team" in data:
        result["team"] = data["team"].get("displayName", team_name.title())

    # Parse events
    events = data.get("events", [])
    now = datetime.now()

    completed = []
    upcoming = []

    for event in events:
        # Determine if completed or upcoming
        competitions = event.get("competitions", [])
        if not competitions:
            continue

        comp = competitions[0]
        status = comp.get("status", {}).get("type", {}).get("state", "")

        # Get date
        date_str = event.get("date", "")

        # Get competitors
        competitors = comp.get("competitors", [])
        if len(competitors) != 2:
            continue

        # Find our team and opponent
        our_team = None
        opponent = None
        target_id = team_info["id"]

        for c in competitors:
            team_data = c.get("team", {})
            # Check multiple ID locations and formats (string and int comparison)
            comp_id = str(c.get("id", ""))
            team_id = str(team_data.get("id", ""))

            if comp_id == target_id or team_id == target_id:
                our_team = c
            else:
                opponent = c

        if not our_team or not opponent:
            # Try matching by name if ID doesn't work
            our_team = None
            opponent = None
            for c in competitors:
                team_data = c.get("team", {})
                team_names = [
                    team_data.get("displayName", "").lower(),
                    team_data.get("shortDisplayName", "").lower(),
                    team_data.get("name", "").lower(),
                    team_data.get("abbreviation", "").lower(),
                ]
                # Check if our team name is contained in any of the team names
                if any(team_name.lower() in n or n in team_name.lower() for n in team_names if n):
                    our_team = c
                else:
                    opponent = c

        if not our_team or not opponent:
            continue

        opponent_name = opponent.get("team", {}).get("displayName", "Unknown")
        home_away = our_team.get("homeAway", "home")

        # Get competition name
        competition_name = ""
        notes = event.get("competitions", [{}])[0].get("notes", [])
        if notes:
            competition_name = notes[0].get("headline", "")
        if not competition_name:
            competition_name = result["league"]

        if status == "post":
            # Completed game
            our_score = int(our_team.get("score", {}).get("value", 0) if isinstance(our_team.get("score"), dict) else our_team.get("score", 0))
            their_score = int(opponent.get("score", {}).get("value", 0) if isinstance(opponent.get("score"), dict) else opponent.get("score", 0))

            game_result = _determine_result(our_score, their_score, team_info["sport"])

            # Format score string - always show our_score-their_score
            score_str = f"{our_score}-{their_score}"

            completed.append({
                "date": _format_date(date_str),
                "date_raw": date_str,
                "opponent": opponent_name,
                "home_away": home_away,
                "score": score_str,
                "result": game_result,
                "competition": competition_name,
            })
        elif status in ("pre", "scheduled"):
            # Upcoming game
            upcoming.append({
                "date": _format_date(date_str),
                "date_raw": date_str,
                "opponent": opponent_name,
                "home_away": home_away,
                "competition": competition_name,
            })

    # Sort and limit results
    completed.sort(key=lambda x: x.get("date_raw", ""), reverse=True)
    upcoming.sort(key=lambda x: x.get("date_raw", ""))

    # Remove raw dates and limit
    for game in completed:
        game.pop("date_raw", None)
    for game in upcoming:
        game.pop("date_raw", None)

    result["recent_results"] = completed[:5]
    result["upcoming"] = upcoming[:3]

    # Try to get standings
    if "team" in data and "standingSummary" in data["team"]:
        standing_str = data["team"]["standingSummary"]
        result["standings"] = {"summary": standing_str}

    # Try record
    if "team" in data and "record" in data["team"]:
        records = data["team"]["record"]
        if "items" in records:
            for item in records["items"]:
                if item.get("type") == "total":
                    stats = {s["name"]: s["value"] for s in item.get("stats", [])}
                    if team_info["sport"] == "soccer":
                        wins = int(stats.get("wins", 0))
                        draws = int(stats.get("ties", 0))
                        losses = int(stats.get("losses", 0))
                        points = int(stats.get("points", 0))
                        result["standings"] = {
                            "record": f"{wins}W-{draws}D-{losses}L",
                            "points": points,
                        }
                    else:
                        wins = int(stats.get("wins", 0))
                        losses = int(stats.get("losses", 0))
                        result["standings"] = {
                            "record": f"{wins}-{losses}",
                        }
                    break

    return result


def fetch_team_schedule(team_name: str, include_news: bool = True) -> dict:
    """
    Fetch recent results, upcoming fixtures, and news for a team.

    Args:
        team_name: Team name (case-insensitive, e.g., "Liverpool", "giants")
        include_news: Whether to fetch news articles (default True)

    Returns:
        Dictionary with team info, recent_results, upcoming, standings, and news.
        On error, returns {"team": name, "error": "reason"}.
    """
    team_key = team_name.lower().strip()

    if team_key not in TEAM_IDS:
        return {"team": team_name, "error": f"Team not found: {team_name}"}

    team_info = TEAM_IDS[team_key]
    url = _build_api_url(team_info["sport"], team_info["league"], team_info["id"])

    data = _fetch_json(url)
    if data is None:
        return {"team": team_name, "error": "Could not fetch data: API request failed"}

    result = _parse_schedule_response(data, team_info, team_name)

    # Fetch news if requested
    if include_news:
        news_data = fetch_team_news(team_name, limit=5)
        result["news"] = news_data.get("articles", [])
    else:
        result["news"] = []

    return result


def fetch_league_scoreboard(league: str, sport: str) -> dict:
    """
    Fetch recent scores across a league.

    Args:
        league: League code (e.g., "eng.1", "nfl")
        sport: Sport type (e.g., "soccer", "football", "basketball")

    Returns:
        Dictionary with league name and list of games.
    """
    url = _build_scoreboard_url(sport, league)

    result = {
        "league": LEAGUE_NAMES.get(league, league),
        "sport": sport,
        "games": [],
    }

    data = _fetch_json(url)
    if data is None:
        result["error"] = "Could not fetch scoreboard data"
        return result

    events = data.get("events", [])

    for event in events:
        competitions = event.get("competitions", [])
        if not competitions:
            continue

        comp = competitions[0]
        competitors = comp.get("competitors", [])
        if len(competitors) != 2:
            continue

        home = None
        away = None
        for c in competitors:
            if c.get("homeAway") == "home":
                home = c
            else:
                away = c

        if not home or not away:
            continue

        home_team = home.get("team", {}).get("displayName", "Unknown")
        away_team = away.get("team", {}).get("displayName", "Unknown")

        home_score = home.get("score", "0")
        away_score = away.get("score", "0")

        status_type = comp.get("status", {}).get("type", {})
        status = status_type.get("state", "scheduled")
        if status == "post":
            status = "final"
        elif status == "in":
            status = "in_progress"

        # Determine if notable (high-scoring, close game, etc.)
        try:
            h_score = int(home_score)
            a_score = int(away_score)
            total_goals = h_score + a_score
            margin = abs(h_score - a_score)
            notable = (total_goals >= 5) or (margin >= 4) or (status == "in_progress")
        except (ValueError, TypeError):
            notable = False

        result["games"].append({
            "date": _format_date(event.get("date", "")),
            "home_team": home_team,
            "away_team": away_team,
            "score": f"{home_score}-{away_score}",
            "status": status,
            "notable": notable,
        })

    return result


def fetch_team_news(team_name: str, limit: int = 5) -> dict:
    """
    Fetch recent news articles for a team.

    Args:
        team_name: Team name (case-insensitive, e.g., "Liverpool", "giants")
        limit: Maximum number of articles to return (default 5)

    Returns:
        Dictionary with team name and articles list.
        On error, returns {"team": name, "error": "reason"}.
    """
    team_key = team_name.lower().strip()

    if team_key not in TEAM_IDS:
        return {"team": team_name, "error": f"Team not found: {team_name}", "articles": []}

    team_info = TEAM_IDS[team_key]

    # Try team-specific news first
    url = _build_news_url(team_info["sport"], team_info["league"], team_info["id"], limit)
    data = _fetch_json(url)

    if data is None:
        # Fall back to league news if team-specific fails
        url = _build_news_url(team_info["sport"], team_info["league"], None, limit)
        data = _fetch_json(url)

    if data is None:
        return {"team": team_name, "error": "Could not fetch news: API request failed", "articles": []}

    articles = _parse_news_response(data, limit)

    return {
        "team": team_name.title(),
        "articles": articles,
    }


def format_for_briefing(team_data: dict, verbosity: str = "normal") -> str:
    """
    Format team data as human-readable text for LLM input.

    Args:
        team_data: Output from fetch_team_schedule()
        verbosity: "brief", "normal", or "detailed"

    Returns:
        Formatted string suitable for inclusion in a briefing.
    """
    if "error" in team_data:
        return f"=== {team_data['team'].upper()} ===\nError: {team_data['error']}\n"

    lines = []
    team_name = team_data.get("team", "Unknown Team")
    sport = team_data.get("sport", "")
    league = team_data.get("league", "")

    lines.append(f"=== {team_name.upper()} ===")
    lines.append(f"Sport: {sport.title()} ({league})")

    # Standings
    standings = team_data.get("standings")
    if standings:
        if "summary" in standings:
            lines.append(f"Current Standing: {standings['summary']}")
        elif "record" in standings:
            standing_line = f"Record: {standings['record']}"
            if "points" in standings:
                standing_line += f" ({standings['points']} pts)"
            lines.append(standing_line)

    lines.append("")

    # Recent results
    recent = team_data.get("recent_results", [])
    if recent:
        limit = 3 if verbosity == "brief" else 5
        lines.append(f"RECENT RESULTS (Last {min(len(recent), limit)}):")
        for game in recent[:limit]:
            home_away = "Home" if game["home_away"] == "home" else "Away"
            result_emoji = {"win": "WIN", "loss": "LOSS", "draw": "DRAW", "tie": "TIE"}.get(game["result"], "")
            lines.append(f"  {game['date']} ({home_away}): {team_name} {game['score']} {game['opponent']} [{result_emoji}] - {game['competition']}")
    else:
        lines.append("RECENT RESULTS: None available")

    lines.append("")

    # Upcoming fixtures
    upcoming = team_data.get("upcoming", [])
    if upcoming:
        limit = 2 if verbosity == "brief" else 3
        lines.append(f"UPCOMING FIXTURES (Next {min(len(upcoming), limit)}):")
        for game in upcoming[:limit]:
            home_away = "Home" if game["home_away"] == "home" else "Away"
            lines.append(f"  {game['date']} ({home_away}): vs {game['opponent']} - {game['competition']}")
    else:
        lines.append("UPCOMING FIXTURES: None scheduled")

    # News
    news = team_data.get("news", [])
    if news:
        lines.append("")
        news_limit = 2 if verbosity == "brief" else (5 if verbosity == "detailed" else 3)
        lines.append(f"RECENT NEWS:")
        for article in news[:news_limit]:
            headline = article.get("headline", "")
            published = article.get("published", "")
            date_str = _format_date(published) if published else ""
            if date_str:
                lines.append(f'  "{headline}" ({date_str})')
            else:
                lines.append(f'  "{headline}"')

    return "\n".join(lines)


def get_supported_teams() -> list[str]:
    """Return list of supported team names."""
    # Return unique team names (dedupe aliases)
    seen_ids = set()
    teams = []
    for name, info in TEAM_IDS.items():
        key = (info["id"], info["league"])
        if key not in seen_ids:
            seen_ids.add(key)
            teams.append(name)
    return sorted(teams)


if __name__ == "__main__":
    # Demo: fetch and display Liverpool data
    print("ESPN Sports Fetcher Demo")
    print("=" * 60)

    demo_teams = ["liverpool", "knicks"]

    for team in demo_teams:
        print(f"\nFetching {team}...")
        data = fetch_team_schedule(team)
        print(format_for_briefing(data))
        print()
        time.sleep(0.5)  # Be respectful to API

    print("\nSupported teams:")
    print(", ".join(get_supported_teams()))
