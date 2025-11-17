import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import leafmap.foliumap as leafmap
import requests
from io import BytesIO
import zipfile

# -------------------------------------------------------
# Streamlit page config
# -------------------------------------------------------
st.set_page_config(page_title='Utah Population Dashboard', layout='wide')

st.title('Utah Population Dashboard')
st.write(
    'This dashboard visualizes county-level population in Utah, '
    'using U.S. Census population estimates. '
    'The map shows population change from 2020 to 2024, and the bar chart '
    'compares population in 2020 and 2024 for each county.'
)

st.info("Note: This app uses TIGER/LINE county shapefiles from the U.S. Census.")

st.sidebar.title('About')
st.sidebar.info('Explore population patterns across Utah counties.')

# Sidebar colors for bar chart
col1, col2 = st.sidebar.columns(2)
pop2020_color = col1.color_picker('Color for 2020', "#86BFE0")
pop2024_color = col2.color_picker('Color for 2024', "#C66762")

# -------------------------------------------------------
# Load TIGER county boundaries
# -------------------------------------------------------
@st.cache_data
def load_tiger_counties():
    """Load US Census TIGER/Line Shapefile for counties (2023)."""
    tiger_url = "https://www2.census.gov/geo/tiger/TIGER2023/COUNTY/tl_2023_us_county.zip"
    
    with st.spinner("Loading US Census TIGER county shapefiles..."):
        response = requests.get(tiger_url)
        z = zipfile.ZipFile(BytesIO(response.content))
        z.extractall("/tmp/tiger_counties")
        
        gdf = gpd.read_file("/tmp/tiger_counties/tl_2023_us_county.shp")
        gdf['GEOID'] = gdf['GEOID'].astype(str).str.zfill(5)
        gdf = gdf.to_crs(epsg=4326)
    return gdf

# -------------------------------------------------------
# Load Utah population data from CSV
# -------------------------------------------------------
@st.cache_data
def read_utah_population(csv_path: str):
    """
    Read the Utah population CSV file and prepare it for mapping.
    """
    df = pd.read_csv(csv_path)

    # Keep only county-level (SUMLEV 50)
    df = df[df['SUMLEV'] == 50].copy()

    # Build FIPS codes
    df['STATEFP'] = df['STATE'].astype(int).astype(str).str.zfill(2)
    df['COUNTYFP'] = df['COUNTY'].astype(int).astype(str).str.zfill(3)
    df['GEOID'] = df['STATEFP'] + df['COUNTYFP']

    # Use county name as NAME
    df['NAME'] = df['CTYNAME']

    # Select only needed columns
    df = df[['NAME', 'GEOID', 'STATEFP', 'POPESTIMATE2020', 'POPESTIMATE2024']].copy()
    df = df.rename(
        columns={
            'POPESTIMATE2020': 'POP2020',
            'POPESTIMATE2024': 'POP2024'
        }
    )

    # Population change
    df['Pop_Change'] = df['POP2024'] - df['POP2020']

    # Keep only Utah (STATEFP == 49)
    df = df[df['STATEFP'] == "49"].copy()

    return df

# -------------------------------------------------------
# Load data
# -------------------------------------------------------
TIGER = load_tiger_counties()

csv_path = "DataPop.csv" 
pop_df = read_utah_population(csv_path)

# Sidebar statistics
st.sidebar.write("### Summary statistics (Utah counties)")
st.sidebar.dataframe(pop_df[['POP2020', 'POP2024', 'Pop_Change']].describe())

# -------------------------------------------------------
# Create the map: Population Change
# -------------------------------------------------------
st.write("## Map: Population Change (2020–2024) in Utah Counties")

# Filter TIGER to Utah
utah_gdf = TIGER[TIGER['STATEFP'] == "49"].copy()

# Merge shapefile & population
utah_gdf = utah_gdf.merge(pop_df, on='GEOID', how='left')

m = leafmap.Map(
    layers_control=True,
    draw_control=False,
    measure_control=False,
    fullscreen_control=False,
)
m.add_basemap('CartoDB.Positron')

# Add population change layer
m.add_data(
    utah_gdf,
    layer_name='Population Change 2020–2024',
    column="Pop_Change",
    scheme="Quantiles",
    cmap="RdYlGn",
    zoom_to_layer=True,
    info_mode=None,
)

m.to_streamlit(1000, 600)

# -------------------------------------------------------
# Map: Population 2024
# -------------------------------------------------------
st.write("## Map: Population in 2024")

m2 = leafmap.Map(
    layers_control=True,
    draw_control=False,
    measure_control=False,
    fullscreen_control=False,
)
m2.add_basemap('CartoDB.Positron')

m2.add_data(
    utah_gdf,
    layer_name='Population 2024',
    column="POP2024",
    scheme="Quantiles",
    cmap="Blues",
    zoom_to_layer=True,
    info_mode=None,
)

m2.to_streamlit(1000, 600)

# -------------------------------------------------------
# Bar chart: 2020 vs 2024 population
# -------------------------------------------------------
st.write("## Bar Chart: Population in 2020 vs 2024 (Utah Counties)")

plot_df = pop_df.sort_values('POP2024', ascending=False)

fig, ax = plt.subplots(1, 1, figsize=(10, 8))
plot_df.plot(
    kind='bar',
    ax=ax,
    x='NAME',
    y=['POP2020', 'POP2024'],
    color=[pop2020_color, pop2024_color],
    xlabel="County",
    ylabel="Population",
)
ax.set_title('Utah Counties: Population in 2020 vs 2024')
ax.set_xticklabels(plot_df['NAME'], rotation=90, ha='right')
ax.set_ylim(0, 1.1 * plot_df[['POP2020', 'POP2024']].to_numpy().max())

st.pyplot(fig)

