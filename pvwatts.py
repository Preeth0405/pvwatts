import streamlit as st
import plotly.express as px
import requests
import pandas as pd
import hashlib
import json
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("⚡ NREL PVWatts AC Energy Simulator")

# --- Login System ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

users = {"admin": hash_password("123")}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

def login():
    with st.form("Login"):
        st.write("🔐 Please login to access the app")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if username in users and users[username] == hash_password(password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("✅ Logged in successfully!")
                st.stop()
            else:
                st.error("❌ Invalid credentials")

def logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.experimental_rerun()

# Display login/logout
if st.session_state.authenticated:
    st.sidebar.write(f"👋 Logged in as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        logout()
else:
    login()
    st.stop()

# 📍 Location Input
st.header("📍 Site Location Input")
location_mode = st.radio("Select location input method", ["Enter Coordinates", "Search by Address"])
lat, lon = None, None
map_ready = False

if location_mode == "Enter Coordinates":
    lat = st.number_input("Latitude", value=51.5074, format="%.6f", key="lat")
    lon = st.number_input("Longitude", value=-0.1278, format="%.6f", key="lon")
    map_ready = True
else:
    address = st.text_input("Enter Address", value="London, UK", key="address")
    if address:
        headers = {"User-Agent": "pvwatts-app/1.0 (your_email@example.com)"}
        geo_url = f"https://nominatim.openstreetmap.org/search?format=json&q={address}"
        geo_response = requests.get(geo_url, headers=headers)

        if geo_response.status_code == 200:
            try:
                geo_data = geo_response.json()
                if geo_data:
                    lat = float(geo_data[0]['lat'])
                    lon = float(geo_data[0]['lon'])
                    st.success(f"📌 Found: {geo_data[0]['display_name']}")
                    st.write(f"**Latitude**: {lat:.6f}, **Longitude**: {lon:.6f}")
                    map_ready = True
                else:
                    st.warning("⚠️ Address not found.")
            except ValueError:
                st.error("❌ Failed to decode location data.")
        else:
            st.error(f"❌ Geolocation API error: {geo_response.status_code}")

if map_ready:
    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))

# 🔧 PV System Inputs
st.sidebar.header("🔧 PV System Parameters")
peak_power_kw = st.sidebar.number_input("Installed PV Power (kWp)", 0.1, 10000.0, 5.0, key="pv")
panel_type = st.sidebar.selectbox("Module Type", [0, 1, 2], help="0: Standard, 1: Premium, 2: Thin Film", key="type")
system_loss_pct = st.sidebar.slider("System Loss (%)", 0, 30, 14, key="loss")
mounting = st.sidebar.selectbox("Mounting Type", [0, 1, 2, 3, 4], help="0: Rack, 1: Roof, etc.", key="mount")
tilt = st.sidebar.slider("Tilt Angle (°)", 0, 60, 35, key="tilt")
azimuth = st.sidebar.slider("Azimuth (°)", 0, 360, 180, key="az")
inverter_ratio = st.sidebar.number_input("DC/AC Ratio", 0.1, 2.0, 1.0, key="ratio")
interval = st.sidebar.selectbox("Granularity", ["monthly", "hourly"], key="interval")
dataset = st.sidebar.selectbox("Dataset", ["nsrdb", "tmy2", "tmy3", "intl"], key="ds")
radius = st.sidebar.slider("Search Radius (miles)", 1, 100, 25, key="radius")
inv = st.sidebar.number_input("Inverter Efficiency (%)", 96.0, 99.5, 96.0, 0.1, key="inv")

# Save Input Button (only for logged in user)
if st.sidebar.button("💾 Save Inputs to JSON"):
    inputs_dict = {
        "Latitude": lat,
        "Longitude": lon,
        "PV Size (kWp)": peak_power_kw,
        "Module Type": panel_type,
        "System Loss (%)": system_loss_pct,
        "Mounting Type": mounting,
        "Tilt (°)": tilt,
        "Azimuth (°)": azimuth,
        "DC/AC Ratio": inverter_ratio,
        "Interval": interval,
        "Dataset": dataset,
        "Radius": radius,
        "Inverter Efficiency (%)": inv
    }
    st.sidebar.download_button("⬇️ Download JSON", json.dumps(inputs_dict, indent=2), "pvwatts_inputs.json", "application/json")

# 🔐 API Key
api_key = "beHYbrG2eqslmF6pvTx5fOH4WsabCnB3hUedxanX"

# Run Simulation
if st.button("🔍 Run Simulation") and lat is not None and lon is not None:
    with st.spinner("Fetching data from NREL PVWatts..."):
        params = {
            "api_key": api_key,
            "lat": lat,
            "lon": lon,
            "system_capacity": peak_power_kw,
            "module_type": panel_type,
            "losses": system_loss_pct,
            "array_type": mounting,
            "tilt": tilt,
            "azimuth": azimuth,
            "dc_ac_ratio": inverter_ratio,
            "timeframe": interval,
            "format": "json",
            "dataset": dataset,
            "radius": radius,
            "gcr": 0.4,
            "inv_eff": inv,
            "use_wf_albedo": 1
        }

        url = "https://developer.nrel.gov/api/pvwatts/v8.json"
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            outputs = data.get("outputs", {})
            station = data.get("station_info", {})

            if outputs:
                st.success("✅ Simulation Complete!")

                st.subheader("📡 Station Info")
                station_df = pd.DataFrame({
                    "Field": ["City", "State", "Latitude", "Longitude", "Elevation", "Time Zone", "Dataset", "Distance (mi)"],
                    "Value": [
                        station.get("city", ""), station.get("state", ""), station.get("lat", ""),
                        station.get("lon", ""), station.get("elev", ""), station.get("time_zone", ""),
                        station.get("solar_resource_file", ""), station.get("distance", "")
                    ]
                })
                st.table(station_df)

                ac_annual = outputs.get("ac_annual", 0)
                specific_yield = round(ac_annual / peak_power_kw, 2)
                capacity_factor = round(outputs.get("capacity_factor", 0), 2)

                col1, col2, col3 = st.columns(3)
                col1.metric("Total AC Output (kWh)", f"{ac_annual:,.0f}")
                col2.metric("Specific Yield (kWh/kWp)", f"{specific_yield}")
                col3.metric("Capacity Factor (%)", f"{capacity_factor}")

                if interval == "monthly":
                    ac_monthly = outputs["ac_monthly"]
                    monthly_df = pd.DataFrame({
                        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                        "AC Output (kWh)": ac_monthly,
                        "Specific Yield (kWh/kWp)": [round(kwh / peak_power_kw, 2) for kwh in ac_monthly]
                    })
                    fig = px.bar(monthly_df, x="Month", y="AC Output (kWh)", title="📅 Monthly AC Output")
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(monthly_df)

                elif interval == "hourly":
                    ac_hourly = outputs.get("ac", [])
                    dc_hourly = outputs.get("dc", [])
                    tz_offset = station.get("time_zone", 0)
                    start_time = datetime(2024, 1, 1)
                    timestamps = [start_time + timedelta(hours=i) for i in range(len(ac_hourly))]

                    df_hourly = pd.DataFrame({
                        "Timestamp": timestamps,
                        "AC Output (kWh)": ac_hourly,
                        "DC Output (kWh)": dc_hourly,
                        "Specific Yield (kWh/kWp)": [round(kwh / peak_power_kw, 3) for kwh in ac_hourly]
                    })

                    st.subheader("⏱️ Hourly Output Preview")
                    st.dataframe(df_hourly.head(48))

                    st.download_button("📥 Download Full Hourly CSV", df_hourly.to_csv(index=False), "hourly_output.csv", "text/csv")
            else:
                st.error("❌ No outputs returned.")
        else:
            st.error(f"❌ API Error {response.status_code}: {response.text}")
