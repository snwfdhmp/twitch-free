import hashlib
import json
import csv
import os
import random
import re
import subprocess
import tkinter as tk
import sys
from time import sleep
from shutil import rmtree, copyfileobj
from datetime import datetime, timedelta
from tkinter import filedialog
from urllib.parse import urlparse
from unicodedata import normalize
import asyncio
import grequests
import aiohttp
from bs4 import BeautifulSoup
from seleniumbase import SB
import requests
from packaging import version
import ffmpeg_downloader as ffdl
from tqdm import tqdm
from ffmpeg_progress_yield import FfmpegProgress


CURRENT_VERSION = "1.3.6"
SUPPORTED_FORMATS = [".mp4", ".mkv", ".mov", ".avi", ".ts"]

if sys.platform == 'win32':
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# keep
def quote_filename(filename):
    if not filename.startswith("'") and not filename.endswith("'"):
        filename = filename.replace("'", "'\"'\"'")
        filename = f"'{filename}'"
    return filename


def ask_to_redownload(output_path):
    while True:
        choice = input(f"\nFile already exists at {output_path}. Do you want to redownload it? (Y/N): ").strip().lower()
        if choice in ['y', 'n']:
            return choice == 'y'
        print("Invalid input! Please enter 'Y' for Yes or 'N' for No.")


def get_websites_tracker_url():
    while True:
        tracker_url = input("Enter Twitchtracker/Streamscharts/Sullygnome url: ").strip()
        if re.match(r"^(https?:\/\/)?(www\.)?(twitchtracker\.com|streamscharts\.com|sullygnome\.com)\/.*", tracker_url):
            return tracker_url

        print("\n✖  Invalid URL! Please enter a URL from Twitchtracker, Streamscharts, or Sullygnome.\n")


def print_get_twitch_url_menu():
    twitch_url = input("Enter Twitch URL: ").strip(" \"'")
    if "twitch.tv" in twitch_url:
        return twitch_url
    print("\n✖  Invalid Twitch URL! Please try again:\n")
    return print_get_twitch_url_menu()


def get_twitch_or_tracker_url():
    while True:
        url = input("Enter Twitchtracker/Streamscharts/Sullygnome/Twitch URL: ").strip()

        if re.match(r"^(https?:\/\/)?(www\.)?(twitchtracker\.com|streamscharts\.com|sullygnome\.com|twitch\.tv)\/.*", url):
            return url

        print("\n✖  Invalid URL! Please enter a URL from Twitchtracker, Streamscharts, Sullygnome, or Twitch.\n")


def get_latest_version(retries=3):
    for attempt in range(retries):
        try:
            res = requests.get("https://api.github.com/repos/MacielG1/VodRecovery/releases/latest", timeout=30)
            if res.status_code == 200:
                release_info = res.json()
                return release_info["tag_name"]
            else:
                return None
        except Exception:
            if attempt < retries - 1: 
                sleep(3)  
                continue 
            else:
                return None


def check_for_updates():
    latest_version = version.parse(get_latest_version())
    current_version = version.parse(CURRENT_VERSION)
    if latest_version and current_version:
        if latest_version != current_version:
            print(f"\n\033[34mNew version ({latest_version}) - Download at: https://github.com/MacielG1/VodRecovery/releases/latest\033[0m")
            input("\nPress Enter to continue...")
            return run_vod_recover()
        else:
            print(f"\n\033[92m\u2713 Vod Recovery is updated to {CURRENT_VERSION}!\033[0m")
            input("\nPress Enter to continue...")
            return
    else:
        print("\n✖  Could not check for updates!")

def sanitize_filename(filename, restricted=False):
    if filename == "":
        return ""

    def replace_insane(char):
        if not restricted and char == "\n":
            return "\0 "
        elif not restricted and char in '"*:<>?|/\\':
            return {"/": "\u29f8", "\\": "\u29f9"}.get(char, chr(ord(char) + 0xFEE0))
        elif char == "?" or ord(char) < 32 or ord(char) == 127:
            return ""
        elif char == '"':
            return "" if restricted else "'"
        elif char == ":":
            return "\0_\0-" if restricted else "\0 \0-"
        elif char in "\\/|*<>":
            return "\0_"
        if restricted and (
            char in "!&'()[]{}$;`^,#" or char.isspace() or ord(char) > 127
        ):
            return "\0_"
        return char

    if restricted:
        filename = normalize("NFKC", filename)
    filename = re.sub(
        r"[0-9]+(?::[0-9]+)+", lambda m: m.group(0).replace(":", "_"), filename
    )
    result = "".join(map(replace_insane, filename))
    result = re.sub(r"(\0.)(?:(?=\1)..)+", r"\1", result)
    strip_re = r"(?:\0.|[ _-])*"
    result = re.sub(f"^\0.{strip_re}|{strip_re}\0.$", "", result)
    result = result.replace("\0", "") or "_"

    while "__" in result:
        result = result.replace("__", "_")
    result = result.strip("_")
    if restricted and result.startswith("-_"):
        result = result[2:]
    if result.startswith("-"):
        result = "_" + result[len("-") :]
    result = result.lstrip(".")
    if not result:
        result = "_"
    return result


def read_config_file(config_file):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "config", f"{config_file}.json")
    with open(config_path, encoding="utf-8") as config_file:
        config = json.load(config_file)
    return config


def open_file(file_path):
    if sys.platform.startswith("darwin"):
        subprocess.call(("open", file_path))
    elif os.name == "nt":
        subprocess.Popen(["start", file_path], shell=True)
    elif os.name == "posix":
        subprocess.call(("xdg-open", file_path))
    else:
        print(f"\nFile Location: {file_path}")


def print_help():
    try:
        help_data = read_config_file("help")
        print("\n--------------- Help Section ---------------")
        for menu, options in help_data.items():
            print(f"\n{menu.replace('_', ' ').title()}:")
            for option, description in options.items():
                print(f"  {option}: {description}")
        print("\n --------------- End of Help Section ---------------\n")
    except Exception as error:
        print(f"An unexpected error occurred: {error}")


def read_text_file(text_file_path):
    lines = []
    with open(text_file_path, "r", encoding="utf-8") as text_file:
        for line in text_file:
            lines.append(line.rstrip())
    return lines


def write_text_file(input_text, destination_path):
    with open(destination_path, "a+", encoding="utf-8") as text_file:
        text_file.write(input_text + "\n")


def write_m3u8_to_file(m3u8_link, destination_path, max_retries=5):
    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(m3u8_link, timeout=10)
            response.raise_for_status()

            with open(destination_path, "w", encoding="utf-8") as m3u8_file:
                m3u8_file.write(response.text)

            return m3u8_file

        except Exception:
            attempt += 1
            sleep(1)
    raise Exception(f"Failed to write M3U8 after {max_retries} attempts.")


def read_csv_file(csv_file_path):
    with open(csv_file_path, "r", encoding="utf-8") as csv_file:
        return list(csv.reader(csv_file))

def get_log_filepath(streamer_name, video_id):
    log_filename = os.path.join(get_default_directory(), f"{streamer_name}_{video_id}_log.txt")
    return log_filename


def get_vod_filepath(streamer_name, video_id):
    vod_filename = os.path.join(get_default_directory(), f"{streamer_name}_{video_id}.m3u8")
    return vod_filename


def get_script_directory():
    return os.path.dirname(os.path.realpath(__file__))


def return_user_agent():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_agents = read_text_file(os.path.join(script_dir, "lib", "user_agents.txt"))
    header = {"user-agent": random.choice(user_agents)}
    return header


def calculate_epoch_timestamp(timestamp, seconds):
    try:
        epoch_timestamp = ((datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S") + timedelta(seconds=seconds)) - datetime(1970, 1, 1)).total_seconds()
        return epoch_timestamp
    except ValueError:
        return None


def calculate_days_since_broadcast(start_timestamp):
    if start_timestamp is None:
        return 0
    vod_age = datetime.today() - datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
    return max(vod_age.days, 0)


def is_video_muted(m3u8_link):
    response = requests.get(m3u8_link, timeout=10).text
    return bool("unmuted" in response)


def calculate_broadcast_duration_in_minutes(hours, minutes):
    return (int(hours) * 60) + int(minutes)


def calculate_max_clip_offset(video_duration):
    return (video_duration * 60) + 2000


def parse_streamer_from_csv_filename(csv_filename):
    _, file_name = os.path.split(csv_filename)
    streamer_name = file_name.strip()
    return streamer_name.split()[0]

# keep
def parse_streamer_from_m3u8_link(m3u8_link):
    indices = [i.start() for i in re.finditer("_", m3u8_link)]
    streamer_name = m3u8_link[indices[0] + 1 : indices[-2]]
    return streamer_name

# keep
def parse_video_id_from_m3u8_link(m3u8_link):
    indices = [i.start() for i in re.finditer("_", m3u8_link)]
    video_id = m3u8_link[
        indices[0] + len(parse_streamer_from_m3u8_link(m3u8_link)) + 2 : indices[-1]
    ]
    return video_id


def parse_streamer_and_video_id_from_m3u8_link(m3u8_link):
    indices = [i.start() for i in re.finditer("_", m3u8_link)]
    streamer_name = m3u8_link[indices[0] + 1 : indices[-2]]
    video_id = m3u8_link[indices[0] + len(streamer_name) + 2 : indices[-1]]
    return f" - {streamer_name} [{video_id}]"


def parse_streamscharts_url(streamscharts_url):
    try:
        streamer_name = streamscharts_url.split("/channels/", 1)[1].split("/streams/")[0]
        video_id = streamscharts_url.split("/streams/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\033[91m \n✖  Invalid Streamscharts URL! Please try again:\n \033[0m")
        input("Press Enter to continue...")
        return run_vod_recover()


def parse_twitchtracker_url(twitchtracker_url):
    try:
        streamer_name = twitchtracker_url.split(".com/", 1)[1].split("/streams/")[0]
        video_id = twitchtracker_url.split("/streams/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\033[91m \n✖  Invalid Twitchtracker URL! Please try again:\n \033[0m")
        input("Press Enter to continue...")
        return run_vod_recover()


def parse_sullygnome_url(sullygnome_url):
    try:
        streamer_name = sullygnome_url.split("/channel/", 1)[1].split("/")[0]
        video_id = sullygnome_url.split("/stream/", 1)[1]
        return streamer_name, video_id
    except IndexError:
        print("\033[91m \n✖  Invalid SullyGnome URL! Please try again:\n \033[0m")
        input("Press Enter to continue...")
        return run_vod_recover()


def get_m3u8_file_dialog():
    try:
        window = tk.Tk()
        window.wm_attributes("-topmost", 1)
        window.withdraw()
        directory = get_default_directory()
        file_path = filedialog.askopenfilename(
            parent=window,
            initialdir=directory,
            title="Select A File",
            filetypes=(("M3U8 files", "*.m3u8"), ("All files", "*")),
        )
        window.destroy()
        return file_path
    except tk.TclError:
        file_path = input("Enter the full path to the M3U8 file: ").strip(' "\'')
        while not file_path:
            return None
        while not os.path.exists(file_path):
            file_path = input("File does not exist! Enter a valid path: ").strip(' "\'')
        return file_path


def parse_vod_filename(m3u8_video_filename):
    base = os.path.basename(m3u8_video_filename)
    streamer_name, video_id = base.split(".m3u8", 1)[0].rsplit("_", 1)
    return streamer_name, video_id


def parse_vod_filename_with_Brackets(m3u8_video_filename):
    base = os.path.basename(m3u8_video_filename)
    streamer_name, video_id = base.split(".m3u8", 1)[0].rsplit("_", 1)
    return f" - {streamer_name} [{video_id}]"


def remove_chars_from_ordinal_numbers(datetime_string):
    ordinal_numbers = ["th", "nd", "st", "rd"]
    for exclude_string in ordinal_numbers:
        if exclude_string in datetime_string:
            return datetime_string.replace(datetime_string.split(" ")[1], datetime_string.split(" ")[1][:-len(exclude_string)])


def generate_website_links(streamer_name, video_id, tracker_url=None):
    website_list = [
        f"https://sullygnome.com/channel/{streamer_name}/stream/{video_id}",
        f"https://twitchtracker.com/{streamer_name}/streams/{video_id}",
        f"https://streamscharts.com/channels/{streamer_name}/streams/{video_id}",
    ]
    if tracker_url:
        website_list = [link for link in website_list if tracker_url not in link]
    return website_list


def convert_url(url, target):
    # converts url to the specified target website
    patterns = {
        "sullygnome": "https://sullygnome.com/channel/{}/stream/{}",
        "twitchtracker": "https://twitchtracker.com/{}/streams/{}",
        "streamscharts": "https://streamscharts.com/channels/{}/streams/{}",
    }
    parsed_url = urlparse(url)
    streamer, video_id = None, None

    if "sullygnome" in url:
        streamer = parsed_url.path.split("/")[2]
        video_id = parsed_url.path.split("/")[4]

    elif "twitchtracker" in url:
        streamer = parsed_url.path.split("/")[1]
        video_id = parsed_url.path.split("/")[3]

    elif "streamscharts" in url:
        streamer = parsed_url.path.split("/")[2]
        video_id = parsed_url.path.split("/")[4]

    if streamer and video_id:
        return patterns[target].format(streamer, video_id)


def extract_offset(clip_url):
    clip_offset = re.search(r"(?:-offset|-index)-(\d+)", clip_url)
    return clip_offset.group(1)


def get_clip_format(video_id, offsets):
    default_clip_list = [f"https://clips-media-assets2.twitch.tv/{video_id}-offset-{i}.mp4" for i in range(0, offsets, 2)]
    alternate_clip_list = [f"https://clips-media-assets2.twitch.tv/vod-{video_id}-offset-{i}.mp4" for i in range(0, offsets, 2)]
    legacy_clip_list = [f"https://clips-media-assets2.twitch.tv/{video_id}-index-{i:010}.mp4" for i in range(offsets)]

    clip_format_dict = {
        "1": default_clip_list,
        "2": alternate_clip_list,
        "3": legacy_clip_list,
    }
    return clip_format_dict


def get_random_clip_information():
    while True:
        url = get_websites_tracker_url()

        if "streamscharts" in url:
            _, video_id = parse_streamscharts_url(url)
            break
        if "twitchtracker" in url:
            _, video_id = parse_twitchtracker_url(url)
            break
        if "sullygnome" in url:
            _, video_id = parse_sullygnome_url(url)
            break

        print("\n✖  Link not supported! Please try again:\n")

    while True:
        duration = get_time_input_HH_MM("Enter stream duration in (HH:MM) format: ")
        hours, minutes = map(int, duration.split(":"))
        if hours >= 0 and minutes >= 0:
            break
    return video_id, hours, minutes


def manual_clip_recover():
    while True:
        streamer_name = input("Enter the Streamer Name: ")
        if streamer_name.strip():
            break
        else:
            print("\n✖  No streamer name! Please try again:\n")
    while True:
        video_id = input("Enter the Video ID (from: Twitchtracker/Streamscharts/Sullygnome): ")
        if video_id.strip():
            break
        else:
            print("\n✖  No video ID! Please try again:\n")

    while True:
        duration = get_time_input_HH_MM("Enter stream duration in (HH:MM) format: ")

        hours, minutes = map(int, duration.split(":"))
        if hours >= 0 and minutes >= 0:
            total_minutes = hours * 60 + minutes
            break

    clip_recover(streamer_name, video_id, total_minutes)


def website_clip_recover():
    tracker_url = get_websites_tracker_url()

    if not tracker_url.startswith("https://"):
        tracker_url = "https://" + tracker_url
    if "streamscharts" in tracker_url:
        streamer, video_id = parse_streamscharts_url(tracker_url)

        print("\nRetrieving stream duration from Streamscharts")
        duration_streamscharts = parse_duration_streamscharts(tracker_url)
        # print(f"Duration: {duration_streamscharts}")

        clip_recover(streamer, video_id, int(duration_streamscharts))
    elif "twitchtracker" in tracker_url:
        streamer, video_id = parse_twitchtracker_url(tracker_url)

        print("\nRetrieving stream duration from Twitchtracker")
        duration_twitchtracker = parse_duration_twitchtracker(tracker_url)
        # print(f"Duration: {duration_twitchtracker}")

        clip_recover(streamer, video_id, int(duration_twitchtracker))
    elif "sullygnome" in tracker_url:
        streamer, video_id = parse_sullygnome_url(tracker_url)

        print("\nRetrieving stream duration from Sullygnome")
        duration_sullygnome = parse_duration_sullygnome(tracker_url)
        if duration_sullygnome is None:
            print("Could not retrieve duration from Sullygnome. Try a different URL.\n")
            return print_main_menu()
        # print(f"Duration: {duration_sullygnome}")
        clip_recover(streamer, video_id, int(duration_sullygnome))
    else:
        print("\n✖  Link not supported! Try again...\n")
        return run_vod_recover()


def manual_vod_recover():
    while True:
        streamer_name = input("Enter the Streamer Name: ")
        if streamer_name.lower().strip():
            break

        print("\n✖  No streamer name! Please try again:\n")

    while True:
        video_id = input("Enter the Video ID (from: Twitchtracker/Streamscharts/Sullygnome): ")
        if video_id.strip():
            break
        else:
            print("\n✖  No video ID! Please try again:\n")

    timestamp = get_time_input_YYYY_MM_DD_HH_MM_SS("Enter VOD Datetime YYYY-MM-DD HH:MM:SS (24-hour format, UTC): ")

    m3u8_link = vod_recover(streamer_name, video_id, timestamp)
    if m3u8_link is None:
        sys.exit("No M3U8 link found! Exiting...")

    m3u8_source = process_m3u8_configuration(m3u8_link)
    handle_download_menu(m3u8_source)

async def fetch_status(session, url, retries=3, timeout=30):
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    return url
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt < retries - 1:
                await asyncio.sleep(2)
    return None


async def get_vod_urls(streamer_name, video_id, start_timestamp):
    m3u8_link_list = []
    script_dir = get_script_directory()
    domains = read_text_file(os.path.join(script_dir, "lib", "domains.txt"))

    print("\nSearching for M3U8 URL...")

    m3u8_link_list = [
        f"{domain.strip()}{str(hashlib.sha1(f'{streamer_name}_{video_id}_{int(calculate_epoch_timestamp(start_timestamp, seconds))}'.encode('utf-8')).hexdigest())[:20]}_{streamer_name}_{video_id}_{int(calculate_epoch_timestamp(start_timestamp, seconds))}/chunked/index-dvr.m3u8"
        for seconds in range(60)
        for domain in domains if domain.strip()
    ]

    print("\n".join(m3u8_link_list))
    print("\nExiting process...")

    sys.exit(0) # early exit because that's all we need

    return successful_url


def return_supported_qualities(m3u8_link):
    if m3u8_link is None:
        return None
    
    if "chunked" in m3u8_link:
        return m3u8_link

    print("\nChecking for available qualities...")
    resolutions = ["chunked", "1080p60", "1080p30", "720p60", "720p30", "480p60", "480p30"]
    request_list = [
        grequests.get(m3u8_link.replace("chunked", resolution))
        for resolution in resolutions
    ]
    responses = grequests.map(request_list)
    valid_resolutions = [
        resolution
        for resolution, response in zip(resolutions, responses)
        if response and response.status_code == 200
    ]

    if not valid_resolutions:
        return None

    valid_resolutions.sort(key=resolutions.index)

    if always_best_quality:
        return m3u8_link.replace("chunked", valid_resolutions[0])

    print("\nQuality Options:")
    for idx, resolution in enumerate(valid_resolutions, 1):
        if "chunked" in resolution:
            print(f"{idx}. {resolution.replace('chunked', 'Chunked (Best Quality)')}")
        else:
            print(f"{idx}. {resolution}")

    user_option = get_user_resolution_choice(m3u8_link, valid_resolutions)
    return user_option


def get_user_resolution_choice(m3u8_link, valid_resolutions):
    try:
        choice = int(input("Choose a quality: "))
        if 1 <= choice <= len(valid_resolutions):
            quality = valid_resolutions[choice - 1]
            user_option = m3u8_link.replace("chunked", quality)
            return user_option

        print("\n✖  Invalid option! Please try again:\n")
        return get_user_resolution_choice(m3u8_link, valid_resolutions)
    except ValueError:
        print("\n✖  Invalid option! Please try again:\n")
        return get_user_resolution_choice(m3u8_link, valid_resolutions)


def parse_website_duration(duration_string):
    if isinstance(duration_string, list):
        duration_string = " ".join(duration_string)
    if not isinstance(duration_string, str):
        try:
            duration_string = str(duration_string)
        except Exception:
            return 0

    pattern = r"(\d+)\s*(h(?:ou)?r?s?|m(?:in)?(?:ute)?s?)"
    matches = re.findall(pattern, duration_string, re.IGNORECASE)
    if not matches:
        try:
            minutes = int(duration_string)
            return calculate_broadcast_duration_in_minutes(0, minutes)
        except ValueError:
            return 0

    time_units = {"h": 0, "m": 0}
    for value, unit in matches:
        time_units[unit[0].lower()] = int(value)

    return calculate_broadcast_duration_in_minutes(time_units["h"], time_units["m"])


def handle_cloudflare(sb):
    try:
        sb.uc_gui_handle_captcha()
    except Exception:
        pass
    finally:
        # delete folder generated by selenium browser
        if os.path.exists("downloaded_files"):
            rmtree("downloaded_files")


def parse_streamscharts_duration_data(bs):
    streamscharts_duration = bs.find_all("div", {"class": "text-xs font-bold"})[3].text
    streamscharts_duration_in_minutes = parse_website_duration(streamscharts_duration)
    return streamscharts_duration_in_minutes


def parse_duration_streamscharts(streamscharts_url):
    try:
        # Method 1: Using requests
        response = requests.get(streamscharts_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_streamscharts_duration_data(bs)

        # Method 2: Using Selenium
        print("Opening Streamcharts with browser...")
        with SB(uc=True) as sb:
            sb.uc_open_with_reconnect(streamscharts_url, reconnect_time=3)
            handle_cloudflare(sb)
            bs = BeautifulSoup(sb.driver.page_source, "html.parser")
            return parse_streamscharts_duration_data(bs)

    except Exception:
        pass

    sullygnome_url = convert_url(streamscharts_url, "sullygnome")
    if sullygnome_url:
        return parse_duration_sullygnome(sullygnome_url)
    return None


def parse_twitchtracker_duration_data(bs):
    twitchtracker_duration = bs.find_all("div", {"class": "g-x-s-value"})[0].text
    twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
    return twitchtracker_duration_in_minutes


def parse_duration_twitchtracker(twitchtracker_url, try_alternative=True):
    try:
        # Method 1: Using requests
        response = requests.get(twitchtracker_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_twitchtracker_duration_data(bs)

        # Method 2: Using Selenium
        print("Opening Twitchtracker with browser...")
        with SB(uc=True) as sb:
            sb.uc_open_with_reconnect(twitchtracker_url, reconnect_time=3)
            handle_cloudflare(sb)
            bs = BeautifulSoup(sb.driver.page_source, "html.parser")
            return parse_twitchtracker_duration_data(bs)

    except Exception:
        pass

    if try_alternative:
        sullygnome_url = convert_url(twitchtracker_url, "sullygnome")
        if sullygnome_url:
            return parse_duration_sullygnome(sullygnome_url)
    return None


def parse_sullygnome_duration_data(bs):
    sullygnome_duration = bs.find_all("div", {"class": "MiddleSubHeaderItemValue"})[7].text.split(",")
    sullygnome_duration_in_minutes = parse_website_duration(sullygnome_duration)
    return sullygnome_duration_in_minutes


def parse_duration_sullygnome(sullygnome_url):
    try:
        # Method 1: Using requests
        response = requests.get(sullygnome_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_sullygnome_duration_data(bs)

        # Method 2: Using Selenium
        print("Opening Sullygnome with browser...")
        with SB(uc=True) as sb:
            sb.uc_open_with_reconnect(sullygnome_url, reconnect_time=3)
            handle_cloudflare(sb)
            bs = BeautifulSoup(sb.driver.page_source, "html.parser")
            return parse_sullygnome_duration_data(bs)

    except Exception:
        pass

    sullygnome_url = convert_url(sullygnome_url, "twitchtracker")
    if sullygnome_url:
        return parse_duration_twitchtracker(sullygnome_url, try_alternative=False)
    return None


def parse_streamscharts_datetime_data(bs):
    stream_date = (
        bs.find_all("time", {"class": "ml-2 font-bold"})[0]
        .text.strip()
        .replace(",", "")
        + ":00"
    )
    stream_datetime = datetime.strptime(stream_date, "%d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")


    try:
        streamcharts_duration = bs.find_all("span", {"class": "mx-2 font-bold"})[0].text
        streamcharts_duration_in_minutes = parse_website_duration(streamcharts_duration)
    except Exception:
        streamcharts_duration_in_minutes = None

    print(f"Datetime: {stream_datetime}")
    return stream_datetime, streamcharts_duration_in_minutes


def parse_datetime_streamscharts(streamscharts_url):
    print("\nRetrieving datetime from Streamscharts...")

    try:
        # Method 1: Using requests
        response = requests.get(
            streamscharts_url, headers=return_user_agent(), timeout=10
        )
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_streamscharts_datetime_data(bs)

        # Method 2: Using Selenium
        print("Opening Streamscharts with browser...")

        with SB(uc=True) as sb:
            sb.uc_open_with_reconnect(streamscharts_url, reconnect_time=3)
            handle_cloudflare(sb)
            bs = BeautifulSoup(sb.driver.page_source, "html.parser")

            return parse_streamscharts_datetime_data(bs)

    except Exception:
        pass
    return None, None


def parse_twitchtracker_datetime_data(bs):
    twitchtracker_datetime = bs.find_all("div", {"class": "stream-timestamp-dt"})[0].text
    try:
        twitchtracker_duration = bs.find_all("div", {"class": "g-x-s-value"})[0].text
        twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
    except Exception:
        twitchtracker_duration_in_minutes = None

    print(f"Datetime: {twitchtracker_datetime}")
    return twitchtracker_datetime, twitchtracker_duration_in_minutes


def parse_datetime_twitchtracker(twitchtracker_url):
    print("\nRetrieving datetime from Twitchtracker...")

    try:
        # Method 1: Using requests
        response = requests.get(twitchtracker_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_twitchtracker_datetime_data(bs)

        # Method 2: Using Selenium
        print("Opening Twitchtracker with browser...")
        with SB(uc=True) as sb:
            sb.uc_open_with_reconnect(twitchtracker_url, reconnect_time=3)
            handle_cloudflare(sb)

            bs = BeautifulSoup(sb.driver.page_source, "html.parser")
            description_meta = bs.find("meta", {"name": "description"})
            twitchtracker_datetime = None

            if description_meta:
                description_content = description_meta.get("content")
                match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", description_content)
                if match:
                    twitchtracker_datetime = match.group(0)
                    print(f"Datetime: {twitchtracker_datetime}")

                    try:
                        twitchtracker_duration = bs.find_all("div", {"class": "g-x-s-value"})[0].text
                        twitchtracker_duration_in_minutes = parse_website_duration(twitchtracker_duration)
                    except Exception:
                        twitchtracker_duration_in_minutes = None

                    return twitchtracker_datetime, twitchtracker_duration_in_minutes
    except Exception:
        pass
    return None, None


def parse_sullygnome_datetime_data(bs):
    stream_date = bs.find_all("div", {"class": "MiddleSubHeaderItemValue"})[6].text
    modified_stream_date = remove_chars_from_ordinal_numbers(stream_date)
    formatted_stream_date = datetime.strptime(modified_stream_date, "%A %d %B %I:%M%p").strftime("%m-%d %H:%M:%S")
    sullygnome_datetime = str(datetime.now().year) + "-" + formatted_stream_date

    sullygnome_duration = bs.find_all("div", {"class": "MiddleSubHeaderItemValue"})[7].text.split(",")
    sullygnome_duration_in_minutes = parse_website_duration(sullygnome_duration)

    print(f"Datetime: {sullygnome_datetime}")
    return sullygnome_datetime, sullygnome_duration_in_minutes


def parse_datetime_sullygnome(sullygnome_url):
    print("\nRetrieving datetime from Sullygnome...")

    try:
        # Method 1: Using requests
        response = requests.get(sullygnome_url, headers=return_user_agent(), timeout=10)
        if response.status_code == 200:
            bs = BeautifulSoup(response.content, "html.parser")
            return parse_sullygnome_datetime_data(bs)

        # Method 2: Using Selenium
        print("Opening Sullygnome with browser...")
        with SB(uc=True) as sb:
            sb.uc_open_with_reconnect(sullygnome_url, reconnect_time=3)
            handle_cloudflare(sb)
            bs = BeautifulSoup(sb.driver.page_source, "html.parser")
            return parse_sullygnome_datetime_data(bs)

    except Exception:
        pass
    return None, None


def unmute_vod(m3u8_link):
    video_filepath = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
    
    write_m3u8_to_file(m3u8_link, video_filepath)
    
    with open(video_filepath, "r+", encoding="utf-8") as video_file:
        file_contents = video_file.readlines()
        video_file.seek(0)
        
        is_muted = is_video_muted(m3u8_link)
        base_link = m3u8_link.replace("index-dvr.m3u8", "")
        counter = 0
        
        for segment in file_contents:
            if segment.startswith("#"):
                video_file.write(segment)
            else:
                if is_muted:
                    if "-unmuted" in segment:
                        video_file.write(f"{base_link}{counter}-muted.ts\n")
                    else:
                        video_file.write(f"{base_link}{counter}.ts\n")
                else:
                    video_file.write(f"{base_link}{counter}.ts\n")
                counter += 1
        
        video_file.truncate()
    
    if is_muted:
        print(f"{os.path.normpath(video_filepath)} has been unmuted!\n")

def return_m3u8_duration(m3u8_link):
    total_duration = 0
    file_contents = requests.get(m3u8_link, stream=True, timeout=30).text.splitlines()
    for line in file_contents:
        if line.startswith("#EXTINF:"):
            segment_duration = float(line.split(":")[1].split(",")[0])
            total_duration += segment_duration
    total_minutes = int(total_duration // 60)
    return total_minutes


def process_m3u8_configuration(m3u8_link, skip_check=False):
    playlist_segments = get_all_playlist_segments(m3u8_link)

    check_segments = read_config_by_key("settings", "CHECK_SEGMENTS") and not skip_check

    m3u8_source = None
    if is_video_muted(m3u8_link):
        print("Video contains muted segments")
        if read_config_by_key("settings", "UNMUTE_VIDEO"):
            unmute_vod(m3u8_link)
            m3u8_source = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link),parse_video_id_from_m3u8_link(m3u8_link),)
    else:
        m3u8_source = m3u8_link
        os.remove(get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link)))
    if check_segments:
        print("Checking valid segments...")
        asyncio.run(validate_playlist_segments(playlist_segments))
    return m3u8_source


def get_all_playlist_segments(m3u8_link):
    video_file_path = get_vod_filepath(parse_streamer_from_m3u8_link(m3u8_link), parse_video_id_from_m3u8_link(m3u8_link))
    write_m3u8_to_file(m3u8_link, video_file_path)

    segment_list = []
    base_link = m3u8_link.replace("index-dvr.m3u8", "")
    counter = 0
    
    with open(video_file_path, "r+", encoding="utf-8") as video_file:
        file_contents = video_file.readlines()
        video_file.seek(0)
        
        for segment in file_contents:
            if segment.startswith("#"):
                video_file.write(segment)
            else:
                if "-unmuted" in segment:
                    new_segment = f"{base_link}{counter}-muted.ts"
                else:
                    new_segment = f"{base_link}{counter}.ts"
                
                video_file.write(f"{new_segment}\n")
                segment_list.append(new_segment)
                counter += 1
        
        video_file.truncate()
    return segment_list


async def validate_playlist_segments(segments):
    valid_segments = []
    all_segments = [url.strip() for url in segments]
    available_segment_count = 0

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_status(session, url) for url in all_segments]
        for index, task in enumerate(asyncio.as_completed(tasks)):
            url = await task
            if url:
                available_segment_count += 1
                valid_segments.append(url)
            print(f"\rChecking segments {index + 1} / {len(all_segments)}", end="")

    print()
    if available_segment_count == len(all_segments) or available_segment_count == 0:
        print("All Segments are Available\n")
    elif available_segment_count < len(all_segments):
        print(f"{available_segment_count} out of {len(all_segments)} Segments are Available. To recheck the segments select option 4 from the menu.\n")

    return valid_segments


def vod_recover(streamer_name, video_id, timestamp, tracker_url=None):
    vod_age = calculate_days_since_broadcast(timestamp)

    if vod_age > 60:
        print("Video is older than 60 days. Chances of recovery are very slim.")
    vod_url = None
    if timestamp:
        vod_url = return_supported_qualities(asyncio.run(get_vod_urls(streamer_name, video_id, timestamp)))

    if vod_url is None:
        alternate_websites = generate_website_links(streamer_name, video_id, tracker_url)

        print("\nUnable to recover with provided url! Trying alternate sources...")
        all_timestamps = [timestamp]

        # Check if any alternate websites have a different timestamp
        for website in alternate_websites:
            parsed_timestamp = None
            if "streamscharts" in website:                                                                                                              
                parsed_timestamp, _ = parse_datetime_streamscharts(website)
            elif "twitchtracker" in website:
                parsed_timestamp, _ = parse_datetime_twitchtracker(website)
            elif "sullygnome" in website:
                # If the timestamp shows a year different from the current one, skip it since SullyGnome doesn't provide the year
                if timestamp and datetime.now().year != int(timestamp.split("-")[0]):
                    continue
                parsed_timestamp, _ = parse_datetime_sullygnome(website)

            if (parsed_timestamp and parsed_timestamp != timestamp and parsed_timestamp not in all_timestamps):
                all_timestamps.append(parsed_timestamp)
                vod_url = return_supported_qualities(asyncio.run(get_vod_urls(streamer_name, video_id, parsed_timestamp)))
                if vod_url:
                    return vod_url
        if not any(all_timestamps):
            print("\033[91m \n✖  Unable to get the datetime, Please input it manually using the recovery option. \033[0m")
            input("\nPress Enter to continue...")
            run_vod_recover()
        if not vod_url:
            print("\033[91m \n✖  Unable to recover the video! \033[0m")
            input("\nPress Enter to continue...")
            run_vod_recover()

    return vod_url

# keep
def get_m3u8_duration(m3u8_link):
    command = [
        get_ffprobe_path(),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        m3u8_link
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        if result.returncode != 0:
            return None

        duration = result.stdout.strip()
        if duration:
            return float(duration)

    except Exception:
        return None

# keep
def handle_progress_bar(command, output_filename, total_duration):
    try:
        ff = FfmpegProgress(command)
        with tqdm(total=100, position=0, desc=output_filename, leave=None, colour="green", unit="%", bar_format="{l_bar}{bar}| {percentage:.1f}/100% [{elapsed}]{postfix}") as pbar:
            for progress in ff.run_command_with_progress():
                pbar.update(progress - pbar.n)
                
                if total_duration is not None:
                    total_duration_seconds = total_duration
                    current_duration_seconds = (progress / 100) * total_duration_seconds
                    current_duration_str = str(timedelta(seconds=int(current_duration_seconds)))
                    total_duration_str = str(timedelta(seconds=int(total_duration_seconds)))
                    pbar.set_postfix_str(f"{current_duration_str}/{total_duration_str}")

            pbar.close()
        return True
    except Exception as e:
        print(f"Error: {str(e).strip()}")
        raise Exception

# keep
def handle_file_already_exists(output_path):
    if os.path.exists(output_path):
        if not ask_to_redownload(output_path):
            print("\n\033[94m\u2713 Skipping download!\033[0m\n")
            input("Press Enter to continue...")
            return run_vod_recover()
        
# keep
def handle_retry_command(command):
    try:
        retry_command = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
        print("Retrying command: " + retry_command)
        subprocess.run(retry_command, shell=True, check=True)
        return True
    except Exception:
        return False

# keep
def download_m3u8_video_url(m3u8_link, output_filename):
    if os.name != 'nt':
        output_filename = quote_filename(output_filename)

    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    downloader = get_default_downloader()

    if downloader == "ffmpeg":
        command = [
            get_ffmpeg_path(), 
            "-i", m3u8_link, 
            "-hide_banner",
            "-c", "copy", 
            "-f", get_ffmpeg_format(get_default_video_format()),
            "-y", output_path
        ]
    else:
        command = [
            "yt-dlp",
            m3u8_link,
            "-o", output_path,
        ]
        custom_options = get_yt_dlp_custom_options()
        if custom_options:
            command.extend(custom_options)

    print("\nCommand: " + " ".join(command) + "\n")

    try:
        if downloader == "ffmpeg" and get_use_progress_bar():
            total_duration = get_m3u8_duration(m3u8_link)
            handle_progress_bar(command, output_filename, total_duration)
        else:
            subprocess.run(command, shell=True, check=True)
        return True
    except Exception:
        handle_retry_command(command)

# keep
def download_m3u8_video_file(m3u8_file_path, output_filename):    
    output_path = os.path.normpath(os.path.join(get_default_directory(), output_filename))
    handle_file_already_exists(output_path)

    downloader = get_default_downloader()

    if downloader == "ffmpeg":
        command = [
            get_ffmpeg_path(),
            "-protocol_whitelist", "file,http,https,tcp,tls",
            "-hide_banner",
            "-ignore_unknown",
            "-i", m3u8_file_path,
            "-c", "copy",
            "-f", get_ffmpeg_format(get_default_video_format()),
            "-y", output_path,
        ]

    elif downloader == "yt-dlp":
        if os.name == 'nt':  # For Windows
            m3u8_file_path = f"file:\\\\{m3u8_file_path}"
        else:  # For Linux and macOS
            m3u8_file_path = f"file://{m3u8_file_path}"
        command = [
            "yt-dlp",
            "--enable-file-urls",
            m3u8_file_path,
            "-o", output_path,
        ]
        custom_options = get_yt_dlp_custom_options()
        if custom_options:
            command.extend(custom_options)

    print("\nCommand: " + " ".join(command) + "\n")

    try:
        if downloader == "ffmpeg" and get_use_progress_bar():
            total_duration = get_m3u8_duration(m3u8_file_path)
            handle_progress_bar(command, output_filename, total_duration)

        else:
            subprocess.run(command, shell=True, check=True)
        return True
    except Exception:
        handle_retry_command(command)

# keep
def handle_vod_url_normal(m3u8_source, title=None, stream_date=None):
    is_file = os.path.isfile(m3u8_source)

    if is_file:
        vod_filename = get_filename_for_file_source(m3u8_source, title=title, stream_date=stream_date)

        success = download_m3u8_video_file(m3u8_source, vod_filename)
        if not success:
            return print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")
        os.remove(m3u8_source)
    else:
        vod_filename = get_filename_for_url_source(m3u8_source, title=title, stream_date=stream_date)

        success = download_m3u8_video_url(m3u8_source, vod_filename)
        if not success:
            print(f"\n\033[91m\u2717 Failed to download Vod: {vod_filename}\033[0m\n")
            return

    print(f"\n\033[92m\u2713 Vod downloaded to {os.path.join(get_default_directory(), vod_filename)}\033[0m\n")

# keep
def format_date(date_string):
    try:
        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
    except ValueError:
        return None

# keep
def get_filename_for_file_source(m3u8_source, title, stream_date):
    streamer_name, video_id = parse_vod_filename(m3u8_source)
    formatted_date = format_date(stream_date) if stream_date else None

    filename_parts = [streamer_name]

    if formatted_date:
        filename_parts.append(formatted_date)

    if title:
        filename_parts.append(sanitize_filename(title))

    filename_parts.append(f"[{video_id}]")
    filename = " - ".join(filename_parts) + get_default_video_format()

    return filename

# keep
def get_filename_for_url_source(m3u8_source, title, stream_date):
    streamer = parse_streamer_from_m3u8_link(m3u8_source)
    vod_id = parse_video_id_from_m3u8_link(m3u8_source)
    formatted_date = format_date(stream_date) if stream_date else None

    filename_parts = [streamer]

    if formatted_date:
        filename_parts.append(formatted_date)

    if title:
        filename_parts.append(sanitize_filename(title))

    filename_parts.append(f"[{vod_id}]")
    filename = " - ".join(filename_parts) + get_default_video_format()

    return filename

# keep
def fetch_twitch_data(vod_id, retries=3, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            res = requests.post(
                "https://gql.twitch.tv/gql",
                json={
                    "query": f'query {{ video(id: "{vod_id}") {{ title, broadcastType, createdAt, seekPreviewsURL, owner {{ login }} }} }}'
                },
                headers={
                    "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass

        attempt += 1
        sleep(delay)

    return None

# keep
def twitch_recover(link=None):
    # get it from python vod.py <url> argv
    url = sys.argv[1]
    pattern = r"twitch\.tv/(?:[^\/]+\/)?(\d+)"
    match = re.search(pattern, url)
    vod_id = match.group(1)
    data = fetch_twitch_data(vod_id)
    vod_data = data["data"]["video"]

    current_url = urlparse(vod_data["seekPreviewsURL"])

    domain = current_url.netloc
    paths = current_url.path.split("/")
    vod_special_id = paths[paths.index([i for i in paths if "storyboards" in i][0]) - 1]

    url = f"https://{domain}/{vod_special_id}/chunked/index-dvr.m3u8"
        
    print(f"\n\033[92m\u2713 before qualities: {url}\033[0m")

    sys.exit()

if __name__ == "__main__":
    try:
        twitch_recover()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print("An error occurred:", e)




