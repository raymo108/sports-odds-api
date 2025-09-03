#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a compact sportsbook-style College Football odds poster image
from a DraftKings-style Odds API JSON file (like your ncaaf_week2.json).

Usage:
  python make_cfb_poster.py --json ncaaf_week2.json \
                            --out-img ncaaf_week2_collegenames.png \
                            --out-csv ncaaf_week2.csv \
                            --title "College Football Week 2 Odds – DraftKings"
ex: python3 collegefb_graphic.py --json ncaaf_week2.json --out-img ncaaf_week2_poster.png --title "NCAAF Week 2 Odds – DraftKings"

If --out-csv is omitted, no CSV is produced.
"""

import json
import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# ---------- Format helpers ----------

def fmt_plus(odds):
    """Add '+' for positive odds, keep negatives as-is; handle None."""
    if odds is None or (isinstance(odds, float) and pd.isna(odds)):
        return ""
    try:
        v = float(odds)
    except Exception:
        return str(odds)
    return f"+{int(v)}" if v > 0 else str(int(v))


# ---------- Name extraction (college/school only) ----------

def college_name(team: str) -> str:
    """
    Extract college/school from a full team string.

    Examples:
      "Illinois Fighting Illini"        -> "Illinois"
      "James Madison Dukes"             -> "James Madison"
      "North Carolina Tar Heels"        -> "North Carolina"
      "NC State Wolfpack"               -> "NC State"
      "West Virginia Mountaineers"      -> "West Virginia"
      "San Diego State Aztecs"          -> "San Diego State"
      "Florida International Panthers"  -> "Florida International"
      "Western Kentucky Hilltoppers"    -> "Western Kentucky"
    """
    if not isinstance(team, str) or not team.strip():
        return team

    words = team.split()

    # 1) Two-word “X State”, “X Tech”, “X International”
    if len(words) >= 2 and words[1] in {"State", "Tech", "International"}:
        return " ".join(words[:2])

    # 2) Three-word directional like "San Diego State", "New Mexico State"
    if len(words) >= 3 and (words[0], words[1]) in {
        ("San", "Diego"), ("San", "Jose"), ("San", "Antonio"),
        ("New", "Mexico"), ("New", "Hampshire"), ("New", "Orleans"),
        ("North", "Carolina"), ("South", "Carolina"),
        ("West", "Virginia"),
    }:
        if words[2] in {"State", "Tech"}:
            return " ".join(words[:3])
        return " ".join(words[:2])

    # 3) Directional + school (Northern Illinois, Western Kentucky, Central Michigan…)
    if len(words) >= 2 and words[0] in {"Northern", "Southern", "Eastern", "Western", "Central"}:
        return " ".join(words[:2])

    # 4) Two-word proper names (James Madison, Louisiana Tech, Texas A&M)
    if len(words) >= 2 and (
        words[0] in {"James", "Louisiana", "Texas", "Virginia", "West", "San", "New", "North", "South"} or
        "&" in team or "A&M" in team
    ):
        # Keep first two words by default (covers James Madison, Louisiana Tech, North Texas, etc.)
        return " ".join(words[:2])

    # 5) Default to first word
    return words[0]


# ---------- JSON -> DataFrame ----------

def parse_json_to_df(json_path: Path) -> pd.DataFrame:
    with open(json_path, "r") as f:
        games = json.load(f)

    rows = []
    for g in games:
        home = g.get("home_team")
        away = g.get("away_team")
        date_iso = g.get("commence_time") or ""
        date_disp = date_iso[:10] if date_iso else ""

        bm = (g.get("bookmakers") or [{}])[0]  # assume DraftKings
        markets = {m["key"]: m["outcomes"] for m in bm.get("markets", [])}

        # Moneyline
        ml_map = {o.get("name"): o.get("price") for o in markets.get("h2h", [])}

        # Spreads
        spreads = markets.get("spreads", [])
        sp_home_pt  = next((o.get("point") for o in spreads if o.get("name") == home), None)
        sp_home_odds = next((o.get("price") for o in spreads if o.get("name") == home), None)
        sp_away_pt  = next((o.get("point") for o in spreads if o.get("name") == away), None)
        sp_away_odds = next((o.get("price") for o in spreads if o.get("name") == away), None)

        # Totals
        totals = markets.get("totals", [])
        tot_pts  = next((o.get("point") for o in totals if o.get("name") in ("Over", "Under")), None)
        over_odds = next((o.get("price") for o in totals if o.get("name") == "Over"), None)
        under_odds= next((o.get("price") for o in totals if o.get("name") == "Under"), None)

        rows.append({
            "Date": date_disp,
            "Home Team": home,
            "Away Team": away,
            "Moneyline Home": ml_map.get(home),
            "Moneyline Away": ml_map.get(away),
            "Spread Home": sp_home_pt,
            "Spread Home Odds": sp_home_odds,
            "Spread Away": sp_away_pt,
            "Spread Away Odds": sp_away_odds,
            "Total Points": tot_pts,
            "Over Odds": over_odds,
            "Under Odds": under_odds,
        })

    df = pd.DataFrame(rows)
    # College/school names only
    df["Home Short"] = df["Home Team"].apply(college_name)
    df["Away Short"] = df["Away Team"].apply(college_name)
    return df


# ---------- Poster rendering ----------

def build_poster(
    df: pd.DataFrame,
    title: str,
    out_path: Path,
    facecolor="#1e1e1e",
):
    """
    Render compact poster with:
      - Favorites (lower ML) green; underdogs red
      - Spreads skyblue; Totals khaki
      - '+' added to all positive odds
      - extra spacing to avoid bunching
    """
    fig_height = max(4, len(df) * 0.6 + 1)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    ax.axis("off")
    ax.set_facecolor(facecolor)

    ax.text(0.5, 1.02, title,
            ha="center", va="bottom", fontsize=16, fontweight="bold",
            color="white", transform=ax.transAxes)

    n = len(df)
    y_step = 1.0 / (n + 2)   # breathing room
    top_y = 0.97

    for i, row in df.reset_index(drop=True).iterrows():
        y = top_y - i * y_step
        home_ml, away_ml = row["Moneyline Home"], row["Moneyline Away"]

        if pd.notna(home_ml) and pd.notna(away_ml):
            home_color = "limegreen" if home_ml < away_ml else "tomato"
            away_color = "limegreen" if away_ml < home_ml else "tomato"
        else:
            home_color = "white"
            away_color = "white"

        # Format all odds with + for positive
        ml_home = fmt_plus(home_ml)
        ml_away = fmt_plus(away_ml)
        sp_home_odds = fmt_plus(row["Spread Home Odds"])
        sp_away_odds = fmt_plus(row["Spread Away Odds"])
        ou_over = fmt_plus(row["Over Odds"])
        ou_under = fmt_plus(row["Under Odds"])

        # Row 1: Match + ML + Spread
        ax.text(0.01, y,
                f"{row['Away Short']} @ {row['Home Short']} ({row['Date']})",
                ha="left", va="top", fontsize=9.5, color="white",
                family="monospace", transform=ax.transAxes)

        ax.text(0.35, y, "ML:",
                ha="left", va="top", fontsize=9.5, color="white",
                family="monospace", transform=ax.transAxes)
        ax.text(0.39, y, f"{row['Away Short']} {ml_away}",
                ha="left", va="top", fontsize=9.5, color=away_color,
                family="monospace", transform=ax.transAxes)
        ax.text(0.55, y, f"{row['Home Short']} {ml_home}",
                ha="left", va="top", fontsize=9.5, color=home_color,
                family="monospace", transform=ax.transAxes)

        ax.text(0.72, y,
                f"SP: {row['Away Short']} {row['Spread Away']} ({sp_away_odds}), "
                f"{row['Home Short']} {row['Spread Home']} ({sp_home_odds})",
                ha="left", va="top", fontsize=9.5, color="skyblue",
                family="monospace", transform=ax.transAxes)

        # Row 2: Totals
        ax.text(0.01, y - 0.025,
                f"O/U {row['Total Points']} (O {ou_over}, U {ou_under})",
                ha="left", va="top", fontsize=9.5, color="khaki",
                family="monospace", transform=ax.transAxes)

        # Divider
        ax.hlines(y - 0.05, 0.01, 0.99, colors="gray",
                  linestyles="dotted", linewidth=0.5, transform=ax.transAxes)

    out_path = Path(out_path)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=facecolor)
    plt.close(fig)
    return out_path


# ---------- CSV export (optional) ----------

def export_csv(df: pd.DataFrame, out_csv: Path):
    cols = [
        "Date", "Away Team", "Home Team", "Away Short", "Home Short",
        "Moneyline Away", "Moneyline Home",
        "Spread Away", "Spread Away Odds",
        "Spread Home", "Spread Home Odds",
        "Total Points", "Over Odds", "Under Odds",
    ]
    df[cols].to_csv(out_csv, index=False)


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="Create compact CFB odds poster from Odds API JSON.")
    parser.add_argument("--json", required=True, help="Path to Odds API JSON (e.g., ncaaf_week2.json)")
    parser.add_argument("--out-img", default="ncaaf_poster.png", help="Output image path")
    # parser.add_argument("--out-csv", default=None, help="Optional CSV export path")
    parser.add_argument("--title", default="College Football Odds – DraftKings", help="Poster title")

    args = parser.parse_args()

    df = parse_json_to_df(Path(args.json))

    # Build poster
    out_img = build_poster(df, title=args.title, out_path=Path(args.out_img))
    print(f"Saved poster: {out_img}")

    # # Optional CSV
    # if args.out_csv:
    #     export_csv(df, Path(args.out_csv))
    #     print(f"Saved CSV: {args.out_csv}")


if __name__ == "__main__":
    main()
