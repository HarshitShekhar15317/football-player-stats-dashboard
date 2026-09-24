import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Load & Prepare Data 
file_path = "players_data-2024_2025.csv"
try:
    df = pd.read_csv(file_path, encoding='utf-8')
except UnicodeDecodeError:
    df = pd.read_csv(file_path, encoding='latin1')

df['Min'] = pd.to_numeric(df['Min'], errors='coerce')
df = df.dropna(subset=['Player', 'Squad', 'Pos', 'Comp'], how='any')

# Sidebar Filters
st.sidebar.header("Filters")

leagues = ['All'] + sorted(df['Comp'].dropna().unique().tolist())
selected_league = st.sidebar.selectbox("League", leagues, index=0)

positions = ['All'] + sorted(df['Pos'].dropna().unique().tolist())
selected_pos = st.sidebar.selectbox("Position", positions, index=0)

player_search = st.sidebar.text_input("Search Player Name (partial match)").strip()

top_n = st.sidebar.slider("Number of players in leaderboards", 5, 50, 10, step=5)
st.sidebar.markdown(f"Showing **top {top_n}** in each leaderboard")

# Apply search first (on full df)
if player_search:
    df = df[df['Player'].str.contains(player_search, case=False, na=False)]

# Then apply league/pos filters
filtered_df = df.copy()
if selected_league != 'All':
    filtered_df = filtered_df[filtered_df['Comp'] == selected_league]
if selected_pos != 'All':
    filtered_df = filtered_df[filtered_df['Pos'] == selected_pos]

outfield = filtered_df[filtered_df['Pos'] != 'GK']
outfield = outfield[outfield['Min'] >= 500]

gks = filtered_df[filtered_df['Pos'].str.contains('GK', na=False)]
gks = gks[gks['Min'] >= 500]

st.title("Football Player Stats Dashboard 2024-2025")
st.markdown(f"Big 5 Leagues – FBref | Showing **{len(filtered_df)}** players after filters/search")

if len(filtered_df) == 0:
    st.error("No players match your filters/search. Try broader options.")
    st.stop()

# Player Search Details Section 
if player_search and not filtered_df.empty:
    st.subheader(f"Player Details for '{player_search}' Matches")
    for idx, player in filtered_df.iterrows():
        with st.expander(f"{player['Player']} ({player['Squad']}, {player['Pos']})"):
            stats = {
                "Name": player['Player'],
                "Nationality": player.get('Nation', 'N/A'),
                "Age": player.get('Age', 'N/A'),
                "Club": player['Squad'],
                "Position": player['Pos'],
                "League": player['Comp'],
                "Minutes Played": player['Min'],
                "Goals": player.get('Gls', 0),
                "Assists": player.get('Ast', 0),
                "Expected Goals (xG)": player.get('xG', 0),
                "Key Passes (KP)": player.get('KP', 0),
                "Progressive Passes (PrgP)": player.get('PrgP', 0),
                "Passes into Final Third (1/3)": player.get('1/3', 0),
                "Progressive Runs/Carries (PrgR)": player.get('PrgR', 0),
                "Touches in Attacking Third (Att 3rd)": player.get('Att 3rd', 0),
                "Tackles (Tkl)": player.get('Tkl', 0),
                "Clearances (Clr)": player.get('Clr', 0),
                "Interceptions (Int)": player.get('Int', 0),
                "Clean Sheets (CS - GK only)": player.get('CS', 'N/A'),
            }
            st.table(pd.DataFrame.from_dict(stats, orient='index', columns=['Value']))

# Player Comparison Radar Chart 
st.subheader("Player Comparison Radar Chart (All Stats)")

if not outfield.empty:
    player_options = sorted(outfield['Player'].unique())
    col1, col2 = st.columns(2)
    player1 = col1.selectbox("Player 1", player_options, index=0)
    player2 = col2.selectbox("Player 2", player_options, index=min(1, len(player_options)-1))

    if player1 and player2 and player1 != player2:
        p1 = outfield[outfield['Player'] == player1].iloc[0]
        p2 = outfield[outfield['Player'] == player2].iloc[0]

        # All leaderboard stats (per 90)
        categories = [
            'Goals/90', 'Assists/90', 'Key Passes/90', 'Passes Final Third/90',
            'Progressive Passes/90', 'Progressive Runs/90', 'Touches Att 3rd/90',
            'Tackles/90', 'Clearances/90', 'Interceptions/90'
        ]

        def get_per90(row, stat, minutes_col='Min'):
            if minutes_col in row and row[minutes_col] > 0:
                return row.get(stat, 0) / (row[minutes_col] / 90)
            return 0

        vals1 = [
            get_per90(p1, 'Gls'), get_per90(p1, 'Ast'), get_per90(p1, 'KP'), get_per90(p1, '1/3'),
            get_per90(p1, 'PrgP'), get_per90(p1, 'PrgR'), get_per90(p1, 'Att 3rd'),
            get_per90(p1, 'Tkl'), get_per90(p1, 'Clr'), get_per90(p1, 'Int')
        ]

        vals2 = [
            get_per90(p2, 'Gls'), get_per90(p2, 'Ast'), get_per90(p2, 'KP'), get_per90(p2, '1/3'),
            get_per90(p2, 'PrgP'), get_per90(p2, 'PrgR'), get_per90(p2, 'Att 3rd'),
            get_per90(p2, 'Tkl'), get_per90(p2, 'Clr'), get_per90(p2, 'Int')
        ]

        # Normalize to 0-100 (percentile within filtered outfield)
        per90_df = outfield.copy()
        stats_cols = ['Gls', 'Ast', 'KP', '1/3', 'PrgP', 'PrgR', 'Att 3rd', 'Tkl', 'Clr', 'Int']
        for col in stats_cols:
            if col in per90_df.columns:
                per90_df[col + '/90'] = per90_df[col] / (per90_df['Min'] / 90)

        max_vals = per90_df[[c + '/90' for c in stats_cols if c in outfield.columns]].max()

        norm_vals1 = [min(v / m * 100 if m > 0 else 0, 100) for v, m in zip(vals1, max_vals)]
        norm_vals2 = [min(v / m * 100 if m > 0 else 0, 100) for v, m in zip(vals2, max_vals)]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=norm_vals1 + [norm_vals1[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=player1,
            line_color='blue'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=norm_vals2 + [norm_vals2[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=player2,
            line_color='orange'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            title=f"{player1} vs {player2} (All Stats - per 90, normalized)"
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("Select two different outfield players to compare (all leaderboard stats included).")
else:
    st.info("No outfield players available for comparison.")

# ── Leaderboards ─────────────────────────────────────────────────────────────

# ── Goal Scorers ─────────────────────────────────────────────────────────────
st.subheader(f"Top {top_n} Goal Scorers")
if 'Gls' in outfield.columns:
    top = outfield.sort_values('Gls', ascending=False).head(top_n)
    fig = px.bar(top, x='Gls', y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'Ast', 'xG', 'Comp'],
                 height=500)
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos','Gls','Ast','Min','xG','Comp']].style.format({'Min': '{:.0f}'}))

# ── Assists ──────────────────────────────────────────────────────────────────
st.subheader(f"Top {top_n} Assist Providers")
if 'Ast' in outfield.columns:
    top = outfield.sort_values('Ast', ascending=False).head(top_n)
    fig = px.bar(top, x='Ast', y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'Gls', 'xG', 'Comp'],
                 height=500)
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos','Ast','Gls','Min','xG','Comp']])

# ── Key Passes (Chances Created) ─────────────────────────────────────────────
st.subheader(f"Top {top_n} Chances Created (Key Passes)")
col = 'KP'
if col in outfield.columns:
    top = outfield.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'Ast', 'Gls', 'xAG', 'Comp'],
                 height=500)
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'Ast','Gls','Min','Comp']])

# ── Passes into Final Third ──────────────────────────────────────────────────
st.subheader(f"Top {top_n} Passes into Final Third")
col = '1/3'   # change to correct name if needed (e.g. 'PPA')
if col in outfield.columns:
    top = outfield.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'PrgP', 'KP', 'Ast', 'Comp'],
                 height=500)
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'PrgP','KP','Min','Comp']])

# ── Progressive Passes ───────────────────────────────────────────────────────
st.subheader(f"Top {top_n} Progressive Passes")
col = 'PrgP'
if col in outfield.columns:
    top = outfield.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'KP', 'Ast', 'Comp'],
                 height=500)
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'KP','Ast','Min','Comp']])

# ── Progressive Runs (Off-the-ball proxy) ────────────────────────────────────
st.subheader(f"Top {top_n} Progressive Runs / Carries")
col = 'PrgR'
if col in outfield.columns:
    top = outfield.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'Touches', 'Ast', 'Gls', 'Comp'],
                 height=500)
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'Touches','Min','Comp']])

# ── Touches in Attacking Third ───────────────────────────────────────────────
st.subheader(f"Top {top_n} Touches in Attacking Third")
col = 'Att 3rd'   # or 'TouAtt3rd' if that's the actual name
if col in outfield.columns:
    top = outfield.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'Touches', 'PrgP', 'KP', 'Comp'],
                 height=500)
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'Touches','Min','Comp']])

# ── Defensive Leaderboards ───────────────────────────────────────────────────
st.subheader("Defensive Leaderboards")

# Tackles
col = 'Tkl'
if col in outfield.columns:
    st.markdown(f"**Top {top_n} Tackles**")
    top = outfield.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'Int', 'Clr', 'Comp'],
                 height=500)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'Int','Clr','Min','Comp']])

# Clearances
col = 'Clr'
if col in outfield.columns:
    st.markdown(f"**Top {top_n} Clearances**")
    top = outfield.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'Tkl', 'Int', 'Comp'],
                 height=500)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'Tkl','Int','Min','Comp']])

# Interceptions
col = 'Int'
if col in outfield.columns:
    st.markdown(f"**Top {top_n} Interceptions**")
    top = outfield.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'Tkl', 'Clr', 'Comp'],
                 height=500)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'Tkl','Clr','Min','Comp']])

# ── GK Clean Sheets ──────────────────────────────────────────────────────────
st.subheader(f"Top {top_n} Goalkeepers - Clean Sheets")
col = 'CS'
if col in gks.columns and not gks.empty:
    top = gks.sort_values(col, ascending=False).head(top_n)
    fig = px.bar(top, x=col, y='Player', color='Squad',
                 hover_data=['Pos', 'Min', 'GA', 'Save%', 'Comp'],
                 height=500)
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(top[['Player','Squad','Pos',col,'Min','GA','Comp']].style.format({'Min': '{:.0f}'}))

