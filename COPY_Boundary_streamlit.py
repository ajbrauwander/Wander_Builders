import streamlit as st
import osmnx as ox
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


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

def get_counts(multipolygon):
    # Get the counts of each type of Point of Interest (POI)
    types = ['tourism', 'camp_site']
    poi_counts = {}
    for t in types:
        gdf = ox.geometries_from_polygon(multipolygon, tags={t: True})
        poi_counts[t] = len(gdf)

    return poi_counts

def get_street_counts(address):
    # Create the street network within the given address
    G = ox.graph_from_place(address, custom_filter='["highway"~"footway|path|cycleway|track"]', retain_all=True)
    
    # Convert the street network to a geopandas GeoDataFrame
    edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    
    # Get the counts of each type of street
    street_counts = edges['highway'].apply(lambda x: str(x)).value_counts().to_dict()

    # Create a bar plot of the counts
    plt.figure(figsize=(5, 3))
    sns.barplot(x=list(street_counts.keys()), y=list(street_counts.values()))
    plt.title('Count of Each Street Type')
    plt.xlabel('Street Type')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    st.pyplot(plt)
    plt.clf()  # Clear the current figure after it is displayed

    # Create a pie chart of the counts
    fig, ax = plt.subplots(figsize=(5, 3))
    wedges, _ = ax.pie(street_counts.values(), wedgeprops=dict(width=0.3), startangle=-40)

    # Create a legend
    ax.legend(wedges, street_counts.keys(),
              title="Street Types",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))

    ax.set_title('Distribution of Street Types')
    st.pyplot(fig)

    return street_counts


st.title('Wander Builders')
address = st.text_input("Enter an address:")

if st.button('Plot'):
    try:
        coordinates, multipolygon = get_geometry(address)
        # street_counts, poi_counts = get_counts(multipolygon)

        m = folium.Map(location=[coordinates[0][1], coordinates[0][0]], zoom_start=9, tiles='Stamen Terrain')
        folium.Polygon(locations=[[coord[1], coord[0]] for coord in coordinates],
                    color='blue', fill=True).add_to(m)

        col1, col2, col3 = st.columns([1,6,1])

        with col2:
            folium_static(m)

        if coordinates is not None:
            st.text("Geometry:")
            st.text_area("", value=str(coordinates), height=150)

        poi_counts = get_counts(multipolygon)

        st.sidebar.header("Counts")
        for category, count in poi_counts.items():
            st.sidebar.markdown(f"**{category.capitalize()}:**", unsafe_allow_html=True)
            st.sidebar.markdown(f"<font color='lightblue' size=4>{count}</font>", unsafe_allow_html=True)
        
        street_counts = get_street_counts(address)

        st.sidebar.header("Street Counts")
        for street_type, count in street_counts.items():
            st.sidebar.markdown(f"**{street_type.capitalize()}:**", unsafe_allow_html=True)
            st.sidebar.markdown(f"<font color='lightblue' size=4>{count}</font>", unsafe_allow_html=True)



    except Exception as e:
        st.text("An error occurred:")
        st.text(e)


