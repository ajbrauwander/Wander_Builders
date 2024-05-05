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
import base64
import requests
import time
import logging
import json
from PIL import Image


    # google_types = [
    # "accounting", "airport", "amusement_park", "aquarium", "art_gallery", "atm",
    # "bakery", "bank", "bar", "beauty_salon", "bicycle_store", "book_store",
    # "bowling_alley", "bus_station", "cafe", "campground", "car_dealer", "car_rental",
    # "car_repair", "car_wash", "casino", "cemetery", "church", "city_hall",
    # "clothing_store", "convenience_store", "courthouse", "dentist", "department_store",
    # "doctor", "drugstore", "electrician", "electronics_store", "embassy",
    # "fire_station", "florist", "funeral_home", "furniture_store", "gas_station", "gym",
    # "hair_care", "hardware_store", "hindu_temple", "home_goods_store", "hospital",
    # "insurance_agency", "jewelry_store", "laundry", "lawyer", "library",
    # "light_rail_station", "liquor_store", "local_government_office", "locksmith",
    # "lodging", "meal_delivery", "meal_takeaway", "mosque", "movie_rental",
    # "movie_theater", "moving_company", "museum", "night_club", "painter", "park",
    # "parking", "pet_store", "pharmacy", "physiotherapist", "plumber", "police",
    # "post_office", "primary_school", "real_estate_agency", "restaurant",
    # "roofing_contractor", "rv_park", "school", "secondary_school", "shoe_store",
    # "shopping_mall", "spa", "stadium", "storage", "store", "subway_station",
    # "supermarket", "synagogue", "taxi_stand", "tourist_attraction", "train_station",
    # "transit_station", "travel_agency", "university", "veterinary_care", "zoo"]


wander_key_ = os.getenv('wander_key')
# wander_key_ = st.secrets["wander_key"]

####### Developer Section ########

def load_image(image_file):
    img = Image.open(image_file)
    return img

def developer_section():
    st.title('Developer Profile')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Hello, I'm Kareem!")
        st.image(load_image('Photo2.jpeg'), width=300)  # Adjust path and size as needed
    
    with col2:
        st.write("""
        - **GIS Developer** with four years on Upwork.
        - **Expertise**:
            - **Custom GIS Tools Creation**
            - **Spatial Data Analysis**
            - **Geospatial Web Development**
            - **Geocoding and Routing**
            - **Data Visualization**
            - **OSMNX** for street network analysis
            - **GeoPandas** for spatial data manipulation
            - **Folium and Leaflet** for interactive maps
            - **QGIS and Mapbox**
            - **PostgreSQL and Django**
            - **Google Maps API**
            - **Streamlit** for web apps
        """)
    
    st.markdown("""
    **Connect with me on Social Media:**
    - [LinkedIn](https://www.linkedin.com/in/kareem-alaraby-59a251108/)
    - [GitHub](https://github.com/TheOther-Guy)
   
    """)
    # Encode the download link for your resume or portfolio
    # with open("path_to_resume.pdf", "rb") as file:
    #     btn = st.download_button(
    #         label="Download My Resume",
    #         data=file,
    #         file_name="Kareem_Resume.pdf",
    #         mime="application/octet-stream"
    #     )

    if st.button('Back to Home'):
        st.session_state.operation = None
        st.experimental_rerun()
####### End Developer Section ########


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

####################
####################

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
            places = search_google_pois(place_name, wander_key, selected_types)
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
                    "Address": place.get("vicinity"),
                    "Type": place.get("types"),
                    "Rating": place.get("rating"),
                    # "Address": place.get("formattedAddress"),
                    "Status": place.get("businessStatus"),
                    "User Ratings Total": place.get("userRatingsTotal"),
                    "Price Level": place.get("priceLevel"),
                    "Opening Hours": place.get("openingHours", {}).get("weekday_text"),
                    "Website": place.get("website"),
                    "Phone Number": place.get("formattedPhoneNumber"),
                    "International Phone Number": place.get("internationalPhoneNumber"),
                    "Google Maps URL": place.get("url"),
                    "Google Maps Place ID": place.get("place_id"),
                    "Google Maps Reference": place.get("reference"),
                    "Google Maps Scope": place.get("scope"),
                    "Icon": place.get("icon"),
                    "ID": place.get("id"),
                    "Permanently Closed": place.get("permanentlyClosed"),
                    "UTC Offset": place.get("utc_offset"),
                    "Photos": place.get("photos"),
                    "Altitude": place.get("geometry", {}).get("location", {}).get("alt"),
                    
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
            elif st.button("Search POIs", key='search_pois'):
                st.session_state.operation = "search_pois"
                st.experimental_rerun()
            elif st.button("Developer Profile", key='developer_profile'):
                st.session_state.operation = "developer_profile"
                st.experimental_rerun()

    # Initialize session state for selecting operations
    if "operation" not in st.session_state:
        st.session_state.operation = None

    # Operation execution based on selection
    if st.session_state.operation == "boundary":
        display_boundary_page()
    elif st.session_state.operation == "convert_kml":
        convert_kml_to_geojson()
    elif st.session_state.operation == "search_pois":
        search_pois()
    elif st.session_state.operation == "developer_profile":
        developer_section()  # This is the function you will write to display the developer profile
    else:
        choose_operation()

if __name__ == "__main__":
    main()





