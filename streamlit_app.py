import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="DCFC Event Data", page_icon="⚽", layout="wide")

st.title("DCFC Event Data")
st.caption("Explore actions on the standardized 105 x 68 meter football pitch.")

PITCH_LENGTH = 105
PITCH_WIDTH = 68
X_OFFSET = PITCH_LENGTH / 2
Y_OFFSET = PITCH_WIDTH / 2

coordinate_columns = [
    "start_adj_coordinates_x",
    "start_adj_coordinates_y",
    "end_adj_coordinates_x",
    "end_adj_coordinates_y",
]
events = pd.read_csv("dcfc_indy_event_data.csv")
for column in [*coordinate_columns, "pressure"]:
    events[column] = pd.to_numeric(events[column], errors="coerce")

events = events.copy()
events = events.assign(
    start_x=events["start_adj_coordinates_x"] + X_OFFSET,
    start_y=events["start_adj_coordinates_y"] + Y_OFFSET,
    end_x=events["end_adj_coordinates_x"] + X_OFFSET,
    end_y=events["end_adj_coordinates_y"] + Y_OFFSET,
)

events = events.dropna(
    subset=[
        "team_name",
        "period_id",
        "action_type",
        "body_part",
        "player_name",
        "start_x",
        "start_y",
    ]
).copy()

teams = sorted(events["team_name"].unique())
action_types = sorted(events["action_type"].unique())
periods = sorted(events["period_id"].unique())
body_parts = sorted(events["body_part"].unique())
players = sorted(events["player_name"].unique())

with st.sidebar:
    st.header("Filters")
    selected_teams = st.multiselect("Team", teams, default=teams)
    selected_periods = st.multiselect("Period", periods, default=periods)
    selected_actions = st.multiselect(
        "Action type", action_types, default=action_types
    )
    selected_body_parts = st.multiselect(
        "Body part", body_parts, default=body_parts
    )
    selected_players = st.multiselect("Player", players, default=players)
    selected_pressure = st.slider(
        "Pressure",
        min_value=0.0,
        max_value=100.0,
        value=(0.0, 100.0),
        step=1.0,
    )

filtered_events = events[
    events["team_name"].isin(selected_teams)
    & events["period_id"].isin(selected_periods)
    & events["action_type"].isin(selected_actions)
    & events["body_part"].isin(selected_body_parts)
    & events["player_name"].isin(selected_players)
    & events["pressure"].fillna(0).between(*selected_pressure)
].reset_index(drop=True)

st.metric("Actions shown", len(filtered_events))
figure = go.Figure()
chart_state = st.session_state.get("event_chart")
selected_points = []
if chart_state:
    selected_points = chart_state.get("selection", {}).get("points", [])
selected_point = selected_points[-1] if selected_points else None
team_colors = {
    team: color
    for team, color in zip(
        teams, ["#d94f4f", "#177e89", "#e09f3e", "#6c63a8"]
    )
}
dark_team_colors = {
    "Detroit City FC": "#8f2424",
    "Indy Eleven": "#0d4f57",
    "Lansing Common FC": "#a56e13",
    "Michigan Stars FC": "#46427a",
}

for team in selected_teams:
    team_events = filtered_events[filtered_events["team_name"] == team]
    if team_events.empty:
        continue

    line_x, line_y, line_hover = [], [], []
    for _, event in team_events.iterrows():
        has_end = pd.notna(event["end_adj_coordinates_x"]) and pd.notna(
            event["end_adj_coordinates_y"]
        )
        if has_end:
            hover_text = (
                f"<b>{event['player_name']}</b><br>"
                f"{event['action_type']} | {event['body_part']}<br>"
                f"{team} | Period {event['period_id']}<br>"
                f"Pressure: {event['pressure']}<br>"
                f"Result: {event['result']}<br>"
                f"Pass receiver type: {event['pass_receiver_type']}<br>"
                f"Start: ({event['start_x']:.1f}, {event['start_y']:.1f}) m<br>"
                f"End: ({event['end_x']:.1f}, {event['end_y']:.1f})"
            )
            line_x.extend(
                [
                    event["start_x"],
                    event["end_x"],
                    None,
                ]
            )
            line_y.extend(
                [
                    event["start_y"],
                    event["end_y"],
                    None,
                ]
            )
            line_hover.extend([hover_text, hover_text, None])

    if line_x:
        figure.add_trace(
            go.Scatter(
                x=line_x,
                y=line_y,
                mode="lines",
                line={"color": team_colors[team], "width": 1.5},
                text=line_hover,
                hoverinfo="text",
                name=f"{team} actions",
                legendgroup=team,
                showlegend=False,
            )
        )

    start_events = team_events
    end_events = team_events[
        team_events["end_x"].notna() & team_events["end_y"].notna()
    ]
    start_hover = [
        f"<b>{event['player_name']}</b><br>"
        f"{event['action_type']} | {event['body_part']}<br>"
        f"{team} | Period {event['period_id']}<br>"
        f"Pressure: {event['pressure']}<br>"
        f"Result: {event['result']}<br>"
        f"Pass receiver type: {event['pass_receiver_type']}<br>"
        f"Start: ({event['start_x']:.1f}, {event['start_y']:.1f}) m"
        for _, event in start_events.iterrows()
    ]
    end_hover = [
        f"<b>{event['player_name']}</b><br>"
        f"{event['action_type']} | {event['body_part']}<br>"
        f"{team} | Period {event['period_id']}<br>"
        f"Pressure: {event['pressure']}<br>"
        f"Result: {event['result']}<br>"
        f"Pass receiver type: {event['pass_receiver_type']}<br>"
        f"End: ({event['end_x']:.1f}, {event['end_y']:.1f}) m"
        for _, event in end_events.iterrows()
    ]

    def selected_points_for_trace(trace_number):
        if not selected_point:
            return None
        if selected_point.get("curve_number") == trace_number:
            return [selected_point["point_number"]]
        return []

    start_trace_number = len(figure.data)
    figure.add_trace(
        go.Scatter(
            x=start_events["start_x"],
            y=start_events["start_y"],
            mode="markers",
            marker={
                "color": team_colors[team],
                "size": 8,
                "line": {"width": 1, "color": "white"},
            },
            selectedpoints=selected_points_for_trace(start_trace_number),
            selected={"marker": {"opacity": 1}},
            unselected={"marker": {"opacity": 0.2}},
            text=start_hover,
            hoverinfo="text",
            name=f"{team} start",
            legendgroup=team,
        )
    )
    end_trace_number = len(figure.data)
    figure.add_trace(
        go.Scatter(
            x=end_events["end_x"],
            y=end_events["end_y"],
            mode="markers",
            marker={
                "color": dark_team_colors.get(team, team_colors[team]),
                "size": 8,
                "line": {"width": 1, "color": "white"},
            },
            selectedpoints=selected_points_for_trace(end_trace_number),
            selected={"marker": {"opacity": 1}},
            unselected={"marker": {"opacity": 0.2}},
            text=end_hover,
            hoverinfo="text",
            name=f"{team} end",
            legendgroup=team,
        )
    )

pitch_shapes = [
    {"type": "rect", "x0": 0, "y0": 0, "x1": PITCH_LENGTH, "y1": PITCH_WIDTH},
    {"type": "line", "x0": X_OFFSET, "y0": 0, "x1": X_OFFSET, "y1": PITCH_WIDTH},
    {"type": "rect", "x0": 0, "y0": 13.84, "x1": 16.5, "y1": 54.16},
    {"type": "rect", "x0": 88.5, "y0": 13.84, "x1": PITCH_LENGTH, "y1": 54.16},
    {"type": "rect", "x0": 0, "y0": 24.84, "x1": 5.5, "y1": 43.16},
    {"type": "rect", "x0": 99.5, "y0": 24.84, "x1": PITCH_LENGTH, "y1": 43.16},
    {"type": "circle", "x0": X_OFFSET - 9.15, "y0": Y_OFFSET - 9.15, "x1": X_OFFSET + 9.15, "y1": Y_OFFSET + 9.15},
]
for shape in pitch_shapes:
    shape.update(line={"color": "#d8e2dc", "width": 2}, fillcolor="rgba(0, 0, 0, 0)")

figure.update_layout(
    height=700,
    plot_bgcolor="#28624f",
    paper_bgcolor="#102a27",
    font={"color": "#f3f7f2"},
    shapes=pitch_shapes,
    xaxis={
        "range": [-2, PITCH_LENGTH + 2],
        "showgrid": False,
        "zeroline": False,
        "title": "Length (m)",
    },
    yaxis={
        "range": [-2, PITCH_WIDTH + 2],
        "showgrid": False,
        "zeroline": False,
        "title": "Width (m)",
        "scaleanchor": "x",
        "scaleratio": 1,
    },
    margin={"l": 20, "r": 20, "t": 30, "b": 20},
    hovermode="closest",
    legend={"orientation": "h", "y": -0.08},
)

if filtered_events.empty:
    st.info("Select at least one value in each filter to show actions.")
else:
    st.plotly_chart(
        figure,
        width="stretch",
        key="event_chart",
        on_select="rerun",
        selection_mode="points",
    )
