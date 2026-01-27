import requests
import re
import urllib3
import random
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🌐 Siteyi çekerken BOT gibi görünmemek için normal tarayıcı UA
BROWSER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

# 📺 IPTV oynatıcıların kullanacağı TV UA
TV_USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 9; SHIELD Android TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.5) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/3.0 TV Safari/537.36",
    "Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.36 (KHTML, like Gecko) Large Screen Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; MiTV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

BIRAZSPOR_URL = "https://raw.githubusercontent.com/smtv62/birazspor/refs/heads/main/liste.m3u"
NEONSPOR_URL = "https://raw.githubusercontent.com/primatzeka/kurbaga/main/NeonSpor/NeonSpor.m3u"

session = requests.Session()
session.verify = False


def get_browser_headers(referer=None):
    headers = {
        "User-Agent": random.choice(BROWSER_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def browser_get(url, referer=None, timeout=10):
    return session.get(
        url,
        headers=get_browser_headers(referer),
        timeout=timeout,
        allow_redirects=True
    )


def tv_user_agent():
    return random.choice(TV_USER_AGENTS)


def find_active_site():
    print("Sistem taranıyor, TRGoals domaini aranıyor...")
    for i in range(1495, 1601):
        url = f"https://trgoals{i}.xyz"
        try:
            r = browser_get(url, referer="https://www.google.com/", timeout=3)
            print(f"Denendi: {url} | Kod: {r.status_code} | Boyut: {len(r.text)}")
            if r.status_code == 200 and "channel-item" in r.text:
                final_url = r.url.rstrip('/')
                print(f"[+] Aktif TRGoals domaini: {final_url}")
                return final_url
        except Exception as e:
            print(f"Hata: {url} -> {e}")
    return None


def get_channel_data(active_url):
    channel_map = {}
    base_url_found = None

    try:
        r = browser_get(active_url, referer="https://www.google.com/")
        soup = BeautifulSoup(r.text, "html.parser")

        items = soup.select("a.channel-item")
        for item in items:
            href = item.get("href", "")
            name_div = item.select_one("div.channel-name")
            cid = re.search(r"id=([a-zA-Z0-9_]+)", href)
            if cid and name_div:
                channel_map[cid.group(1)] = name_div.get_text().strip()

        scripts = soup.find_all("script", src=True)
        potential_sources = [f"{active_url}/channel.html?id=yayin1", active_url]

        for s in scripts:
            script_url = s['src']
            if not script_url.startswith('http'):
                script_url = f"{active_url}/{script_url.lstrip('/')}"
            potential_sources.append(script_url)

        for source in potential_sources:
            try:
                res = browser_get(source, referer=active_url, timeout=5)
                matches = re.findall(r'https?://[a-zA-Z0-9.-]+\.sbs/', res.text)
                if matches:
                    base_url_found = matches[0]
                    break
            except:
                continue

    except Exception as e:
        print(f"[-] TRGoals Hatası: {e}")

    return channel_map, base_url_found


def fetch_external_m3u(url, group_name):
    print(f"{group_name} listesi çekiliyor...")
    lines = []
    try:
        r = browser_get(url)
        if r.status_code == 200:
            content = r.text.splitlines()
            for i in range(len(content)):
                line = content[i].strip()
                if line.startswith("#EXTINF"):
                    line = re.sub(r'group-title="[^"]*"', '', line)
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group_name}"')
                    lines.append(line)

                    next_idx = i + 1
                    while next_idx < len(content) and not content[next_idx].startswith("#EXTINF"):
                        if content[next_idx].strip():
                            lines.append(content[next_idx].strip())
                        next_idx += 1
        return lines
    except Exception as e:
        print(f"[-] {group_name} listesi alınamadı: {e}")
        return []


def create_m3u():
    m3u = ["#EXTM3U"]

    biraz_lines = fetch_external_m3u(BIRAZSPOR_URL, "Birazspor")
    if biraz_lines:
        m3u.extend(biraz_lines)
        print("[+] Birazspor eklendi.")

    active_site = find_active_site()
    if active_site:
        channels, base_url = get_channel_data(active_site)
        if base_url:
            for cid, name in channels.items():
                m3u.append(f'#EXTINF:-1 group-title="TRGoals",{name}')
                m3u.append(f'#EXTVLCOPT:http-user-agent={tv_user_agent()}')
                m3u.append(f'#EXTVLCOPT:http-referrer={active_site}/')
                m3u.append(f'#EXTVLCOPT:http-reconnect=true')
                m3u.append(f'#EXTVLCOPT:network-caching=1000')
                m3u.append(f"{base_url}{cid}.m3u8")
            print("[+] TRGoals eklendi.")
        else:
            print("[-] Base stream adresi bulunamadı.")
    else:
        print("[-] Aktif TRGoals domaini bulunamadı.")

    neon_lines = fetch_external_m3u(NEONSPOR_URL, "NeonSpor")
    if neon_lines:
        m3u.extend(neon_lines)
        print("[+] NeonSpor eklendi.")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("\n--- İŞLEM TAMAM ---")
    print("GitHub uyumlu + TV uyumlu liste hazır 🚀")


if __name__ == "__main__":
    create_m3u()
