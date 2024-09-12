import streamlit as st
import numpy as np
from collections import Counter
import os
import sys
from itertools import cycle

def initialize(now, weighted):
    #structures for collecting data: goals shot and conceded, no. of matches played home and away, whole league shot and conceded
    team_shot_home, team_conceded_home, team_shot_away, team_conceded_away = {}, {}, {}, {}
    home_teams, away_teams = [], []
    league_stats = {'shot_home_avg': 0, 'shot_away_avg':0}

    #appending data to strcutures for all matchdays till the chosen one
    matchdays_played = [int(m) for m in os.listdir(f"{league}_matchdays") if int(m)<int(now)]
    
    for m in matchdays_played:
        factor = 1 if not weighted else int(m)
        h = open(f"{league}_matchdays/{m}", "r", encoding='utf-8')
        for match in h:
            home, away, goal_home, goal_away = match.strip().split("-")
            goal_home, goal_away = int(goal_home), int(goal_away)
            home_teams.extend([home]*factor)
            away_teams.extend([away]*factor)

            league_stats['shot_home_avg']+=factor*goal_home
            league_stats['shot_away_avg']+=factor*goal_away
            
            if not home in team_shot_home:
                team_shot_home[home]=factor*goal_home
                team_conceded_home[home]=factor*goal_away
            else:
                team_shot_home[home]+=factor*goal_home
                team_conceded_home[home]+=factor*goal_away
            if not away in team_shot_away:
                team_shot_away[away]=factor*goal_away
                team_conceded_away[away]=factor*goal_home
            else:
                team_shot_away[away]+=factor*goal_away
                team_conceded_away[away]+=factor*goal_home
            
        h.close()
    
    league_stats["shot_home_avg"]/=len(home_teams)
    league_stats["shot_away_avg"]/=len(away_teams)
    home_att_strength = {}
    home_def_strength = {}
    away_att_strength = {}
    away_def_strength = {}

    #calucalting defence and attack strength for each team
    for k in team_shot_home.keys():
        k_home = home_teams.count(k)
        k_away = away_teams.count(k)
        home_att_strength[k] = (team_shot_home[k])/(k_home*league_stats['shot_home_avg'])
        home_def_strength[k] = (team_conceded_home[k])/(k_home*league_stats['shot_away_avg'])
        away_att_strength[k] = (team_shot_away[k])/(k_away*league_stats['shot_away_avg'])
        away_def_strength[k] = (team_conceded_home[k])/(k_away*league_stats['shot_home_avg'])

    return league_stats, home_att_strength, home_def_strength, away_att_strength, away_def_strength
    

def display_matchday(a, n, weighted):
    league_stats, home_att_strength, home_def_strength, away_att_strength, away_def_strength = initialize(a, weighted)
    current = open(f"{league}_matchdays/{str(a)}", "r", encoding='utf-8')
    col1, col2 = st.columns(2)
    col_list = [col1, col2]
        
    for match, col in zip(current, cycle(col_list)):
        home_team = match.strip().split("-")[0]
        away_team = match.strip().split("-")[1]
        rng = np.random.default_rng()
        results = []
        home = home_att_strength[home_team]*away_def_strength[away_team]*league_stats['shot_home_avg']
        away = home_def_strength[home_team]*away_att_strength[away_team]*league_stats['shot_away_avg']
        #st.write("\n\n\n")
        with col:
            st.subheader(f"{home_team} vs {away_team}", divider="blue")
            st.write("Siła:", round(home,4), round(away,4))
            simulations = 10**n
            for i in range(simulations):
                results.append((int(rng.poisson(home, 1)[0]),int(rng.poisson(away, 1)[0])))
            st.write("Prawdopodobieństwo czystego konta gospodarza:", round(sum(x[1]==0 for x in results)/simulations, 4))
            st.write("Prawdopodobieństwo czystego konta gościa:", round(sum(x[0]==0 for x in results)/simulations, 4))
            st.write("Najbardziej prawdopodobne wyniki:")
            results = Counter(results).most_common(5)
            for i in results:
                st.write(f"Wynik: **{i[0][0]}-{i[0][1]}**, Częstość: {i[1]} / {simulations}")
    current.close()

sys.path.append("ekstraklasa_matchdays")
sys.path.append("1liga_matchdays")

st.set_page_config(layout="wide", page_title="Polish Leagues Model")
st.header("Poisson model for Polish Leagues results prediction", divider="red")
st.sidebar.title("Parameters")
n = st.sidebar.slider('Select number of simulations (10^n):', value=4, min_value=1, max_value=10, step=1, disabled=False)
matchday = st.sidebar.number_input("Select matchday:", min_value=2, max_value=34, step=1, disabled=False)
league = st.sidebar.selectbox("Select league:", ['ekstraklasa', '1liga'], disabled=False)
weighted = st.sidebar.checkbox("form considering", value=True, disabled=False)

button = st.sidebar.button('Confirm', disabled=False)
if button:
    display_matchday(matchday, n, weighted)
    
