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

def initialize(now: int, weighted: str, league: str):
    """
    Initialize structures for collecting data and values: goals shot and conceded, no. of games played home and away,
    whole league shot and conceded
    :param now: match day to analyze
    :param weighted: way of calculating th history of games,
    equally or weighted chronologically with arithmetic or exponential decrease
    :param league: competition to analyze
    :return: all league stats, home teams offensive strength, home teams defensive strengths,
            away teams offensive strengths, away teams defensive strengths
    """
    team_shot_home, team_conceded_home, team_shot_away, team_conceded_away = {}, {}, {}, {}
    home_teams, away_teams = [], []
    league_stats = {'shot_home_avg': 0, 'shot_away_avg':0}
  
    # appending data to structures for all matchdays till the selected one
    matchdays_played = [int(m) for m in os.listdir(f"{league}_matchdays") if int(m)<int(now)]
    
    for m in matchdays_played:
        factor = 1 if weighted=='no' else (int(m) if weighted=='arithmetic' else 2^m)
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

    # calculating defense and attack strength for each team
    for k in team_shot_home.keys():
        k_home = home_teams.count(k)
        k_away = away_teams.count(k)
        home_att_strength[k] = (team_shot_home[k])/(k_home*league_stats['shot_home_avg'])
        home_def_strength[k] = (team_conceded_home[k])/(k_home*league_stats['shot_away_avg'])
        away_att_strength[k] = (team_shot_away[k])/(k_away*league_stats['shot_away_avg'])
        away_def_strength[k] = (team_conceded_home[k])/(k_away*league_stats['shot_home_avg'])

    return league_stats, home_att_strength, home_def_strength, away_att_strength, away_def_strength


def calculate_match(league_stats: list, home_att_strength: dict, home_def_strength: dict, away_att_strength: dict, away_def_strength: dict, match: str, sim: int, n=0):
    """
    Calculate all match-result factors
    :param league_stats: all-league statistics
    :param home_att_strength: strength of home team attack
    :param home_def_strength: strength of home team defense
    :param away_att_strength: strength of away team attack
    :param away_def_strength: strength of away team defense
    :param match:
    :param sim:
    :param n:
    :return: match result factors
    """
    home_team = match.strip().split("-")[0]
    away_team = match.strip().split("-")[1]
    rng = np.random.default_rng()
    results = []
    home = home_att_strength[home_team]*away_def_strength[away_team]*league_stats['shot_home_avg']
    away = home_def_strength[home_team]*away_att_strength[away_team]*league_stats['shot_away_avg']
    for i in range(sim):
        results.append((int(rng.poisson(home, 1)[0]),int(rng.poisson(away, 1)[0])))
    if n!=0:
        probable = Counter(results).most_common(n)
    else:
        probable = Counter(results).most_common()
    return home_team, away_team, home, away, results, probable


def open_matchday(now: int, league: str):
    """
    Open file with games results
    :param now: match day to analyze
    :param league: competition to analyze
    :return: batch of games from the match day
    """
    matchday = open(f"{league}_matchdays/{str(now)}", "r", encoding='utf-8')
    return matchday


def display_matchday(now: int, n: int, weighted: str, league: str, best: int):
    """
    Display selected match day
    :param now: selected match day
    :param n: number of simulations
    :param weighted: way of calculating games history
    :param league: competition
    :param best: no. of most probable games to show
    :return: none
    """
    current = open_matchday(now, league)
    col1, col2 = st.columns(2, border=True)
    col_list = [col1, col2]
    sim = 10**n
    stats, h_a_s, h_d_s, a_a_s, a_d_s = initialize(now, weighted, league)
    for match, col in zip(current, cycle(col_list)):
        home_team, away_team, home, away, results, probable = calculate_match(stats, h_a_s, h_d_s, a_a_s, a_d_s, match, sim, best)
        with col:
            st.subheader(f"{home_team} vs {away_team}", divider="violet")

            indicators_table = pd.DataFrame(
                {
                    f"{home_team}": [round(home,4), f"{round(sum(x[1]==0 for x in results)/sim*100,2)}%"],
                    f"{away_team}": [round(away,4), f"{round(sum(x[0]==0 for x in results)/sim*100,2)}%"]
                },
                index=["Power", "Clean sheet probability"])
            st.table(indicators_table, border="horizontal")
            
            st.markdown(":violet-badge[:material/star: Most probable results]")
            results_table = pd.DataFrame(
                {
                    "Result": [f"**{i[0][0]}-{i[0][1]}**" for i in probable],
                    "Frequency": [f"{i[1]} / {sim}" for i in probable]
                
                },
                index=[str(i+1) for i in range(len(probable))])       
            st.table(results_table, border="horizontal")
    current.close()


def evaluate(now: int, sim: int, league: str):
    """
    Evaluate probabilistic models comparing predicted results with real results
    :param now: last match day of requested analysis
    :param sim: number of simulations
    :param league: competition to analyze
    :return: dataframes with data about predicted confidence and position of real result in predictions
    """
    total_position, total_position_w, total_position_e = [], [], []
    total_confidence, total_confidence_w, total_confidence_e = [], [], []
    # total_clean, total_clean_w, total_clean_e = [], [], []
    for i in range(2, now):
        confidence, confidence_w, confidence_e = 0, 0, 0
        position, position_w, position_e = [], [], []
        matchday = open_matchday(i, league)
        stats, h_a_s, h_d_s, a_a_s, a_d_s = initialize(now, 0, league)
        stats_w, h_a_s_w, h_d_s_w, a_a_s_w, a_d_s_w = initialize(now, 1, league)
        stats_e, h_a_s_e, h_d_s_e, a_a_s_e, a_d_s_e = initialize(now, 2, league)
        match_no = 0
        for match in matchday:
            match_no+=1
            _, _, _, _, _, probable = calculate_match(stats, h_a_s, h_d_s, a_a_s, a_d_s, match, sim)
            _, _, _, _, _, probable_w = calculate_match(stats_w, h_a_s_w, h_d_s_w, a_a_s_w, a_d_s_w, match, sim)
            _, _, _, _, _, probable_e = calculate_match(stats_e, h_a_s_e, h_d_s_e, a_a_s_e, a_d_s_e, match, sim)
            _, _, real_goal_home, real_goal_away = match.strip().split("-")
            x = (int(real_goal_home), int(real_goal_away))
            for j in probable:
                if j[0] == x:
                    confidence+=j[1]
                    position.append(probable.index(j)+1)
                    break
            for j in probable_w:
                if j[0] == x:
                    confidence_w+=j[1]
                    position_w.append(probable_w.index(j)+1)
                    break
            for j in probable_e:
                if j[0] == x:
                    confidence_e+=j[1]
                    position_e.append(probable_e.index(j)+1)
                    break   
        total_confidence.append(round((confidence/(sim*match_no)),4))
        total_position.append(np.median(position))
        total_confidence_w.append(round((confidence_w/(sim*match_no)),4))
        total_position_w.append(np.median(position_w))
        total_confidence_e.append(round((confidence_e/(sim*match_no)),4))
        total_position_e.append(np.median(position_e))
        matchday.close()
    data_confidence = pd.DataFrame({"matchday": list(range(2,now)), "no": total_confidence, "arithmetic": total_confidence_w, "exponential": total_confidence_e})
    data_position = pd.DataFrame({"matchday": list(range(2,now)), "no": total_position, "arithmetic": total_position_w, "exponential": total_position_e})
    # data_clean = pd.DataFrame({"matchday": list(range(2,now)), "no": total_clean, "arithmetic": total_clean_w, "exponential": total_clean_e})
    return data_confidence, data_position #, data_clean

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
    simulations = st.sidebar.slider('Select number of simulations (10^n):', value=3, min_value=1, max_value=10, step=1, disabled=False)
    match_day = st.sidebar.number_input("Select matchday:", min_value=2, max_value=34, value=22, step=1, disabled=False)
    league_chosen = st.sidebar.selectbox("Select league:", ['ekstraklasa', '1liga'], disabled=False)
    weighting_way = st.sidebar.selectbox("Teams form considering:", ['no', 'arithmetic', 'exponential'], disabled=False)
    button = st.sidebar.button('Confirm', disabled=False)
    if button:
        display_matchday(match_day, simulations, weighting_way, league_chosen, 5)

if selected == "Evaluation":
    st.sidebar.title("Evaluate")
    simulations = st.sidebar.slider('Select number of simulations (10^n):', value=3, min_value=1, max_value=10, step=1, disabled=False)
    actual = st.sidebar.number_input("Select actual matchday:", min_value=2, max_value=34, step=1, value=21, disabled=False)
    league_selected = st.sidebar.selectbox("Select league:", ['ekstraklasa', '1liga'], disabled=False)
    data_conf, data_pos = evaluate(actual, 10**simulations, league_selected)
    column1, column2 = st.columns(2)
    with column1:
        chart = alt.Chart(data_conf).mark_line(point=True).encode(x="matchday", y = alt.Y('Confidence:Q'), color='Form considering:N').transform_fold(
            ['arithmetic', 'exponential', 'no'], as_=['Form considering', 'Confidence']).properties(width=750, height=600, title="Average confidence for correct result").interactive()
        st.altair_chart(chart)
    with column2:
        chart2 = alt.Chart(data_pos).mark_line(point=True).encode(x="matchday", y = alt.Y('Position:Q', scale=alt.Scale(reverse=True)), color='Form considering:N').transform_fold(
            ['arithmetic', 'exponential', 'no'], as_=['Form considering', 'Position']).properties(width=750, height=600, title="Median position of correct result in ranking").interactive()
        st.altair_chart(chart2)

# TODO: clean sheet - average error (distance from 1 if clean, from 0 if not)
