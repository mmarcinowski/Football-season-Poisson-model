import streamlit as st
import streamlit_option_menu
from streamlit_option_menu import option_menu
import numpy as np
import pandas as pd
from collections import Counter
import os
import sys
from itertools import cycle
import altair as alt
import matplotlib.pyplot as plt


def initialize(now, weighted, league):
    # structures for collecting data: goals shot and conceded, no. of matches played home and away, whole league shot and conceded
    team_shot_home, team_conceded_home, team_shot_away, team_conceded_away = {}, {}, {}, {}
    home_teams, away_teams = [], []
    league_stats = {'shot_home_avg': 0, 'shot_away_avg':0}

    # appending data to strcutures for all matchdays till the chosen one
    matchdays_played = [int(m) for m in os.listdir(f"{league}_matchdays") if int(m)<int(now)]
    
    for m in matchdays_played:
        factor = 1 if not weighted else int(m)
        h = open_matchday(m, league)
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

    # calucalting defence and attack strength for each team
    for k in team_shot_home.keys():
        k_home = home_teams.count(k)
        k_away = away_teams.count(k)
        home_att_strength[k] = (team_shot_home[k])/(k_home*league_stats['shot_home_avg'])
        home_def_strength[k] = (team_conceded_home[k])/(k_home*league_stats['shot_away_avg'])
        away_att_strength[k] = (team_shot_away[k])/(k_away*league_stats['shot_away_avg'])
        away_def_strength[k] = (team_conceded_home[k])/(k_away*league_stats['shot_home_avg'])

    return league_stats, home_att_strength, home_def_strength, away_att_strength, away_def_strength


def calculate_match(league_stats, home_att_strength, home_def_strength, away_att_strength, away_def_strength, match, simulations, n=0):
    # calculate all match-result-factors 
    home_team = match.strip().split("-")[0]
    away_team = match.strip().split("-")[1]
    rng = np.random.default_rng()
    results = []
    home = home_att_strength[home_team]*away_def_strength[away_team]*league_stats['shot_home_avg']
    away = home_def_strength[home_team]*away_att_strength[away_team]*league_stats['shot_away_avg']
    for i in range(simulations):
        results.append((int(rng.poisson(home, 1)[0]),int(rng.poisson(away, 1)[0])))
    if n!=0:
        probable = Counter(results).most_common(n)
    else:
        probable = Counter(results).most_common()
    return home_team, away_team, home, away, results, probable


def open_matchday(a, league):
    matchday = open(f"{league}_matchdays/{str(a)}", "r", encoding='utf-8')
    return matchday


def display_matchday(a, n, weighted, league):
    # display whole matchday
    current = open_matchday(a, league)
    col1, col2 = st.columns(2)
    col_list = [col1, col2]
    sim = 10**n
    stats, h_a_s, h_d_s, a_a_s, a_d_s = initialize(a, weighted, league)
    for match, col in zip(current, cycle(col_list)):
        home_team, away_team, home, away, results, probable = calculate_match(stats, h_a_s, h_d_s, a_a_s, a_d_s, match, sim, 5)
        with col:
            st.subheader(f"{home_team} vs {away_team}", divider="blue")
            st.write("Siła:", round(home,4), round(away,4))
            st.write("Prawdopodobieństwo czystego konta gospodarza:", round(sum(x[1]==0 for x in results)/sim, 4))
            st.write("Prawdopodobieństwo czystego konta gościa:", round(sum(x[0]==0 for x in results)/sim, 4))
            st.write("Najbardziej prawdopodobne wyniki:")
            for i in probable:
                st.write(f"Wynik: **{i[0][0]}-{i[0][1]}**, Częstość: {i[1]} / {sim}")
    current.close()


def evaluate(now, sim, league):
    total_confidence, total_position, total_confidence_w, total_position_w = [], [], [], []
    for i in range(2,now):
        confidence, position, confidence_w, position_w = 0, 0, 0, 0
        matchday = open_matchday(i, league)
        stats, h_a_s, h_d_s, a_a_s, a_d_s = initialize(now, False, league)
        stats_w, h_a_s_w, h_d_s_w, a_a_s_w, a_d_s_w = initialize(now, True, league) 
        match_no = 0
        for match in matchday:
            match_no+=1
            _, _, _, _, _, probable = calculate_match(stats, h_a_s, h_d_s, a_a_s, a_d_s, match, sim)
            _, _, _, _, _, probable_w = calculate_match(stats_w, h_a_s_w, h_d_s_w, a_a_s_w, a_d_s_w, match, sim)
            _, _, real_goal_home, real_goal_away = match.strip().split("-")
            x = (int(real_goal_home), int(real_goal_away))
            for i in probable:
                if i[0] == x:
                    confidence+=i[1]
                    position+=(probable.index(i)+1)
                    break
            for i in probable_w:
                if i[0] == x:
                    confidence_w+=i[1]
                    position_w+=(probable_w.index(i)+1)
                    break     
        total_confidence.append(round((confidence/(sim*match_no)),4))
        total_position.append(position/match_no)
        total_confidence_w.append(round((confidence_w/(sim*match_no)),4))
        total_position_w.append(position_w/match_no)
        matchday.close()
    data_conf = pd.DataFrame({"matchday": list(range(2,now)), "no": total_confidence, "yes": total_confidence_w})
    data_pos = pd.DataFrame({"matchday": list(range(2,now)), "no": total_position, "yes": total_position_w})
    return data_conf, data_pos

sys.path.append("ekstraklasa_matchdays")
sys.path.append("1liga_matchdays")

st.set_page_config(layout="wide", page_title="Polish Leagues Model")
st.header("Poisson model for Polish Leagues results prediction", divider="red")

with st.sidebar:
    selected = option_menu(
        menu_title = "",
        options = ["Prediction","Evaluation"],
        icons = ["gear","graph-up"],
        menu_icon = "cast",
        default_index = 0
    )

if selected == "Prediction":
    st.sidebar.title("Parameters")
    n = st.sidebar.slider('Select number of simulations (10^n):', value=4, min_value=1, max_value=10, step=1, disabled=False)
    matchday = st.sidebar.number_input("Select matchday:", min_value=2, max_value=34, step=1, disabled=False)
    league = st.sidebar.selectbox("Select league:", ['ekstraklasa', '1liga'], disabled=False)
    weighted = st.sidebar.checkbox("teams' forms considering", value=True, disabled=False)
    button = st.sidebar.button('Confirm', disabled=False)
    if button:
        display_matchday(matchday, n, weighted, league)
if selected == "Evaluation":
    st.sidebar.title("Evaluate")
    n = st.sidebar.slider('Select number of simulations (10^n):', value=3, min_value=1, max_value=10, step=1, disabled=False)
    now = st.sidebar.number_input("Select actual matchday:", min_value=2, max_value=34, step=1, value=19, disabled=False)
    league = st.sidebar.selectbox("Select league:", ['ekstraklasa', '1liga'], disabled=False)
    sim =  10**n
    data_conf, data_pos = evaluate(now, sim, league)
    col1, col2 = st.columns(2)
    with col1:
        chart = alt.Chart(data_conf).mark_line(point=True).encode(x="matchday", y = alt.Y('Confidence:Q'), color='Form considering:N').transform_fold(
            ['yes', 'no'], as_=['Form considering', 'Confidence']).properties(width=750, height=600, title="Average confidence for correct result").interactive()
        st.altair_chart(chart)
    with col2:
        chart2 = alt.Chart(data_pos).mark_line(point=True).encode(x="matchday", y = alt.Y('Position:Q', scale=alt.Scale(reverse=True)), color='Form considering:N').transform_fold(
            ['yes', 'no'], as_=['Form considering', 'Position']).properties(width=750, height=600, title="Average position of correct result in ranking").interactive()
        st.altair_chart(chart2)

# czyste konto - średni błąd (odległość od 1 gdy było czyste i od 0 gdy nie było)
