#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a compact sportsbook-style NFL odds poster image (and optional CSV)
from a DraftKings-style Odds API JSON file.

Usage:
  python make_nfl_poster.py --json nfl_week1.json \
                            --out-img nfl_week1_colorcoded_plus.png \
                            --out-csv nfl_week1.csv \
                            --title "NFL Week 1 Odds - DraftKings"
ex to run: python3 nfl_bet_graphic.py --json nfl_week1.json --out-img nfl_week1_poster.png --title "NFL Week 1 Odds – DraftKings"


If --out-csv is omitted, no CSV is produced.
"""

import json
import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# ---------- Helpers ----------

def strip_team_name(team: str) -> str:
    """
    Keep the nickname (last word). E.g. "Philadelphia Eagles" -> "Eagles".
    """
    # Handle edge-cases (e.g., "Washington Commanders", "New York Jets")
    # This simple rule still works (last word = nickname).
    return team.split()[-1]

def format_odds(odds):
    """
    Format odds with '+' for positive numbers, leave negatives as-is.
    """
    if odds is None:
        return ""
    return f"+{odds}" if odds > 0 else str(odds)

def parse_json_to_df(json_path: Path) -> pd.DataFrame:
    """
    Parse Odds API JSON (DraftKings) into a tidy DataFrame of one row per game.
    Assumes a single bookmaker (DraftKings) with markets: h2h, spreads, totals.
    """
    with open(json_path, "r") as f:
        games = json.load(f)

    rows = []
    for g in games:
        home = g["home_team"]
        away = g["away_team"]
        start_iso = g.get("commence_time")
        # Normalize date display (YYYY-MM-DD)
        date_disp = start_iso[:10] if start_iso else ""

        # Expect first bookmaker to be DraftKings
        bm = g["bookmakers"][0]
        markets = {m["key"]: m["outcomes"] for m in bm["markets"]}

        # Moneyline
        ml_map = {o["name"]: o["price"] for o in markets.get("h2h", [])}

        # Spreads (each outcome has team name + point + price)
        spreads = markets.get("spreads", [])
        spread_home_point = next((o["point"] for o in spreads if o["name"] == home), None)
        spread_home_odds = next((o["price"] for o in spreads if o["name"] == home), None)
        spread_away_point = next((o["point"] for o in spreads if o["name"] == away), None)
        spread_away_odds = next((o["price"] for o in spreads if o["name"] == away), None)

        # Totals (two outcomes: Over/Under with same point)
        totals = markets.get("totals", [])
        total_points = next((o["point"] for o in totals if o["name"] in ("Over", "Under")), None)
        over_odds = next((o["price"] for o in totals if o["name"] == "Over"), None)
        under_odds = next((o["price"] for o in totals if o["name"] == "Under"), None)

        rows.append({
            "Game": f"{away} @ {home}",
            "Date": date_disp,
            "Home Team": home,
            "Away Team": away,
            "Moneyline Home": ml_map.get(home),
            "Moneyline Away": ml_map.get(away),
            "Spread Home": spread_home_point,
            "Spread Home Odds": spread_home_odds,
            "Spread Away": spread_away_point,
            "Spread Away Odds": spread_away_odds,
            "Total Points": total_points,
            "Over Odds": over_odds,
            "Under Odds": under_odds,
        })

    df = pd.DataFrame(rows)
    # Add short names
    df["Home Short"] = df["Home Team"].apply(strip_team_name)
    df["Away Short"] = df["Away Team"].apply(strip_team_name)
    return df

def build_poster(
    df: pd.DataFrame,
    title: str,
    out_path: Path,
    facecolor="#1e1e1e",
):
    """
    Render the compact poster with single-line entries, color-coding:
      - Favorites (lower moneyline) = limegreen
      - Underdogs = tomato
      - Spreads = skyblue
      - Totals = khaki
    Adds '+' signs to positive money odds.
    """
    # Figure height scales with number of games
    fig_height = max(3.5, len(df) * 0.45 + 1)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    ax.axis("off")
    ax.set_facecolor(facecolor)

    # Title
    ax.text(
        0.5, 1.02, title,
        ha="center", va="bottom",
        fontsize=16, fontweight="bold", color="white",
        transform=ax.transAxes
    )

    # For vertical spacing
    n = len(df)
    y_step = 1.0 / max(n, 1)
    top_y = 0.95

    for i, row in df.reset_index(drop=True).iterrows():
        y = top_y - i * y_step

        # Colors based on favorite (lower moneyline is favorite)
        home_is_fav = (
            row["Moneyline Home"] is not None and
            row["Moneyline Away"] is not None and
            row["Moneyline Home"] < row["Moneyline Away"]
        )
        away_is_fav = (
            row["Moneyline Home"] is not None and
            row["Moneyline Away"] is not None and
            row["Moneyline Away"] < row["Moneyline Home"]
        )

        home_color = "limegreen" if home_is_fav else "tomato"
        away_color = "limegreen" if away_is_fav else "tomato"

        # Format odds w/ plus sign
        ml_home = format_odds(row["Moneyline Home"])
        ml_away = format_odds(row["Moneyline Away"])
        sp_home_odds = format_odds(row["Spread Home Odds"])
        sp_away_odds = format_odds(row["Spread Away Odds"])
        ou_over = format_odds(row["Over Odds"])
        ou_under = format_odds(row["Under Odds"])

        # Single-line display pieces
        game_str = f"{row['Away Short']} @ {row['Home Short']} ({row['Date']})"
        ml_label = "ML:"
        sp_label = "SP:"
        ou_label = "O/U"

        # Left: Game info
        ax.text(0.01, y, game_str, ha="left", va="top",
                fontsize=9, color="white", family="monospace", transform=ax.transAxes)

        # Middle: Moneyline (color-coded fav/underdog)
        ax.text(0.35, y, ml_label, ha="left", va="top",
                fontsize=9, color="white", family="monospace", transform=ax.transAxes)
        ax.text(0.39, y, f"{row['Away Short']} {ml_away}",
                ha="left", va="top", fontsize=9, color=away_color, family="monospace", transform=ax.transAxes)
        ax.text(0.55, y, f"{row['Home Short']} {ml_home}",
                ha="left", va="top", fontsize=9, color=home_color, family="monospace", transform=ax.transAxes)

        # Right: Spreads (blue) and Totals (yellow, on next line for clarity)
        ax.text(0.72, y,
                f"{sp_label} {row['Away Short']} {row['Spread Away']} ({sp_away_odds}), "
                f"{row['Home Short']} {row['Spread Home']} ({sp_home_odds})",
                ha="left", va="top", fontsize=9, color="skyblue", family="monospace", transform=ax.transAxes)

        ax.text(0.01, y - 0.02,
                f"{ou_label} {row['Total Points']} (O {ou_over}, U {ou_under})",
                ha="left", va="top", fontsize=9, color="khaki", family="monospace", transform=ax.transAxes)

        # Divider line under each game
        ax.hlines(y - 0.035, 0.01, 0.99, colors="gray",
                  linestyles="dotted", linewidth=0.5, transform=ax.transAxes)

    out_path = Path(out_path)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=facecolor)
    plt.close(fig)
    return out_path

def export_csv(df: pd.DataFrame, out_csv: Path):
    """
    Export a tidy CSV with all key fields + short names.
    """
    cols = [
        "Date", "Away Team", "Home Team", "Away Short", "Home Short",
        "Moneyline Away", "Moneyline Home",
        "Spread Away", "Spread Away Odds",
        "Spread Home", "Spread Home Odds",
        "Total Points", "Over Odds", "Under Odds"
    ]
    df[cols].to_csv(out_csv, index=False)

# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="Create compact NFL odds poster from Odds API JSON.")
    parser.add_argument("--json", required=True, help="Path to Odds API JSON (e.g., nfl_week1.json)")
    parser.add_argument("--out-img", default="nfl_week_poster.png", help="Output image path")
    # parser.add_argument("--out-csv", default=None, help="Optional CSV export path")
    parser.add_argument("--title", default="NFL Odds - DraftKings", help="Poster title text")

    args = parser.parse_args()
    json_path = Path(args.json)

    df = parse_json_to_df(json_path)

    # Build poster
    out_img = build_poster(df, title=args.title, out_path=Path(args.out_img))
    print(f"Saved poster: {out_img}")

    # # Optional CSV
    # if args.out_csv:
    #     export_csv(df, Path(args.out_csv))
    #     print(f"Saved CSV: {args.out_csv}")

if __name__ == "__main__":
    main()
