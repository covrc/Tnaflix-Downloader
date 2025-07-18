import requests
import argparse
import re
import subprocess

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
        match = re.search(r'(.+?)" type="video/mp4" size="(\d+)"', fmt)
        if match:
            url, size = match.groups()
            format_list.append((url, size))
    format_list.sort(key=lambda x: int(x[1]), reverse=True)
    return format_list

def extract_filename_from_url(url):
    match = re.search(r'/([^/]+\.(mp4|mkv|webm|mov))', url)
    return match.group(1) if match else "video_downloaded.mp4"

def download_with_wget(url, output_filename):
    print(f"Downloading with wget:\nURL: {url}\nOutput File: {output_filename}")
    subprocess.run(['wget', '--continue', url, '-O', output_filename])

def main():
    parser = argparse.ArgumentParser(description="Download highest quality video from TNAFlix using wget")
    parser.add_argument('url', help="URL of the video")
    parser.add_argument('-F', '--list-formats', action='store_true', help="List available formats without downloading")
    args = parser.parse_args()

    # Extract video ID
    video_id_match = re.search(r'video(\d+)', args.url)
    if not video_id_match:
        raise ValueError("Invalid URL format")
    video_id = video_id_match.group(1)

    # Fetch video data
    video_data = fetch_video_data(video_id)

    # Get available formats
    formats = list_formats(video_data)
    if not formats:
        raise Exception("No video formats found")

    # If listing formats only
    if args.list_formats:
        print("Available formats:")
        for url, size in formats:
            filename = extract_filename_from_url(url)
            print(f"Size: {size} bytes - Filename: {filename} - URL: {url}")
        return

    # Otherwise, proceed to download highest quality format
    best_format_url = formats[0][0]
    base_filename = extract_filename_from_url(best_format_url)
    name_parts = base_filename.rsplit('.', 1)
    output_file = f"{name_parts[0]}_{video_id}.{name_parts[1]}" if len(name_parts) == 2 else f"{base_filename}_{video_id}"
    download_with_wget(best_format_url, output_file)

if __name__ == "__main__":
    main()
