import streamlit as st
import geopandas as gpd
import xml.etree.ElementTree as ET
import os
from io import BytesIO
import json
import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib import style
# from streamlit_folium import folium_static
# from streamlit_folium import st_folium
# import folium
import base64
import pandas as pd
import time
from shapely.geometry import Point
import random
from shapely.geometry import MultiLineString, LineString
import shutil


# Function to extract coordinates from KML
def extract_coordinates(coordinates):
    coords = coordinates.text.split()
    coord_list = []
    for coord in coords:
        lon, lat, _ = coord.split(",")
        coord_list.append([float(lon), float(lat)])
    return coord_list

def kml_to_geojson(kml_path):
    # Parse the KML file
    tree = ET.parse(kml_path)
    root = tree.getroot()

    # Define the KML namespace
    kml_ns = "{http://www.opengis.net/kml/2.2}"

    # Define the base structure for the GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    # Function to extract coordinates from KML
    def extract_coordinates(coordinates):
        coords = coordinates.text.split()
        coord_list = []
        for coord in coords:
            lon, lat, _ = coord.split(",")
            coord_list.append([float(lon), float(lat)])
        return coord_list

    # Iterate over Placemark elements in the KML
    for placemark in root.findall(".//{}Placemark".format(kml_ns)):
        # Create a base feature structure
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {}
        }
        
        # Extract Polygon geometries
        polygon = placemark.find(".//{}Polygon".format(kml_ns))
        if polygon is not None:
            feature["geometry"]["type"] = "Polygon"
            outer_boundary = polygon.find("{}outerBoundaryIs/{}LinearRing/{}coordinates".format(kml_ns, kml_ns, kml_ns))
            feature["geometry"]["coordinates"] = [extract_coordinates(outer_boundary)]
            
        # Extract LineString geometries
        linestring = placemark.find(".//{}LineString".format(kml_ns))
        if linestring is not None:
            feature["geometry"]["type"] = "LineString"
            coordinates = linestring.find("{}coordinates".format(kml_ns))
            feature["geometry"]["coordinates"] = extract_coordinates(coordinates)

        # If we've defined a geometry, add the feature to the list
        if "type" in feature["geometry"]:
            geojson["features"].append(feature)

    return geojson

###################
def make_random_changes_from_file(gdf, tolerance=0.000007):
    """
    Modify the LineString or MultiLineString geometry in the given GeoDataFrame.
    
    Parameters:
        gdf (GeoDataFrame): Input GeoDataFrame.
        tolerance (float): Amount by which to randomly alter each coordinate.
        
    Returns:
        GeoDataFrame: Modified GeoDataFrame.
    """

    def is_linestring_or_multilinestring(geom):
        return isinstance(geom, (LineString, MultiLineString))

    # Filter rows where the geometry is LineString or MultiLineString
    lines = gdf[gdf.geometry.apply(is_linestring_or_multilinestring)]

    # If there are no LineString or MultiLineString geometries, return the original GeoDataFrame
    if lines.shape[0] == 0:
        return gdf

    modified_geoms = []
    for geometry in lines.geometry:
        if isinstance(geometry, LineString):
            coords = list(geometry.coords)
            modified_coords = [(x + random.uniform(-tolerance, tolerance), y + random.uniform(-tolerance, tolerance)) for x, y in coords]
            modified_geoms.append(LineString(modified_coords))
        elif isinstance(geometry, MultiLineString):
            modified_multiline_coords = []
            for linestring in geometry:
                coords = list(linestring.coords)
                modified_coords = [(x + random.uniform(-tolerance, tolerance), y + random.uniform(-tolerance, tolerance)) for x, y in coords]
                modified_multiline_coords.append(modified_coords)
            modified_geoms.append(MultiLineString(modified_multiline_coords))

    # Update the geometry column in the filtered rows
    gdf.loc[lines.index, 'geometry'] = modified_geoms

    return gdf
################

def convert_kml_to_geojson():
    st.header("Convert KML to GeoJSON")

    uploaded_file = st.file_uploader("Choose a KML file", type="kml")
    if uploaded_file:
        geojson_data = kml_to_geojson(uploaded_file)

        # Convert the GeoJSON data to a GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
        
        # Check if the geometry type is LineString or MultiLineString
        if any(gdf["geometry"].geom_type.isin(["LineString", "MultiLineString"])):
            # Alter the geometry with the provided function
            gdf = make_random_changes_from_file(gdf)

        # Extract the file name without the extension and keep the spaces
        file_name_without_extension = os.path.splitext(uploaded_file.name)[0]

        # Add the 'Name' column to the GeoDataFrame
        gdf['Name'] = file_name_without_extension
        
        # Convert the modified GeoDataFrame back to GeoJSON
        geojson_data = json.loads(gdf.to_json())

        # Convert GeoJSON data to a string and then encode it
        geojson_str = json.dumps(geojson_data)
        geojson_bytes = geojson_str.encode('utf-8')
        
        # Use BytesIO to hold the byte data
        buffer = BytesIO()
        buffer.write(geojson_bytes)
        buffer.seek(0)
        
        # Create a download link for the GeoJSON data
        fname = file_name_without_extension + ".geojson"
        st.markdown(
            f"<a href='data:application/json;charset=utf-8;,{geojson_str}' download='{fname}'>Click here to download the modified GeoJSON file</a>",
            unsafe_allow_html=True
        )

    if st.button('Back to Home'):
        st.session_state.operation = None
        st.experimental_rerun()



def display_boundary_page():
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
        for index, value in street_counts.items():
            st.sidebar.markdown(f"<p style='font-weight:bold;color:white;'>{index}</p><p style='font-weight:bold;color:lightblue;'>{value}</p>", unsafe_allow_html=True)

        # Display amenities counts
        amenities = ['camp_site', 'school', 'bus_stop', 'hospital', 'hotel', 'motel', 'bar', 'biergarten', 'cafe', 'fast_food', 'food_court', 'ice_cream', 
                    #  'pub', 'community_centre', 'events_venue', 'social_centre', 'police', 'ranger_station', 'drinking_water', 'dog_toilet', 'shelter',
                    #  'telephone', 'toilets', 'animal_boarding', 'childcare', 'hunting_stand'
                    ]
        
        amenities_counts = get_amenities_counts(multipolygon, amenities)
        st.sidebar.markdown("<h1 style='color: red;'>Amenities Counts</h1>", unsafe_allow_html=True)
        for index, value in amenities_counts.items():
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

    st.title('Get Boundary')
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


    if st.button('Back to Home'):
        st.session_state.operation = None
        st.experimental_rerun()

def is_lat_lon(value):
    try:
        lat, lon = map(float, value.split(','))
        return True
    except:
        return False
    
def download_link(object_to_download, download_filename, download_link_text):
    if isinstance(object_to_download, pd.DataFrame):
        object_to_download = object_to_download.to_csv(index=False)

    # Some strings <-> bytes conversions necessary here
    b64 = base64.b64encode(object_to_download.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="{download_filename}">{download_link_text}</a>'

def bulk_pois_processing():
    st.header("Bulk POIs Processing")
    st.info("Upload an excel file that has 2 columns, ['name', 'coords'], and the code will create,a single geojson file for every sheet,\
             to be uploaded to wonder as a Bulk...")
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    
    if uploaded_file:
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)

        for sheet_name, df in all_sheets.items():
            st.write(f"Processing sheet: {sheet_name}")

            latitudes = []
            longitudes = []
    
            for idx, row in df.iterrows():
                coords = row['coords']
        
                if is_lat_lon(coords):
                    lat, lon = map(float, coords.split(','))
                    latitudes.append(lat)
                    longitudes.append(lon)
                else:
                    try:
                        st.write(f"Geocoding address: {coords}")
                        lat, lon = ox.geocoder.geocode(coords)
                        latitudes.append(lat)
                        longitudes.append(lon)
                    except Exception as e:
                        st.write(f"Error geocoding address: {coords}. Error: {str(e)}")
                        latitudes.append(None)
                        longitudes.append(None)
            
                    # Respect rate limits of the geocoding service
                    time.sleep(1)
    
            df['latitude'] = latitudes
            df['longitude'] = longitudes
    
            # Convert the DataFrame into a GeoDataFrame
            geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
            gdf = gpd.GeoDataFrame(df, geometry=geometry)

            # Save the GeoDataFrame as a GeoJSON file
            geojson_str = gdf.to_json()
            
            # Provide a download link for the GeoJSON data
            st.markdown(download_link(geojson_str, f"{sheet_name}.geojson", f"Click here to download {sheet_name}.geojson"), unsafe_allow_html=True)

    if st.button('Back to Home'):
        st.session_state.operation = None
        st.experimental_rerun()

# adding the function for POI's search with osm
def search_pois():
    st.header("Search for Points of Interest")
    
    # User input for place name or address
    place_name = st.text_input("Enter a place name or address:")
    
    # Search type selection
    search_type = st.radio("Select Search Type", ["OSM", "Google POIs"])
    
    if st.button("Search"):
        if search_type == "OSM":
            # Placeholder for OSM search logic resulting in a GeoDataFrame 'gdf'
            gdf = ox.geometries_from_place(place_name, tags={"amenity":True})
            # gdf = ...  # Perform actual OSM search here
            
            # Dissolve by 'name' to aggregate geometries
            gdf_dissolved = gdf.dissolve(by='name')[['geometry']].reset_index()
            gdf_dissolved = gdf_dissolved[gdf_dissolved['geometry'].geom_type == 'Point']
            
            # Convert to GeoJSON
            geojson_str = gdf_dissolved.to_json()
            
            # Generate download link
            b64 = base64.b64encode(geojson_str.encode()).decode()
            href = f'<a href="data:file/json;base64,{b64}" download="POIs.geojson">Download GeoJSON file</a>'
            st.markdown(href, unsafe_allow_html=True)
            
        elif search_type == "Google POIs":
            # Placeholder for Google Places API search logic
            pass  # Implement Google Places API search and follow similar steps as above

    if st.button('Back to Home'):
        st.session_state.operation = None
        st.experimental_rerun()
        
################

def main():
    st.title("Wander Builders")
    
    # Define actions for each operation within the app
    # Function for operation selection
    def choose_operation():
        st.write("Choose Operation from the Sidebar")
        with st.sidebar:
            if st.button("Get Boundary", key='get_boundary'):
                st.session_state.operation = "boundary"
                st.experimental_rerun()
            elif st.button("Convert KML to GeoJSON", key='convert_kml'):
                st.session_state.operation = "convert_kml"
                st.experimental_rerun()
            # elif st.button("Bulk POIs", key='bulk_pois'):
            #     st.session_state.operation = "bulk_pois"
            #     st.experimental_rerun()
            elif st.button("Search POIs", key='search_pois'):
                st.session_state.operation = "search_pois"
                st.experimental_rerun()

    # Initialize session state for selecting operations
    if "operation" not in st.session_state:
        st.session_state.operation = None

    # Operation execution based on selection
    if st.session_state.operation == "boundary":
        display_boundary_page()
    elif st.session_state.operation == "convert_kml":
        convert_kml_to_geojson()
    # elif st.session_state.operation == "bulk_pois":
    #     bulk_pois_processing()
    elif st.session_state.operation == "search_pois":
        search_pois()
    else:
        choose_operation()

    # Back to Home button to reset the operation
    # if st.button('Back to Home', key='back_to_home'):
    #     st.session_state.operation = None
    #     st.experimental_rerun()

if __name__ == "__main__":
    main()




