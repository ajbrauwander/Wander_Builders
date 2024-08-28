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
import numpy as np
import time
from shapely.geometry import Point
import random
from shapely.geometry import MultiLineString, LineString, shape, Point
from shapely.ops import split
import shutil
import requests
import re
from datetime import datetime

# wander_key_ = os.getenv('wander_key')
wander_key_ = st.secrets["wander_key"]

USERNAME = st.secrets["USERNAME"]
PASSWORD = st.secrets["PASSWORD"]


# Function to handle login
def login(username, password):
    if username == USERNAME and password == PASSWORD:
        return True
    else:
        return False
    
####### Developer Section ########

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if login(username, password):
            st.session_state.logged_in = True
            st.sidebar.success("Logged in successfully")
        else:
            st.sidebar.error("Invalid username or password")
else:
    # Streamlit App
    st.sidebar.success("Logged in successfully")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.sidebar.warning("Logged out")

    ############# geocoding ##############

    def geocode_address(address, api_key):
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
        response = requests.get(url).json()
        if response['status'] == 'OK':
            location = response['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            return None, None

    def reverse_geocode(lat, lng, api_key):
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}"
        response = requests.get(url).json()
        if response['status'] == 'OK':
            address = response['results'][0]['formatted_address']
            return address
        else:
            return None

    def dms_to_decimal(dms_str):
        """
        Convert DMS (degrees, minutes, seconds) format to decimal degrees.
        """
        try:
            parts = re.split('[°\'"]+', dms_str.strip())
            if len(parts) >= 3:
                degrees = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                direction = dms_str[-1]
                decimal = degrees + minutes / 60 + seconds / 3600
                if direction in ['W', 'S']:
                    decimal = -decimal
                return decimal
            else:
                return None
        except Exception as e:
            st.warning(f"Error converting DMS to decimal: {e}")
            return None

    def geocoding_page():
        st.title("Geocoding & Reverse Geocoding")

        option = st.selectbox("Choose an option", ["Geocoding", "Reverse Geocoding"])
        coord_format = st.selectbox("Coordinate Format", ["W, N", "lat, lng"])
        query_type = st.radio("Query Type", ["Single Query", "Upload File"])

        if query_type == "Single Query":
            if option == "Geocoding":
                address = st.text_input("Enter the address:")
                if st.button("Geocode"):
                    lat, lng = geocode_address(address, wander_key_)
                    if lat and lng:
                        st.write(f"Coordinates: {lat}, {lng}")
                    else:
                        st.write("Address not found.")
            else:
                if coord_format == "W, N":
                    w = st.text_input("Enter longitude (W):")
                    n = st.text_input("Enter latitude (N):")
                    if st.button("Reverse Geocode"):
                        lat = dms_to_decimal(n)
                        lon = dms_to_decimal(w)
                        if lat and lon:
                            address = reverse_geocode(lat, lon, wander_key_)
                            if address:
                                st.write(f"Address: {address}")
                            else:
                                st.write("Coordinates not found.")
                        else:
                            st.write("Invalid DMS coordinates.")
                else:
                    lat = st.number_input("Enter latitude:")
                    lon = st.number_input("Enter longitude:")
                    if st.button("Reverse Geocode"):
                        address = reverse_geocode(lat, lon, wander_key_)
                        if address:
                            st.write(f"Address: {address}")
                        else:
                            st.write("Coordinates not found.")
        else:
            uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])
            if uploaded_file:
                if "csv" in uploaded_file.name:
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)

                if st.button("Process"):
                    if option == "Geocoding":
                        df['Coordinates'] = df.iloc[:, 0].apply(lambda addr: geocode_address(addr, wander_key_))
                        df['Latitude'] = df['Coordinates'].apply(lambda x: x[0])
                        df['Longitude'] = df['Coordinates'].apply(lambda x: x[1])
                        df.drop(columns=['Coordinates'], inplace=True)
                    else:
                        if coord_format == "W, N":
                            df['lat'] = df['n'].astype(str).apply(dms_to_decimal)
                            df['lon'] = df['w'].astype(str).apply(dms_to_decimal)
                            df['Address'] = df.apply(lambda row: reverse_geocode(row['lat'], row['lon'], wander_key_), axis=1)
                        else:
                            df['Address'] = df.apply(lambda row: reverse_geocode(row[0], row[1], wander_key_), axis=1)

                    st.write(df)

                    # Save the DataFrame to a BytesIO object
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Sheet1')
                        writer.save()
                    output.seek(0)

                    st.success("File processed successfully. Download the output file below.")
                    st.download_button(
                        label="Download Output",
                        data=output,
                        file_name="output.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        if st.button('Back to Home'):
            st.session_state.operation = None
            st.experimental_rerun()

    ########### end geocoding ############

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
        
    ################
    ################

    def download_link(object_to_download, download_filename, download_link_text):
        """
        Generates a link to download the given object_to_download.
        """
        if isinstance(object_to_download, pd.DataFrame):
            object_to_download = object_to_download.to_json(orient='records')

        b64 = base64.b64encode(object_to_download.encode()).decode()
        return f'<a href="data:text/json;base64,{b64}" download="{download_filename}"> {download_link_text} </a>'

    def csv_download_link(object_to_download, download_filename, download_link_text):
        """
        Generates a link to download the given object_to_download.
        """
        if isinstance(object_to_download, pd.DataFrame):
            object_to_download = object_to_download.to_csv(index=False)

        b64 = base64.b64encode(object_to_download.encode()).decode()
        return f'<a href="data:text/csv;base64,{b64}" download="{download_filename}"> {download_link_text} </a>'


    def fetch_google_places(api_url, params):
        all_places = []
        next_page_token = None

        while True:
            # Include the next page token in parameters if it exists
            if next_page_token:
                params['pagetoken'] = next_page_token
            else:
                params.pop('pagetoken', None)

            response = requests.get(api_url, params=params)
            results = response.json()

            all_places.extend(results.get('results', []))

            next_page_token = results.get('next_page_token')
            if not next_page_token:
                break
            else:
                time.sleep(2)

        return all_places

    def search_google_pois(place_name, api_key, selected_types=None):
        API_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

        # Parameters for the initial place search
        params = {
            'input': place_name,
            'inputtype': 'textquery',
            'fields': 'photos,formatted_address,name,geometry',
            'key': api_key
        }

        # Make the initial search to get the location
        place_response = requests.get(API_URL, params=params).json()
        if place_response.get("candidates"):
            location = place_response['candidates'][0]['geometry']['location']
            
            # Parameters for nearby search, based on the found location
            nearby_params = {
                'location': f"{location['lat']},{location['lng']}",
                'radius': '30000',
                'type': '|'.join(selected_types),
                'key': api_key
            }

            # Fetch all places using the nearby search API endpoint
            response = requests.get(NEARBY_SEARCH_URL, params=nearby_params)
            results = response.json()

            # Fetch all places using the nearby search API endpoint
            all_places = fetch_google_places(NEARBY_SEARCH_URL, nearby_params)
            st.write(f"Found {len(all_places)} places from Google")
            # Process and display the results as needed
            return all_places
        else:
            return []




    def search_pois():
        st.header("Search for Points of Interest")
        place_name = st.text_input("Enter a place name or address:")
        search_type = st.radio("Select Search Type", ["OSM", "Google POIs"])

        google_types = [
        "accounting", "airport", "amusement_park", "aquarium", "art_gallery", "atm",
        "bakery", "bank", "bar", "beauty_salon", "bicycle_store", "book_store",
        "bowling_alley", "bus_station", "cafe", "campground", "car_dealer", "car_rental",
        "car_repair", "car_wash", "casino", "cemetery", "church", "city_hall",
        "clothing_store", "convenience_store", "courthouse", "dentist", "department_store",
        "doctor", "drugstore", "electrician", "electronics_store", "embassy",
        "fire_station", "florist", "funeral_home", "furniture_store", "gas_station", "gym",
        "hair_care", "hardware_store", "hindu_temple", "home_goods_store", "hospital",
        "insurance_agency", "jewelry_store", "laundry", "lawyer", "library",
        "light_rail_station", "liquor_store", "local_government_office", "locksmith",
        "lodging", "meal_delivery", "meal_takeaway", "mosque", "movie_rental",
        "movie_theater", "moving_company", "museum", "night_club", "painter", "park",
        "parking", "pet_store", "pharmacy", "physiotherapist", "plumber", "police",
        "post_office", "primary_school", "real_estate_agency", "restaurant",
        "roofing_contractor", "rv_park", "school", "secondary_school", "shoe_store",
        "shopping_mall", "spa", "stadium", "storage", "store", "subway_station",
        "supermarket", "synagogue", "taxi_stand", "tourist_attraction", "train_station",
        "transit_station", "travel_agency", "university", "veterinary_care", "zoo"
        ]

        if search_type == "OSM":
            # Define categories and corresponding OSM tags
            category_tags = {
                "Lodging": [{"tourism": ["hotel", "motel", "guest_house", "hostel"]}],
                "Food & Drink": [{"amenity": ["restaurant", "cafe", "pub", "bar"]}],
                "Shopping": [{"shop": True}],
                "Things To Do": [{"tourism": "attraction"}, {"leisure": ["park", "sports_centre"]}],
                "Museums": [{"tourism": "museum"}]
            }

            # Implement the multiselect widget for category selection
            selected_categories = st.multiselect(
                'Select Categories to Search For:',
                options=list(category_tags.keys()),  # Display category names
                default=['Food & Drink']  # Default selection
            )

            # Build list of tags based on selected categories
            tags = {}
            for category in selected_categories:
                for tag in category_tags[category]:
                    tags.update(tag)

        elif search_type == "Google POIs":
            selected_types = st.multiselect('Select Types to Search For:', google_types, ['restaurant'])

        if st.button("Search"):
            if search_type == "OSM" and place_name:
                # Using OSMnx to search for amenities based on selected tags
                gdf = ox.geometries_from_place(place_name, tags=tags)
                # Dissolve by 'name' to aggregate geometries and filter for Points
                gdf_dissolved = gdf.dissolve(by='name')[['geometry']].reset_index()
                gdf_dissolved = gdf_dissolved[gdf_dissolved['geometry'].geom_type == 'Point']

                # Convert to GeoJSON
                geojson_str = gdf_dissolved.to_json()
                csv_text = gdf_dissolved.to_csv(index=False)

                # Generate download link for the GeoJSON file
                b64 = base64.b64encode(geojson_str.encode()).decode()
                href = f'<a href="data:file/json;base64,{b64}" download="{place_name}_{selected_categories}_OSM_POIs.geojson">Download GeoJSON file</a>'
                st.markdown(href, unsafe_allow_html=True)

                # Generate download link for the CSV file
                b64 = base64.b64encode(csv_text.encode()).decode()
                href = f'<a href="data:file/json;base64,{b64}" download="{place_name}_{selected_categories}_OSM_POIs.csv">Download CSV file</a>'
                st.markdown(href, unsafe_allow_html=True)


            elif search_type == "Google POIs" and place_name:
                places = search_google_pois(place_name, wander_key_, selected_types)
                if places:
                    # Process places to a GeoJSON format
                    features = [{
                        "type": "Feature",
                        "properties": {"name": place.get("name")},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [place.get("geometry", {}).get("location", {}).get("lng"),
                                            place.get("geometry", {}).get("location", {}).get("lat")]
                        }
                    } for place in places]

                    geojson = {
                        "type": "FeatureCollection",
                        "features": features
                    }

                    # Convert to GeoJSON string and encode for download
                    geojson_str = json.dumps(geojson)
                    b64 = base64.b64encode(geojson_str.encode()).decode()
                    href = f'<a href="data:file/json;base64,{b64}" download="{place_name}_{selected_types}_Google_POIs.geojson">Download GeoJSON file</a>'
                    st.markdown(href, unsafe_allow_html=True)

    ##############################

                    # Convert each place to a simplified dictionary for CSV conversion
                    places_dicts = [{
                        "Name": place.get("name"),
                        "Latitude": place.get("geometry", {}).get("location", {}).get("lat"),
                        "Longitude": place.get("geometry", {}).get("location", {}).get("lng")
                    } for place in places]  # `places` should be defined elsewhere in your actual request handling

                    # Create a DataFrame
                    df = pd.DataFrame(places_dicts)

                    # Generate download link for the CSV
                    href = csv_download_link(df, f"{place_name.replace(' ', '_')}_{selected_types}_Google_POIs.csv", "Download CSV")
                    st.markdown(href, unsafe_allow_html=True)

    ##############################
                else:
                    st.write("No POIs found.")

            # OSM search logic remains unchanged

        if st.button('Back to Home'):
            st.session_state.operation = None
            st.experimental_rerun()
    ##################
# search POIs page


    def convert_arcgis_paths_to_geojson(arcgis_geom):
        """
        Converts an ArcGIS 'paths' geometry object to a GeoJSON structure.
        
        Parameters:
        arcgis_geom (dict): A dictionary containing the ArcGIS geometry with 'paths'.
        
        Returns:
        dict: A GeoJSON geometry dictionary.
        """
        paths = arcgis_geom.get('paths', [])

        if len(paths) == 1:
            geojson_geom = LineString(paths[0])
        else:
            geojson_geom = MultiLineString(paths)

        return geojson_geom

    def query_api(endpoint, params):
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            st.error(f"Error querying API: {e}")
            return None

    def check_far_splitted(geometry, threshold=50):
        """
        Check if any segments in the LineString or MultiLineString geometry are far splitted.
        
        Parameters:
        geometry: Shapely geometry (LineString or MultiLineString)
        threshold: Distance in meters beyond which segments are considered far-splitted
        
        Returns:
        str: 'yes' if the geometry is far splitted, 'no' otherwise.
        """
        if isinstance(geometry, LineString):
            segments = [geometry]
        elif isinstance(geometry, MultiLineString):
            segments = list(geometry.geoms)
        else:
            return 'no'  # If not a LineString or MultiLineString

        for i in range(len(segments) - 1):
            # Get the end point of the current segment and the start point of the next segment
            end_point = segments[i].coords[-1]
            start_point = segments[i + 1].coords[0]
            
            # Calculate the Euclidean distance between these points
            distance = np.sqrt((end_point[0] - start_point[0])**2 + (end_point[1] - start_point[1])**2)
            
            if distance > threshold:
                return 'yes'

        return 'no'


    def query_parks_facilities_api(endpoint, params):
        """
        Queries the Parks and Facilities API and returns a GeoDataFrame.
        
        Parameters:
        - endpoint: The API endpoint URL.
        - params: The parameters for the API request.
        
        Returns:
        - gpd.GeoDataFrame: A GeoDataFrame with the queried data.
        """
        response = requests.get(endpoint, params=params)
        data = response.json()

        # Extract spatial reference information
        if 'spatialReference' in data:
            spatial_ref = data['spatialReference']['latestWkid']
        else:
            if 'features' in data and data['features']:
                spatial_ref = data['features'][0]['geometry'].get('spatialReference', {}).get('latestWkid', None)
        
        # Extract features and create a list for geometries
        features = data['features']
        geometries = []
        attributes = []

        for feature in features:
            geom = feature['geometry']
            
            # Handle None geometry
            if geom is None:
                continue  # Skip this feature if geometry is None

            # Handle Point geometries (x and y coordinates)
            if 'x' in geom and 'y' in geom:
                geom_geojson = Point(geom['x'], geom['y'])
            else:
                continue  # Skip this feature if it doesn't have x and y coordinates

            # Append the converted Shapely geometry
            geometries.append(geom_geojson)
            
            # Extract the attributes
            attributes.append(feature['attributes'])

        # Create a DataFrame for attributes
        df = pd.DataFrame(attributes)

        # Create a GeoDataFrame by combining the attributes with the geometries
        gdf = gpd.GeoDataFrame(df, geometry=geometries)

        # Set the CRS based on the spatial reference from the API response
        if spatial_ref:
            gdf.set_crs(epsg=spatial_ref, inplace=True)
        
        return gdf


    def query_apis_page():
        st.title("Query APIs")

        # Dropdown menu for API selection
        api_choice = st.selectbox(
            "Select API to Query:",
            ("Greenways API", "Multi Use Paths API", "Parks and Facilities API")
        )

        # Input for Layer ID
        layer_id = st.text_input("Enter Layer ID:", value="0")

        # Determine the endpoint based on user selection
        if api_choice == "Greenways API":
            endpoint = f"https://twfgis.wakeforestnc.gov/server/rest/services/Greenways_Wake_Forest/MapServer/{layer_id}/query"
            dissolve_column = "Name"
        elif api_choice == "Multi Use Paths API":
            endpoint = f"https://twfgis.wakeforestnc.gov/server/rest/services/MultiUsePath/MapServer/{layer_id}/query"
            dissolve_column = "Street"
        elif api_choice == "Parks and Facilities API":
            endpoint = f"https://twfgis.wakeforestnc.gov/server/rest/services/ParksAndFacilities/MapServer/{layer_id}/query"
            dissolve_column = None  # No need to dissolve for points

        # Parameters to send with the API request
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "json"
        }

        # Query the API when the button is clicked
        if st.button("Query API"):
            data = query_api(endpoint, params)
            if data:
                st.success("API queried successfully!")

                features = data['features']
                geometries = []
                attributes = []
                spatial_ref = None

                # Extract spatial reference information
                if 'spatialReference' in data:
                    spatial_ref = data['spatialReference']['latestWkid']
                else:
                    if 'features' in data and data['features']:
                        spatial_ref = data['features'][0]['geometry'].get('spatialReference', {}).get('latestWkid', None)
                
                for feature in features:
                    geom = feature['geometry']
                    
                    # Check if the geometry is valid
                    if geom is None:
                        continue
                    
                    try:
                        # Convert geometry based on the API
                        if api_choice == "Greenways API" or api_choice == "Multi Use Paths API":
                            if 'paths' in geom:
                                geom_geojson = convert_arcgis_paths_to_geojson(geom)
                            else:
                                geom_geojson = shape(geom)
                            shapely_geom = shape(geom_geojson)
                        elif api_choice == "Parks and Facilities API":
                            if 'x' in geom and 'y' in geom:
                                shapely_geom = Point(geom['x'], geom['y'])
                            else:
                                st.warning("Skipping a feature with unknown geometry format.")
                                continue
                        
                        geometries.append(shapely_geom)
                        attributes.append(feature['attributes'])
                    except Exception as e:
                        st.warning(f"Skipping a feature due to geometry processing error: {e}")
                        continue

                # Log the number of geometries and attributes
                st.write(f"Number of geometries: {len(geometries)}")
                # st.write(f"Number of attributes: {len(attributes)}")

                # Create a DataFrame for attributes
                df = pd.DataFrame(attributes)

                if dissolve_column:
                    # Drop rows where the dissolve column is blank or NaN
                    mask = df[dissolve_column].notna()
                    df = df[mask]
                    geometries = [geometry for i, geometry in enumerate(geometries) if mask.iloc[i]]

                    # Ensure the number of geometries and attributes still match
                    if len(df) != len(geometries):
                        st.error("Mismatch between number of geometries and attributes after processing. Please check the data.")
                        return

                # Create a GeoDataFrame by combining the attributes with the geometries
                gdf = gpd.GeoDataFrame(df, geometry=geometries)

                # Set the CRS based on the spatial reference from the API response
                if spatial_ref:
                    gdf.set_crs(epsg=spatial_ref, inplace=True)

                if dissolve_column:
                    # Perform the dissolve operation by the appropriate column
                    if dissolve_column in df.columns:
                        dissolved_gdf = gdf.dissolve(by=dissolve_column, aggfunc='first')
                        dissolved_gdf.reset_index(inplace=True)
                    else:
                        st.warning(f"'{dissolve_column}' column not found. Skipping dissolve operation.")
                        dissolved_gdf = gdf
                else:
                    dissolved_gdf = gdf  # For points, no dissolve needed

                # Rename 'Name' or 'Street' to 'name'
                if dissolve_column:
                    dissolved_gdf.rename(columns={dissolve_column: 'name'}, inplace=True)
                elif api_choice == "Parks and Facilities API":
                    dissolved_gdf.rename(columns={'LABEL': 'name'}, inplace=True)
                    
                # Convert 'name' column to lowercase and filter out non-logical names
                if 'name' in dissolved_gdf.columns:
                    dissolved_gdf['name'] = dissolved_gdf['name'].str.lower()
                    non_logical_names = [
                        "no name trail", "unknown", "no name", "null", "undefined", 
                        "trail", "n/a", "na", "-", "", None
                    ]

                    dissolved_gdf = dissolved_gdf[~dissolved_gdf['name'].isin(non_logical_names)]
                    
                    # making name titles --> capitalizing each word
                    dissolved_gdf['name'] = dissolved_gdf['name'].str.title()

                if api_choice != "Parks and Facilities API":
                    # Check geometries for being far splitted
                    dissolved_gdf['far_splitted'] = dissolved_gdf['geometry'].apply(check_far_splitted)

                # Transform the CRS to EPSG:4326 (WGS 84)
                dissolved_gdf = dissolved_gdf.to_crs(epsg=4326)

                # Generate a timestamp for the filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # Create filenames based on the API name and timestamp
                excel_filename = f"{api_choice.replace(' ', '_').lower()}_{timestamp}.xlsx"
                geojson_filename = f"{api_choice.replace(' ', '_').lower()}_{timestamp}.geojson"

                # Provide options to download the result as an Excel or GeoJSON file
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    dissolved_gdf.to_excel(writer, index=False, sheet_name='Sheet1')

                output.seek(0)

                st.download_button(
                    label="Download as Excel",
                    data=output,
                    file_name=excel_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # Convert the dissolved GeoDataFrame to GeoJSON format
                geojson = dissolved_gdf.to_json()
                st.download_button(
                    label="Download as GeoJSON",
                    data=geojson,
                    file_name=geojson_filename,
                    mime="application/json"
                )





        if st.button('Back to Home'):
            st.session_state.operation = None
            st.experimental_rerun()


    ##################


    def main():
        st.title("Wander Builders")

        def choose_operation():
            st.write("Choose Operation from the Sidebar")
            with st.sidebar:
                if st.button("Get Boundary", key='get_boundary'):
                    st.session_state.operation = "boundary"
                    st.experimental_rerun()
                elif st.button("Convert KML to GeoJSON", key='convert_kml'):
                    st.session_state.operation = "convert_kml"
                    st.experimental_rerun()
                elif st.button("Search POIs", key='search_pois'):
                    st.session_state.operation = "search_pois"
                    st.experimental_rerun()
                elif st.button("Geocoding & Reverse Geocoding", key='geocoding'):
                    st.session_state.operation = "geocoding"
                    st.experimental_rerun()
                elif st.button("Query APIs", key='query_apis'):  # New page
                    st.session_state.operation = "query_apis"
                    st.experimental_rerun()

        if "operation" not in st.session_state:
            st.session_state.operation = None

        if st.session_state.operation == "boundary":
            display_boundary_page()
        elif st.session_state.operation == "convert_kml":
            convert_kml_to_geojson()
        elif st.session_state.operation == "search_pois":
            search_pois()
        elif st.session_state.operation == "geocoding":
            geocoding_page()
        elif st.session_state.operation == "query_apis":  # New page
            query_apis_page()
        else:
            choose_operation()

    if __name__ == "__main__":
        main()