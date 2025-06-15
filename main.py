import os
import json
import pandas as pd
import csv
from datetime import datetime
from PIL import Image, ImageDraw


import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Calculate and plot your Female Manipulator Musical Compass coordinates')
    parser.add_argument('--folder_path_to_jsons', type=str, required=False, default='Spotify Extended Streaming History',
                      help='Path to folder containing Spotify Extended Streaming History JSON files')
    parser.add_argument('--start_date', type=str, required=False, default=None,
                      help='Start date in YYYYMMDD format')
    parser.add_argument('--end_date', type=str, required=False, default=None,
                      help='End date in YYYYMMDD format')
    return parser.parse_args()


def logical_to_pixel(x, y):
    # X axis
    x_start, x_end = 147, 1049
    # Y axis
    y_start, y_end = 180, 1084

    px = x_start + ((x + 1) / 2) * (x_end - x_start)
    py = y_start + ((1 - y) / 2) * (y_end - y_start)
    return int(round(px)), int(round(py))


def plot_on_photo(mean_x, mean_y, pixel_x, pixel_y, q1_plays, q2_plays, q3_plays, q4_plays, photo_path='compass.jpg', output_path='compass_with_dot.png'):
    # Open the image
    image = Image.open(photo_path)
    draw = ImageDraw.Draw(image)
    # Draw a red dot (circle) at the specified pixel coordinates
    radius = 10
    left_up_point = (pixel_x - radius, pixel_y - radius)
    right_down_point = (pixel_x + radius, pixel_y + radius)
    draw.ellipse([left_up_point, right_down_point], fill='red', outline='black')
    
    # Add coordinates text
    font_size = 20
    text_offset = 15
    text_position = (pixel_x + radius + text_offset, pixel_y - font_size//2)
    text = f"({mean_x:.3f}, {mean_y:.3f})"
    # Calculate text size to create background rectangle
    text_bbox = draw.textbbox(text_position, text, font_size=font_size)
    # Draw white background rectangle
    draw.rectangle(text_bbox, fill='white')
    # Draw text on top
    draw.text(text_position, text, fill='red', font_size=font_size, font_weight='bold')
    
    # Save the image
    image.save(output_path)
    print(f"\nSaved image with dot at ({pixel_x}, {pixel_y}) to {output_path}")



def main():
    args = parse_args()
    folder_path = args.folder_path_to_jsons
    start_date = args.start_date
    end_date = args.end_date

    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory.")
        return

    print(f"\nFolder path provided: {folder_path}")

    # Load all files in the folder that start with 'Streaming_History_Audio' and end with .json
    streaming_history_files = [
        f for f in os.listdir(folder_path)
        if f.startswith("Streaming_History_Audio") and f.endswith(".json")
    ]

    if streaming_history_files:
        print("\nFound the following Streaming_History_Audio files:")
        for filename in streaming_history_files:
            print(f"- {filename}")
    else:
        print("\nNo Streaming_History_Audio files found in the folder.")
        return

    # Read and filter data
    filtered_entries = []
    for filename in streaming_history_files:
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue
            for entry in data:
                ts = entry.get("ts")
                if ts:
                    try:
                        date = datetime.fromisoformat(ts.replace('Z', '+00:00')).date()
                    except Exception as e:
                        print(f"Error parsing timestamp {ts} in {filename}: {e}")
                        continue
                    
                    # Convert start_date and end_date strings to date objects if they exist
                    entry_in_range = True
                    if start_date:
                        start = datetime.strptime(start_date, '%Y%m%d').date()
                        entry_in_range = entry_in_range and date >= start
                    if end_date:
                        end = datetime.strptime(end_date, '%Y%m%d').date()
                        entry_in_range = entry_in_range and date <= end
                        
                    if entry_in_range and not entry.get('skipped'):
                        filtered_entries.append(entry)

    print(f"\nTotal non-skipped listens in range: {len(filtered_entries)}")

    # Save frequency of all artists to CSV
    all_artist_counts = {}
    for entry in filtered_entries:
        artist = entry.get('master_metadata_album_artist_name')
        if artist:
            all_artist_counts[artist] = all_artist_counts.get(artist, 0) + 1
    
    # Sort artists by count in descending order and save to CSV
    sorted_all_artists = sorted(all_artist_counts.items(), key=lambda x: x[1], reverse=True)
    with open('artist_frequencies.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Artist', 'Play Count'])
        writer.writerows(sorted_all_artists)
    print("\nArtist frequencies saved to artist_frequencies.csv")

    # read coords.csv
    coords_df = pd.read_csv('coords.csv')

    # retain only the entries where the artist is in the coords_df.Artist column
    filtered_entries = [entry for entry in filtered_entries if entry.get('master_metadata_album_artist_name') in coords_df.Artist.values]
    print(f"\nTotal non-skipped female manipulator listens in range: {len(filtered_entries)}")

    # Print frequency of each artist in coords_df.Artist
    print("\nFemale manipulator listens per artist in range:")
    artist_list = coords_df.Artist.values
    artist_counts = {artist: 0 for artist in artist_list}
    for entry in filtered_entries:
        artist = entry.get('master_metadata_album_artist_name')
        if artist in artist_counts:
            artist_counts[artist] += 1
    # Sort artists by count in descending order
    sorted_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)
    for artist, count in sorted_artists:
        print(f"{artist}: {count}")

    # Calculate mean_x and mean_y
    coords_df['play_count'] = coords_df['Artist'].map(artist_counts).fillna(0).astype(int)
    listened = coords_df[coords_df['play_count'] > 0]
    if not listened.empty:
        weighted_x = (listened['x'] * listened['play_count']).sum()
        weighted_y = (listened['y'] * listened['play_count']).sum()
        total_plays = listened['play_count'].sum()
        mean_x = weighted_x / total_plays
        mean_y = weighted_y / total_plays
        print(f"\nYour listening coordinates: ({mean_x:.2f}, {mean_y:.2f})")

        # Calculate listens per quadrant
        q1_plays = listened[(listened['x'] >= 0) & (listened['y'] >= 0)]['play_count'].sum()
        q2_plays = listened[(listened['x'] < 0) & (listened['y'] >= 0)]['play_count'].sum() 
        q3_plays = listened[(listened['x'] < 0) & (listened['y'] < 0)]['play_count'].sum()
        q4_plays = listened[(listened['x'] >= 0) & (listened['y'] < 0)]['play_count'].sum()
        print("\nListens per quadrant:")
        print(f"Q1 (top right): {q1_plays}")
        print(f"Q2 (top left): {q2_plays}")
        print(f"Q3 (bottom left): {q3_plays}")
        print(f"Q4 (bottom right): {q4_plays}")

        # Plot on photo
        pixel_x, pixel_y = logical_to_pixel(mean_x, mean_y)
        plot_on_photo(mean_x, mean_y, pixel_x, pixel_y, q1_plays, q2_plays, q3_plays, q4_plays)
    else:
        print("\nNo matching artists with plays found for coordinate calculation.")


if __name__ == "__main__":
    main() 