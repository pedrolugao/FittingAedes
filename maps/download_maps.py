#!/usr/bin/env python3
"""
Script to download satellite and roadmap images from Google Maps Static API
for the study areas from the Aedes aegypti surveillance paper.

Cities and neighborhoods:
- Santarem (STR), Para - North Region
- Parnamirim (PNM), Rio Grande do Norte - Northeast Region
- Duque de Caxias (DQC), Rio de Janeiro - Southeast Region
- Nova Iguacu (NIG), Rio de Janeiro - Southeast Region
- Campo Grande (CGR), Mato Grosso do Sul - Central-West Region

Each city has 3 neighborhoods (A, B, C) with 1 km^2 study areas.

Reference: Codeco et al. (2015) "Surveillance of Aedes aegypti: Comparison of
House Index with Four Alternative Traps" - PLoS Neglected Tropical Diseases
"""

import os
import json
import requests
import math
import time
from pathlib import Path

# ============================================================================
# CONFIGURATION - ADD YOUR API KEY HERE
# ============================================================================
API_KEY = "YOUR_GOOGLE_MAPS_API_KEY_HERE"

# ============================================================================
# STUDY AREAS CONFIGURATION
# ============================================================================
# Coordinates for study neighborhoods based on the paper and geographic research
# The paper mentions 3 non-adjacent 1 km^2 areas per city
# Note: These coordinates are approximate centers for each neighborhood
# You may need to adjust them based on the exact study locations

NEIGHBORHOODS = {
    "Santarem_PA": {
        "city_coords": (-2.4431, -54.7081),  # City center reference
        "neighborhoods": {
            # Neighborhoods from study data
            "Jd_Santarem": (-2.4378241794575026, -54.71987459086378),      # Jardim Santarem
            "Republica": (-2.4678187892272376, -54.71850151326716),        # Republica neighborhood
            "Santarenzinho": (-2.448755899384659, -54.739186248494214),    # Santarenzinho neighborhood
        }
    },
    "Parnamirim_RN": {
        "city_coords": (-5.9158, -35.2628),  # City center reference
        "neighborhoods": {
            # Neighborhoods from study data
            "Areia": (-5.911979478632795, -35.28125445852211),            # Parque das Arvores/Areia Branca area
            "Emaus": (-5.883164700992478, -35.248752695921134),            # Emaus neighborhood
            "Liberdade": (-5.9293443352973325, -35.2466101857502),        # Liberdade neighborhood
        }
    },
    "DuqueDeCaxias_RJ": {
        "city_coords": (-22.7856, -43.3116),  # City center reference
        "neighborhoods": {
            # Neighborhoods from study data
            "Bilac": (-22.75639311934788, -43.2859907217267553),           # Jardim Gramacho/Bilac area
            "Primavera": (-22.690484842834632, -43.26754505904175),       # Primavera neighborhood
            "Saracuruna": (-22.67618976653338, -43.253923409713764),      # Saracuruna neighborhood
        }
    },
    "NovaIguacu_RJ": {
        "city_coords": (-22.7556, -43.4503),  # City center reference
        "neighborhoods": {
            # Neighborhoods from study data
            "Cabucu": (-22.78330975017275, -43.54597528965344),          # Cabucu neighborhood
            "Ceramica": (-22.733255495451203, -43.47619632222511),        # Ceramica neighborhood
            "Moqueta": (-22.745873633848824, -43.45582278212255),         # Moqueta neighborhood
        }
    },
    "CampoGrande_MS": {
        "city_coords": (-20.4428, -54.6464),  # City center reference
        "neighborhoods": {
            # Neighborhoods from study data
            "Carlota": (-20.493369919889364, -54.599496948275636),         # Vila Carlota neighborhood
            "Guanandi": (-20.50009659444382, -54.6453119802571),        # Guanandi neighborhood
            "Planalto": (-20.452341817016315, -54.62921434767367),        # Planalto neighborhood
        }
    }
}

# ============================================================================
# MAP SETTINGS
# ============================================================================

# Image size in pixels (maximum for free tier is 640x640)
IMAGE_SIZE = 640

# For 1 km^2 area at different latitudes, we need appropriate zoom levels
# At zoom 16, each pixel is ~2.4m at equator, giving ~1.5km width at 640px
# At zoom 17, each pixel is ~1.2m at equator, giving ~768m width at 640px
# We'll use zoom 16 which gives approximately 1km x 1km coverage

ZOOM_LEVEL = 16

# Scale factor (1 or 2, where 2 gives higher resolution)
SCALE = 2

# Final image dimensions (640 * scale = 1280 pixels for scale=2)
FINAL_SIZE = IMAGE_SIZE * SCALE

# ============================================================================
# MAP STYLE FOR ROADMAP
# ============================================================================

def load_map_style():
    """Load the custom map style from mapStyle.json"""
    style_path = Path(__file__).parent / "mapStyle.json"
    if style_path.exists():
        with open(style_path, 'r') as f:
            return json.load(f)
    return None

def convert_style_to_url_params(style_json):
    """
    Convert the JSON style to Google Maps Static API style parameters.

    The Google Maps Static API uses a different format than the JSON style.
    We need to convert the style to URL parameters.
    """
    style_params = []

    if not style_json or 'styles' not in style_json:
        return style_params

    # Mapping from JSON style IDs to Google Maps feature types
    feature_mapping = {
        'infrastructure': 'landscape.man_made',
        'infrastructure.roadNetwork': 'road',
        'natural': 'landscape.natural',
        'natural.land': 'landscape.natural.landcover',
        'pointOfInterest': 'poi',
        'political': 'administrative',
        'political.landParcel': 'administrative.land_parcel',
    }

    for style in style_json.get('styles', []):
        style_id = style.get('id', '')
        feature_type = feature_mapping.get(style_id, style_id.replace('.', '.'))

        # Handle geometry styles
        if 'geometry' in style:
            geom = style['geometry']
            if 'fillColor' in geom:
                color = geom['fillColor'].replace('#', '0x')
                style_params.append(f"style=feature:{feature_type}|element:geometry.fill|color:{color}")
            if 'strokeColor' in geom:
                color = geom['strokeColor'].replace('#', '0x')
                style_params.append(f"style=feature:{feature_type}|element:geometry.stroke|color:{color}")
            if geom.get('visible') == False:
                style_params.append(f"style=feature:{feature_type}|element:geometry|visibility:off")

        # Handle label styles
        if 'label' in style:
            label = style['label']
            if label.get('visible') == False:
                style_params.append(f"style=feature:{feature_type}|element:labels|visibility:off")
            if 'textFillColor' in label:
                color = label['textFillColor'].replace('#', '0x')
                style_params.append(f"style=feature:{feature_type}|element:labels.text.fill|color:{color}")
            if 'textStrokeColor' in label:
                color = label['textStrokeColor'].replace('#', '0x')
                style_params.append(f"style=feature:{feature_type}|element:labels.text.stroke|color:{color}")

    return style_params


def get_roadmap_style_string():
    """
    Generate style string for a clean roadmap suitable for analysis.
    This creates a simplified map showing only roads and basic land features.
    """
    # Load custom style if available
    style_json = load_map_style()
    if style_json:
        return convert_style_to_url_params(style_json)

    # Fallback: Create a clean roadmap style programmatically
    styles = [
        # Hide all labels
        "style=feature:all|element:labels|visibility:off",
        # Simple land color
        "style=feature:landscape|element:geometry|color:0xd3f8e2",
        # Road styling
        "style=feature:road|element:geometry|color:0xd7dfe6",
        # Hide POIs
        "style=feature:poi|visibility:off",
        # Hide transit
        "style=feature:transit|visibility:off",
        # Hide administrative boundaries
        "style=feature:administrative|element:labels|visibility:off",
    ]
    return styles


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def meters_per_pixel(lat, zoom):
    """
    Calculate meters per pixel at a given latitude and zoom level.

    Formula: meters_per_pixel = 156543.03392 * cos(lat) / (2^zoom)
    """
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)


def calculate_zoom_for_1km(lat, image_size=640, scale=2):
    """
    Calculate the zoom level needed to capture approximately 1km width.

    At the equator:
    - Zoom 16: ~2.4m/px -> 640px = 1536m (~1.5km)
    - Zoom 17: ~1.2m/px -> 640px = 768m (~0.75km)
    - Zoom 18: ~0.6m/px -> 640px = 384m

    For 1km coverage with 640px base image, we want zoom ~17
    """
    target_meters = 1000  # 1 km
    best_zoom = 17
    best_diff = float('inf')

    for zoom in range(14, 21):
        mpp = meters_per_pixel(lat, zoom)
        coverage = mpp * image_size
        diff = abs(coverage - target_meters)
        if diff < best_diff:
            best_diff = diff
            best_zoom = zoom

    return best_zoom


def create_directory_structure(base_path):
    """Create the folder structure for all cities and neighborhoods."""
    for city_name, city_data in NEIGHBORHOODS.items():
        city_path = base_path / city_name
        city_path.mkdir(parents=True, exist_ok=True)

        for neighborhood_name in city_data['neighborhoods'].keys():
            neighborhood_path = city_path / neighborhood_name
            neighborhood_path.mkdir(parents=True, exist_ok=True)

    print(f"Created directory structure at: {base_path}")


def download_satellite_map(lat, lon, output_path, api_key):
    """
    Download a clean satellite image (no labels, markers, or overlays).

    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        output_path: Path to save the image
        api_key: Google Maps API key
    """
    # Calculate appropriate zoom for this latitude
    zoom = calculate_zoom_for_1km(lat, IMAGE_SIZE)

    base_url = "https://maps.googleapis.com/maps/api/staticmap"

    params = {
        'center': f"{lat},{lon}",
        'zoom': zoom,
        'size': f"{IMAGE_SIZE}x{IMAGE_SIZE}",
        'scale': SCALE,
        'maptype': 'satellite',
        'key': api_key,
        # No markers, no labels for clean satellite imagery
    }

    # Build URL with style to remove all labels from satellite view
    url = f"{base_url}?center={params['center']}&zoom={params['zoom']}&size={params['size']}&scale={params['scale']}&maptype={params['maptype']}&key={params['key']}"

    # Add style to hide labels on satellite
    url += "&style=feature:all|element:labels|visibility:off"

    try:
        response = requests.get(url)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f"  Saved satellite map: {output_path}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  Error downloading satellite map: {e}")
        return False


def download_roadmap(lat, lon, output_path, api_key):
    """
    Download a styled roadmap image.

    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        output_path: Path to save the image
        api_key: Google Maps API key
    """
    # Calculate appropriate zoom for this latitude (must match satellite)
    zoom = calculate_zoom_for_1km(lat, IMAGE_SIZE)

    base_url = "https://maps.googleapis.com/maps/api/staticmap"

    # Build base URL
    url = f"{base_url}?center={lat},{lon}&zoom={zoom}&size={IMAGE_SIZE}x{IMAGE_SIZE}&scale={SCALE}&maptype=roadmap&key={api_key}"

    # Add custom styles
    style_params = get_roadmap_style_string()
    for style in style_params:
        url += f"&{style}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f"  Saved roadmap: {output_path}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  Error downloading roadmap: {e}")
        return False


def download_all_maps(base_path, api_key):
    """Download all satellite and roadmap images for all neighborhoods."""

    if api_key == "YOUR_GOOGLE_MAPS_API_KEY_HERE":
        print("ERROR: Please set your Google Maps API key in the script!")
        print("Edit the API_KEY variable at the top of the file.")
        return

    base_path = Path(base_path)

    # Create directory structure
    create_directory_structure(base_path)

    total = sum(len(city['neighborhoods']) for city in NEIGHBORHOODS.values())
    current = 0

    for city_name, city_data in NEIGHBORHOODS.items():
        print(f"\nProcessing city: {city_name}")

        for neighborhood_name, coords in city_data['neighborhoods'].items():
            current += 1
            lat, lon = coords

            print(f"\n  [{current}/{total}] Neighborhood: {neighborhood_name}")
            print(f"  Coordinates: {lat}, {lon}")

            # Calculate zoom and coverage info
            zoom = calculate_zoom_for_1km(lat, IMAGE_SIZE)
            mpp = meters_per_pixel(lat, zoom)
            coverage_m = mpp * IMAGE_SIZE * SCALE

            print(f"  Zoom level: {zoom}")
            print(f"  Coverage: {coverage_m:.0f}m x {coverage_m:.0f}m")

            neighborhood_path = base_path / city_name / neighborhood_name

            # Download satellite image (skip if already exists)
            satellite_path = neighborhood_path / "satellite.png"
            if satellite_path.exists():
                print(f"  Satellite map already exists, skipping...")
            else:
                download_satellite_map(lat, lon, satellite_path, api_key)
                time.sleep(2)  # Delay to avoid rate limiting

            # Download roadmap image (skip if already exists)
            roadmap_path = neighborhood_path / "roadmap.png"
            if roadmap_path.exists():
                print(f"  Roadmap already exists, skipping...")
            else:
                download_roadmap(lat, lon, roadmap_path, api_key)
                time.sleep(2)  # Delay between neighborhoods

    print(f"\n{'='*60}")
    print("Download complete!")
    print(f"Maps saved to: {base_path}")
    print(f"Total neighborhoods processed: {total}")


def generate_coordinates_report(base_path):
    """Generate a report of all coordinates used."""
    report_path = Path(base_path) / "coordinates_report.txt"

    with open(report_path, 'w') as f:
        f.write("Aedes aegypti Study Areas - Coordinate Report\n")
        f.write("=" * 60 + "\n\n")
        f.write("Reference: Codeco et al. (2015) PLoS Negl Trop Dis\n")
        f.write("DOI: 10.1371/journal.pntd.0003475\n\n")

        for city_name, city_data in NEIGHBORHOODS.items():
            f.write(f"\n{city_name}\n")
            f.write("-" * 40 + "\n")
            f.write(f"City center reference: {city_data['city_coords']}\n\n")

            for neighborhood_name, coords in city_data['neighborhoods'].items():
                lat, lon = coords
                zoom = calculate_zoom_for_1km(lat, IMAGE_SIZE)
                mpp = meters_per_pixel(lat, zoom)
                coverage = mpp * IMAGE_SIZE * SCALE

                f.write(f"  {neighborhood_name}:\n")
                f.write(f"    Latitude:  {lat}\n")
                f.write(f"    Longitude: {lon}\n")
                f.write(f"    Zoom:      {zoom}\n")
                f.write(f"    Coverage:  ~{coverage:.0f}m x {coverage:.0f}m\n\n")

    print(f"Coordinates report saved to: {report_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Google Maps satellite and roadmap images for Aedes study areas"
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='Google Maps API key (or set API_KEY in script)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory (default: script directory)'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only generate coordinates report, do not download maps'
    )

    args = parser.parse_args()

    # Determine API key
    api_key = args.api_key if args.api_key else API_KEY

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent

    print("=" * 60)
    print("Aedes aegypti Study Areas Map Downloader")
    print("=" * 60)
    print(f"\nOutput directory: {output_dir}")
    print(f"Image size: {IMAGE_SIZE}x{IMAGE_SIZE} (scale {SCALE}x = {FINAL_SIZE}x{FINAL_SIZE} pixels)")

    if args.report_only:
        generate_coordinates_report(output_dir)
    else:
        # Generate report first
        generate_coordinates_report(output_dir)
        # Then download maps
        download_all_maps(output_dir, api_key)
