import streamlit as st
import requests
import pandas as pd

# --- CONFIGURATION ---
API_KEY = "988f69c52b479e0873b5f966dd7908b8"  # <--- PASTE YOUR KEY HERE
SPORT = "basketball_nba"
MARKETS = "player_points,player_rebounds,player_assists" 
BOOKMAKERS = "draftkings,fanduel,mgm"

st.set_page_config(page_title="SharpStake | +EV Finder", layout="wide")

# --- 1. THE MATH ENGINE ---
def american_to_prob(odds):
    """Converts American odds (-110, +150) to Implied Probability (0-100%)"""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return (-odds) / (-odds + 100)

def get_data():
    """Fetches live odds from The Odds API"""
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": MARKETS,
        "bookmakers": BOOKMAKERS,
        "oddsFormat": "american"
    }
    # First get events (games)
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        st.error(f"Error fetching games: {resp.text}")
        return []
    
    events = resp.json()
    all_props = []

    # Loop through each game to get props
    for event in events:
        event_id = event['id']
        game_title = f"{event['home_team']} vs {event['away_team']}"
        
        # Fetch props for this game
        props_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds"
        props_resp = requests.get(props_url, params=params)
        if props_resp.status_code != 200: continue
        
        game_data = props_resp.json()
        
        for book in game_data['bookmakers']:
            book_name = book['title']
            for market in book['markets']:
                prop_type = market['key'] # e.g. player_points
                for outcome in market['outcomes']:
                    player_name = outcome['name']
                    line = outcome.get('point', 0) # The stat line (e.g. 25.5)
                    odds = outcome['price']
                    prob = american_to_prob(odds) * 100 # Convert to %
                    
                    all_props.append({
                        "Game": game_title,
                        "Player": player_name,
                        "Prop": prop_type.replace("player_", "").title(),
                        "Line": line,
                        "Side": "Over" if "Over" in outcome['name'] else "Under", # Simplified
                        "Book": book_name,
                        "Odds": odds,
                        "Win%": round(prob, 2)
                    })
    return pd.DataFrame(all_props)

# --- 2. THE WEBSITE (FRONTEND) ---
st.title("⚡ SharpStake: The +EV Finder")
st.markdown("Find the best player props instantly.")

# Sidebar Controls
ev_threshold = st.sidebar.slider("Minimum Win Probability (%)", 50, 75, 56)
selected_prop = st.sidebar.multiselect("Filter Prop Type", ["Points", "Rebounds", "Assists"], default=["Points"])

# Load Data Button
if st.button("Refresh Odds"):
    with st.spinner("Scanning Sportsbooks..."):
        df = get_data()
        if not df.empty:
            # Filter Data
            mask = (df['Win%'] >= ev_threshold) & (df['Prop'].isin(selected_prop))
            filtered_df = df[mask].sort_values(by="Win%", ascending=False)
            
            # Show Best Bets
            st.success(f"Found {len(filtered_df)} +EV Plays!")
            
            # Style the Table
            st.dataframe(
                filtered_df,
                column_config={
                    "Win%": st.column_config.ProgressColumn(
                        "Win Probability",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                },
                use_container_width=True
            )
        else:
            st.warning("No data found or API limit reached.")
