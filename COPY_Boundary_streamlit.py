

import streamlit as st
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import style
# from streamlit_folium import folium_static
# from streamlit_folium import st_folium
# import folium
import pandas as pd

# Function to get geometry from address
def get_geometry(address):
    city = ox.geocode_to_gdf(address)
    multipolygon = city.geometry.iloc[0]
    coordinates = []

    if multipolygon.geom_type == 'Polygon':
        coordinates = [list(coord) for coord in multipolygon.exterior.coords]
    elif multipolygon.geom_type == 'MultiPolygon':
        for polygon in multipolygon:
            coordinates.extend([list(coord) for coord in polygon.exterior.coords])
    else:
        raise ValueError("Unsupported geometry type: {}".format(multipolygon.geom_type))
    
    return coordinates, multipolygon

def plot_polygon(coordinates, multipolygon):
    fig, ax = plt.subplots()

    # Plot polygon
    polygon_gdf = gpd.GeoDataFrame(index=[0], geometry=[multipolygon])
    polygon_gdf.plot(ax=ax, color='blue')

    # Plot centroid
    centroid = multipolygon.centroid
    ax.plot(centroid.x, centroid.y, 'ro')

    plt.title('Polygon')
    st.pyplot(fig)


# Function to get counts of street types
def get_street_counts(G):
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    return edges['highway'].value_counts()

# Function to get counts of specified amenities
def get_amenities_counts(multipolygon, amenities):
    amenities_counts = {}
    for amenity in amenities:
        try:
            amenities_gdf = ox.geometries_from_polygon(multipolygon, tags={'amenity': amenity})
            amenities_counts[amenity] = len(amenities_gdf)
        except Exception as e:
            amenities_counts[amenity] = str(e)
    return pd.Series(amenities_counts)

def get_additional_details():
    multipolygon = st.session_state['multipolygon']

    G = ox.graph_from_polygon(multipolygon, network_type='drive')
    street_counts = get_street_counts(G)

    # Display street counts
    st.sidebar.markdown("<h1 style='color: red;'>Street Counts</h1>", unsafe_allow_html=True)
    for index, value in street_counts.iteritems():
        st.sidebar.markdown(f"<p style='font-weight:bold;color:white;'>{index}</p><p style='font-weight:bold;color:lightblue;'>{value}</p>", unsafe_allow_html=True)

    # Display amenities counts
    amenities = ['camp_site', 'school', 'bus_stop', 'hospital', 'hotel', 'motel', 'bar', 'biergarten', 'cafe', 'fast_food', 'food_court', 'ice_cream', 
                #  'pub', 'community_centre', 'events_venue', 'social_centre', 'police', 'ranger_station', 'drinking_water', 'dog_toilet', 'shelter',
                #  'telephone', 'toilets', 'animal_boarding', 'childcare', 'hunting_stand'
                 ]
    
    amenities_counts = get_amenities_counts(multipolygon, amenities)
    st.sidebar.markdown("<h1 style='color: red;'>Amenities Counts</h1>", unsafe_allow_html=True)
    for index, value in amenities_counts.iteritems():
        st.sidebar.markdown(f"<p style='font-weight:bold;color:white;'>{index}</p><p style='font-weight:bold;color:lightblue;'>{value}</p>", unsafe_allow_html=True)

    # Bar chart for street counts
    fig, ax = plt.subplots(figsize=(8,6))
    ax.bar(street_counts.index.map(str), street_counts.values)  # Convert index to string
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # Pie chart for street counts
    fig1, ax1 = plt.subplots(figsize=(5,3))
    wedges, _ = ax1.pie(street_counts.values, wedgeprops=dict(width=0.3), startangle=-40)
    ax1.legend(wedges, street_counts.index.map(str), title="Street Types", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    ax1.set_title('Distribution of Street Types')
    st.pyplot(fig1)

st.title('Wander Builders')
address = st.text_input("Enter an address:")

coordinates = None
multipolygon = None

if st.button('Plot'):
    try:
        coordinates, multipolygon = get_geometry(address)
        plot_polygon(coordinates, multipolygon)
        st.text("Geometry:")
        st.text_area("", value=str(coordinates), height=150)
        st.session_state['multipolygon'] = multipolygon

    except Exception as e:
        st.text("An error occurred:")
        st.text(e)

if st.button("Get Additional Details"):
    get_additional_details()
