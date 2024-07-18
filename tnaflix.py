import requests
import json
import argparse
import re
from tqdm import tqdm

def fetch_video_data(video_id):
    url = f"https://tnaflix.com/ajax/video-player/{video_id}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch video data: {response.status_code}")
    return response.json()

def list_formats(video_data):
    formats = video_data['html'].split('source src="')[1:]
    format_list = []
    for fmt in formats:
        url, size = re.search(r'(.+?)" type="video/mp4" size="(\d+)"', fmt).groups()
        format_list.append((url, size))
    format_list.sort(key=lambda x: int(x[1]), reverse=True)
    return format_list

def download_video(url, file_name):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024

    if response.status_code == 200:
        with open(file_name, 'wb') as f, tqdm(
                desc=file_name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        print(f"Video successfully downloaded as {file_name}")
    else:
        print(f"Failed to download video: {response.status_code}")

def main():
    parser = argparse.ArgumentParser(description="Download videos from TNAFlix")
    parser.add_argument('url', help="URL of the video")
    parser.add_argument('-f', '--format', help="Specify format size to download")
    parser.add_argument('-F', '--list-formats', action='store_true', help="List available formats")
    args = parser.parse_args()

    # Extract video ID
    video_id_match = re.search(r'video(\d+)', args.url)
    if not video_id_match:
        raise ValueError("Invalid URL format")
    video_id = video_id_match.group(1)

    # Fetch video data
    video_data = fetch_video_data(video_id)
    
    # List formats if -F flag is used
    if args.list_formats:
        formats = list_formats(video_data)
        for url, size in formats:
            print(f"Size: {size} - URL: {url}")
        return

    # Determine which format to download
    formats = list_formats(video_data)
    if args.format:
        selected_format = next((url for url, size in formats if size == args.format), None)
        if not selected_format:
            raise ValueError("Specified format not found")
    else:
        # Select the second highest quality format
        if len(formats) > 1:
            selected_format = formats[1][0]
        else:
            selected_format = formats[0][0]

    # Download the selected format
    download_video(selected_format, f"video_{video_id}.mp4")

if __name__ == "__main__":
    main()

