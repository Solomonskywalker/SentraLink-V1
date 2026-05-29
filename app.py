import streamlit as st
import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv
import pydeck as pdk
import numpy as np
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import time



static_container = st.container()
live_container = st.container()

#loading environmental variables
load_dotenv("/home/solomon/Documents/Software Engineering/SentraLink/V1/.env")



# auto refresh
st_autorefresh(interval=5000, key="refresh")

def get_connection():
    """ database parameters"""
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )


query = """
    SELECT COUNT(DISTINCT icao24)
    FROM live_flights WHERE captured_at >= NOW() - INTERVAL '5 minutes';
    """
query2 = """
  SELECT date_trunc('hour', captured_at) AS hour, COUNT(DISTINCT icao24) AS flights FROM live_flights
  GROUP BY hour
  ORDER BY hour;
 """
query3 = """
 SELECT
     ROUND(lat::numeric, 1) AS lat_bin,
     ROUND(lon::numeric, 1) AS lon_bin,
     COUNT(*) AS density FROM live_flights 
     GROUP BY lat_bin, lon_bin ORDER BY density DESC
     Limit 10;
     """

@st.cache_data(ttl=300)  # refresh every 5 minutes
def load_static_data():
    conn = get_connection()

    df = pd.read_sql(query, conn)
    df2 = pd.read_sql(query2, conn)
    df3 = pd.read_sql(query3, conn)

    conn.close()
    return df, df2, df3
df, df2, df3 = load_static_data()

# Ensure correct data types, columns into numeric type
df3["lat_bin"] = df3["lat_bin"].astype(float)
df3["lon_bin"] = df3["lon_bin"].astype(float)
df3["density"] = df3["density"].astype(float)
# scatterplot, places with high density aircraft
df3["scaled"] = np.log1p(df3["density"]) * 1000

print(df3)

#the map of our current location
view_state = pdk.ViewState(
    latitude=35.0,
    longitude=32.0,
    zoom=6,
)

# what to draw on the map
layer = (
    pdk.Layer(
        "ScatterplotLayer",
        data=df3,
        get_position='[lon_bin, lat_bin]',
        get_radius='scaled',  # siz of circle
        get_fill_color='[255, 140, 0, 160]',  # orange color
        pickable=True
    ))


with static_container:
    #page title
    st.title("SentraLink Airspace Intelligence")

    active_aircraft = df.iloc[0, 0]
    st.metric("Active Aircraft (Last 5 minutes)", active_aircraft)

    # subheading of the line line_chart
    st.subheader("Flights per Hour")
    st.line_chart(df2.set_index("hour"))
    #display first few row in streamlit
    st.sidebar.write("Sample Data")
    st.sidebar.dataframe(df3.head())


def compute_vector(lat, lon, track, speed):
    try:
        if pd.isna(track) or pd.isna(speed):
            return [lat, lon]

        angle = np.radians(track)
        distance = min(speed * 0.00001, 0.5)

        new_lat = lat + distance * np.cos(angle)
        new_lon = lon + (distance * np.sin(angle) / np.cos(np.radians(lat)))
        return [new_lat, new_lon]
    except Exception:
        return [lat, lon]


with live_container:
    st.subheader("Live Aircraft Position")

    conn = get_connection()
    query_live = """
    SELECT DISTINCT ON (icao24)
     icao24, lat, lon, altitude_ft, ground_speed_kts, captured_at, track
     FROM live_flights
     WHERE captured_at >= NOW() - INTERVAL '30 seconds'
     """
    #load live data
    df_live = pd.read_sql(query_live, conn)
    conn.close()

    # we clean the data
    df_live = df_live.dropna(subset=["lat", "lon"])
    df_live["lat"]=df_live["lat"].astype(float)
    df_live["lon"]=df_live["lon"].astype(float)

   # st.write("DEBUG:", df_live[["track", "ground_speed_kts"]].head())
    df_live = df_live.dropna(subset=["track", "ground_speed_kts"])

    # store result into two rows
    if not df_live.empty:
        df_live[["end_lat", "end_lon"]] = pd.DataFrame(
            df_live.apply(
            lambda r: compute_vector(
                r["lat"], r["lon"], r.get("track"), r.get("ground_speed_kts")
            ),
            axis=1,
            ).tolist(),
            index=df_live.index
        )



    #what to draw on the live_flight map
    layer_live = pdk.Layer(
       "ScatterplotLayer",
        data=df_live,
        get_position='[lon, lat]',
        get_radius=1500,
        get_fill_color='[0, 200, 255, 180]',
        pickable=True,

    )

    layer_direction = pdk.Layer(
        "LineLayer",
        data=df_live,
        get_source_position='[lon, lat]',
        get_target_postion='[end_lon, end_lat]',
        get_color='[0, 255, 0, 120]',
        get_width=2,

    )

    # what to draw, where to draw and get details of any aircraft when you hover on a circle
    deck = pdk.Deck(
        layers = [layer, layer_live, layer_direction],
        initial_view_state=view_state,
        tooltip={
            "html": """
            <b>ICAO:</b> {icao24} <br />
            Altitude: {altitude_ft} <br />
            Speed: {ground_speed_kts}
            Heading: {track}°
            """,
            "style": {"color": "white"}

    }
    )

    st.pydeck_chart(deck)
    st.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")




