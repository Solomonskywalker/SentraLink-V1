import psycopg2
import folium
from folium.plugins import HeatMap

# 1. Connect
conn = psycopg2.connect(dbname="sentralink_startup", user="solomon")
cur = conn.cursor()

# 2. Query using your specific column names from image_697fde.png
cur.execute("""
    SELECT lat, lon, callsign, altitude_ft, ground_speed_kts 
    FROM live_flights 
    WHERE lat IS NOT NULL AND lon IS NOT NULL
    ORDER BY captured_at DESC 
    LIMIT 500
""")
data = cur.fetchall()

# 3. Create Map (Centered on Cyprus)
m = folium.Map(location=[35.1264, 33.4299], zoom_start=8, tiles="CartoDB dark_matter")

# 4. Create a list for the Heatmap layer
heat_data = [[float(row[0]), float(row[1])] for row in data]

# 5. Add a Heatmap layer (shows density)
HeatMap(heat_data).add_to(m)

# 6. Add individual markers (clickable popups)
for lat, lon, call, alt, spd in data:
    folium.CircleMarker(
        location=[lat, lon],
        radius=2,
        color="lime",
        fill=True,
        popup=f"Flight: {call}<br>Alt: {alt}<br>Spd: {spd} kts"
    ).add_to(m)

# 7. Save
m.save("cyprus_airspace_viz.html")
print("Map successful! Open 'cyprus_airspace_viz.html' in your browser.")
conn.close()