set -a
source .env
set +a

START="2025-09-04T00:00:00Z"
END="2025-09-10T23:59:59Z"

curl -sS "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/?apiKey=${API_KEY}&regions=us&markets=h2h,spreads,totals&oddsFormat=american&bookmakers=draftkings&dateFormat=iso" \
| jq --arg start "$START" --arg end "$END" '[.[] | select(.commence_time >= $start and .commence_time <= $end)]' \
> nfl_week1.json && echo "Saved Week 1 games to nfl_week1.json"
