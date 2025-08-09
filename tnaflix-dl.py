import argparse
import requests
import re
import subprocess
import os
from urllib.parse import urlparse, unquote
from tqdm import tqdm

def fetch_video_data(video_id):
    url = f"https://tnaflix.com/ajax/video-player/{video_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()

def parse_formats(html):
    """
    Parses <source src="..." type="video/mp4" size="1080"> entries.
    Returns list of dicts: {'url':..., 'size': int, 'quality': '1080p'}
    """
    pattern = re.compile(
        r'<source\s+[^>]*src="([^"]+)"[^>]*type="video\/mp4"[^>]*size="(\d+)"',
        re.IGNORECASE
    )
    matches = pattern.findall(html)
    formats = []
    seen = set()
    for src, size in matches:
        size_i = int(size)
        quality = f"{size_i}p"
        # dedupe by url or quality
        key = (src, size_i)
        if key in seen:
            continue
        seen.add(key)
        formats.append({'url': src, 'size': size_i, 'quality': quality})
    formats.sort(key=lambda x: x['size'], reverse=True)
    return formats

def extract_filename_from_url(url):
    path = urlparse(url).path
    name = os.path.basename(path)
    if not name:
        return "video_downloaded.mp4"
    return unquote(name)

def download_with_wget(url, output_filename):
    print(f"[wget] {url} -> {output_filename}")
    # -c continue, -q quiet removed so user sees wget output; keep -O to force name
    subprocess.run(['wget', '-c', url, '-O', output_filename])

def download_with_requests(url, output_filename):
    print(f"[requests] {url} -> {output_filename}")
    with requests.get(url, stream=True, timeout=15) as r:
        r.raise_for_status()
        total_size = int(r.headers.get('content-length') or 0)
        chunk_size = 8192
        # if total_size == 0, tqdm will show an indeterminate progress bar
        total = total_size if total_size > 0 else None
        with open(output_filename, 'wb') as fh, tqdm(total=total, unit='B', unit_scale=True, desc=output_filename) as pbar:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                fh.write(chunk)
                pbar.update(len(chunk))

def main():
    parser = argparse.ArgumentParser(description="TNAFlix video downloader (wget default; -r -> requests+tqdm)")
    parser.add_argument('url', help="URL of the video page (contains 'video<ID>')")
    parser.add_argument('-F', '--list-formats', action='store_true', help="List available formats (qualities) without downloading")
    parser.add_argument('-f', '--format', type=str, help="Select format by quality (e.g. 720p or 720)")
    parser.add_argument('-r', '--requests-downloader', action='store_true', help="Use requests + tqdm downloader instead of wget")
    args = parser.parse_args()

    # extract video id
    m = re.search(r'video(\d+)', args.url)
    if not m:
        parser.error("Video ID not found in URL (expects something like '...video12345...').")
    video_id = m.group(1)

    # fetch data
    data = fetch_video_data(video_id)
    html = data.get('html', '')
    if not html:
        raise RuntimeError("No HTML returned from AJAX endpoint.")

    # parse formats
    formats = parse_formats(html)
    if not formats:
        raise RuntimeError("No formats found in HTML.")

    if args.list_formats:
        print("Available formats (sorted by size desc):")
        for itm in formats:
            print(f"  {itm['quality']}  -  {itm['size']}  -  {extract_filename_from_url(itm['url'])}\n    {itm['url']}")
        return

    # select format
    selected = None
    if args.format:
        q = args.format.strip().lower()
        # normalize e.g. "720p" -> "720", "720" -> "720"
        if q.endswith('p'):
            qnum = q[:-1]
        else:
            qnum = q
        # try exact numeric match first
        for itm in formats:
            if str(itm['size']) == qnum:
                selected = itm
                break
        # fallback: try matching quality substring
        if selected is None:
            for itm in formats:
                if qnum in itm['quality'].lower():
                    selected = itm
                    break
        if selected is None:
            avail = ', '.join([f['quality'] for f in formats])
            parser.error(f"Requested format '{args.format}' not found. Available: {avail}")
    else:
        # default highest quality
        selected = formats[0]

    # prepare output filename
    base_name = extract_filename_from_url(selected['url'])
    # ensure unique by appending video id
    if '.' in base_name:
        name, ext = base_name.rsplit('.', 1)
        output_file = f"{name}_{video_id}.{ext}"
    else:
        output_file = f"{base_name}_{video_id}"

    # download
    if args.requests_downloader:
        download_with_requests(selected['url'], output_file)
    else:
        download_with_wget(selected['url'], output_file)

if __name__ == "__main__":
    main()
