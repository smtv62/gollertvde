import requests
import re
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

BIRAZSPOR_URL = "https://raw.githubusercontent.com/smtv62/birazspor/refs/heads/main/liste.m3u"
NEONSPOR_URL = "https://raw.githubusercontent.com/primatzeka/kurbaga/main/NeonSpor/NeonSpor.m3u"


# Kanal adından tvg-id üret
def generate_tvg_id(name):
    name = name.lower()
    name = name.replace(" ", "_")
    name = re.sub(r'[^a-z0-9_]', '', name)
    return name


# M3U satırı oluştur
def build_extinf(name, logo="", language="Turkish", country="TR"):
    tvg_id = generate_tvg_id(name)
    return f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" tvg-language="{language}" tvg-country="{country}" tvg-logo="{logo}",{name}'


def find_active_site():
    print("TRGoals domain aranıyor...")
    for i in range(1495, 1601):
        url = f"https://trgoals{i}.xyz"
        try:
            r = requests.get(url, headers=HEADERS, timeout=3, verify=False)
            if r.status_code == 200 and "channel-item" in r.text:
                final_url = r.url.rstrip('/')
                print(f"Aktif domain: {final_url}")
                return final_url
        except:
            continue
    return None


def get_channel_data(active_url):
    channel_map = {}
    base_url_found = None

    try:
        r = requests.get(active_url, headers=HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")

        items = soup.select("a.channel-item")
        for item in items:
            href = item.get("href", "")
            name_div = item.select_one("div.channel-name")
            cid = re.search(r"id=([a-zA-Z0-9_]+)", href)

            if cid and name_div:
                channel_map[cid.group(1)] = name_div.get_text().strip()

        # Stream base url bul
        scripts = soup.find_all("script", src=True)
        potential_sources = [f"{active_url}/channel.html?id=yayin1", active_url]

        for s in scripts:
            script_url = s['src']
            if not script_url.startswith('http'):
                script_url = f"{active_url}/{script_url.lstrip('/')}"
            potential_sources.append(script_url)

        for source in potential_sources:
            try:
                res = requests.get(source, headers=HEADERS, timeout=5, verify=False)
                matches = re.findall(r'https?://[a-zA-Z0-9.-]+\.sbs/', res.text)
                if matches:
                    base_url_found = matches[0]
                    break
            except:
                continue

    except Exception as e:
        print("TRGoals hata:", e)

    return channel_map, base_url_found


def fetch_external_m3u(url):
    print(f"Liste çekiliyor: {url}")
    channels = []

    try:
        r = requests.get(url, timeout=10, verify=False)
        if r.status_code == 200:
            lines = r.text.splitlines()

            for i in range(len(lines)):
                if lines[i].startswith("#EXTINF"):
                    name = lines[i].split(",")[-1].strip()

                    # URL bul
                    j = i + 1
                    while j < len(lines) and lines[j].startswith("#"):
                        j += 1

                    if j < len(lines):
                        stream_url = lines[j].strip()
                        channels.append((name, stream_url))

    except Exception as e:
        print("Liste alınamadı:", e)

    return channels


def create_m3u():
    m3u = ["#EXTM3U"]

    # 1. Birazspor
    biraz = fetch_external_m3u(BIRAZSPOR_URL)
    for name, url in biraz:
        m3u.append(build_extinf(name))
        m3u.append(url)

    print("Birazspor eklendi")

    # 2. TRGoals
    active_site = find_active_site()
    if active_site:
        channels, base_url = get_channel_data(active_site)
        if base_url:
            for cid, name in channels.items():
                stream = f"{base_url}{cid}.m3u8"
                m3u.append(build_extinf(name))
                m3u.append(stream)

    print("TRGoals eklendi")

    # 3. NeonSpor
    neon = fetch_external_m3u(NEONSPOR_URL)
    for name, url in neon:
        m3u.append(build_extinf(name))
        m3u.append(url)

    print("NeonSpor eklendi")

    # Dosya yaz
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("\n--- TAMAMLANDI ---")
    print("Kategori yok, referrer yok, user-agent yok, temiz format.")


if __name__ == "__main__":
    create_m3u()
