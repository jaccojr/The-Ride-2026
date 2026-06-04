import requests, json, time, os
from datetime import datetime, timezone

POINTS = [
    {"stage":1,"isoDate":"2026-06-07","point":0,"label":"Start",      "lat":44.2371,"lon":5.1497, "hour":8},
    {"stage":1,"isoDate":"2026-06-07","point":1,"label":"Halverwege", "lat":44.1851,"lon":5.4585, "hour":12},
    {"stage":1,"isoDate":"2026-06-07","point":2,"label":"Finish",     "lat":44.5195,"lon":5.8013, "hour":16},
    {"stage":2,"isoDate":"2026-06-08","point":0,"label":"Start",      "lat":44.5201,"lon":5.8037, "hour":8},
    {"stage":2,"isoDate":"2026-06-08","point":1,"label":"Halverwege", "lat":44.9684,"lon":5.9613, "hour":12},
    {"stage":2,"isoDate":"2026-06-08","point":2,"label":"Finish",     "lat":45.1146,"lon":6.0081, "hour":16},
    {"stage":3,"isoDate":"2026-06-09","point":0,"label":"Start",      "lat":45.1145,"lon":6.0077, "hour":8},
    {"stage":3,"isoDate":"2026-06-09","point":1,"label":"Halverwege", "lat":45.4810,"lon":6.2625, "hour":12},
    {"stage":3,"isoDate":"2026-06-09","point":2,"label":"Finish",     "lat":45.8121,"lon":5.8483, "hour":16},
    {"stage":4,"isoDate":"2026-06-10","point":0,"label":"Start",      "lat":45.8129,"lon":5.8468, "hour":8},
    {"stage":4,"isoDate":"2026-06-10","point":1,"label":"Halverwege", "lat":46.4784,"lon":6.0668, "hour":12},
    {"stage":4,"isoDate":"2026-06-10","point":2,"label":"Finish",     "lat":47.1007,"lon":6.1603, "hour":16},
    {"stage":5,"isoDate":"2026-06-11","point":0,"label":"Start",      "lat":47.1012,"lon":6.1600, "hour":8},
    {"stage":5,"isoDate":"2026-06-11","point":1,"label":"Halverwege", "lat":47.6486,"lon":6.5445, "hour":12},
    {"stage":5,"isoDate":"2026-06-11","point":2,"label":"Finish",     "lat":48.0782,"lon":6.9426, "hour":16},
    {"stage":6,"isoDate":"2026-06-12","point":0,"label":"Start",      "lat":48.0782,"lon":6.9426, "hour":8},
    {"stage":6,"isoDate":"2026-06-12","point":1,"label":"Halverwege", "lat":48.6310,"lon":6.6460, "hour":12},
    {"stage":6,"isoDate":"2026-06-12","point":2,"label":"Finish",     "lat":49.0404,"lon":6.0591, "hour":16},
    {"stage":7,"isoDate":"2026-06-13","point":0,"label":"Start",      "lat":49.0404,"lon":6.0592, "hour":8},
    {"stage":7,"isoDate":"2026-06-13","point":1,"label":"Halverwege", "lat":49.5777,"lon":5.6686, "hour":12},
    {"stage":7,"isoDate":"2026-06-13","point":2,"label":"Finish",     "lat":50.1770,"lon":5.5989, "hour":16},
    {"stage":8,"isoDate":"2026-06-14","point":0,"label":"Start",      "lat":50.1770,"lon":5.5988, "hour":8},
    {"stage":8,"isoDate":"2026-06-14","point":1,"label":"Halverwege", "lat":50.5973,"lon":5.9310, "hour":12},
    {"stage":8,"isoDate":"2026-06-14","point":2,"label":"Finish",     "lat":50.8660,"lon":5.8215, "hour":16},
]

def fetch_open_meteo(lat, lon, iso_date, hour, retries=3):
    url = (f"https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}"
           f"&hourly=temperature_2m,weathercode,precipitation_probability,windspeed_10m,winddirection_10m"
           f"&timezone=Europe%2FParis&forecast_days=16")
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()
            if data.get('error'):
                raise Exception(data.get('reason', 'API error'))
            target = f"{iso_date}T{str(hour).zfill(2)}:00"
            idx = data['hourly']['time'].index(target)
            return {
                "temp": round(data['hourly']['temperature_2m'][idx]),
                "code": data['hourly']['weathercode'][idx],
                "rain": round(data['hourly']['precipitation_probability'][idx]),
                "wind": round(data['hourly']['windspeed_10m'][idx]),
                "windDeg": round(data['hourly']['winddirection_10m'][idx]),
                "src": "Open-Meteo"
            }
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                print(f"  Timeout attempt {attempt+1}/{retries}, retrying...")
                time.sleep(3)
            else:
                raise
        except Exception:
            raise

def fetch_wttr(lat, lon, iso_date, hour, retries=2):
    url = f"https://wttr.in/{lat},{lon}?format=j1"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()
            from datetime import date
            today = date.today()
            stage_date = date.fromisoformat(iso_date)
            day_diff = (stage_date - today).days
            if day_diff < 0 or day_diff > 2 or day_diff >= len(data['weather']):
                return None
            day_data = data['weather'][day_diff]
            slots = [0, 3, 6, 9, 12, 15, 18, 21]
            nearest = min(slots, key=lambda x: abs(x - hour))
            slot_idx = nearest // 3
            h = day_data['hourly'][slot_idx]
            wc = int(h['weatherCode'])
            code = 3
            if wc <= 113: code = 0
            elif wc <= 116: code = 1
            elif wc <= 119: code = 2
            elif wc <= 122: code = 3
            elif wc <= 263: code = 61
            elif wc <= 299: code = 63
            elif wc <= 374: code = 71
            elif wc <= 389: code = 95
            return {
                "temp": round(float(h['tempC'])),
                "code": code,
                "rain": round(float(h['chanceofrain'])),
                "wind": round(float(h['windspeedKmph'])),
                "windDeg": float(h['winddirDegree']),
                "src": "wttr.in"
            }
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise
        except Exception:
            raise

# Load existing weather.json to preserve data for failed points
existing = {}
if os.path.exists('weather.json'):
    try:
        with open('weather.json') as f:
            old = json.load(f)
            existing = old.get('data', {})
        print(f"Loaded existing data: {sum(1 for v in existing.values() if v)} points")
    except Exception as e:
        print(f"Could not load existing weather.json: {e}")

results = dict(existing)  # start with existing data
updated = 0

for p in POINTS:
    key = f"{p['stage']}-{p['point']}"
    wx = None
    # Try Open-Meteo first
    try:
        wx = fetch_open_meteo(p['lat'], p['lon'], p['isoDate'], p['hour'])
        print(f"✓ E{p['stage']} {p['label']}: {wx['temp']}° via Open-Meteo")
    except Exception as e:
        print(f"✗ Open-Meteo E{p['stage']} {p['label']}: {e}")
    # Fallback to wttr.in
    if not wx:
        try:
            wx = fetch_wttr(p['lat'], p['lon'], p['isoDate'], p['hour'])
            if wx:
                print(f"✓ E{p['stage']} {p['label']}: {wx['temp']}° via wttr.in")
            else:
                print(f"✗ wttr.in E{p['stage']} {p['label']}: outside window")
        except Exception as e:
            print(f"✗ wttr.in E{p['stage']} {p['label']}: {e}")

    if wx:
        results[key] = wx
        updated += 1
    elif key in existing and existing[key]:
        print(f"  → Keeping existing data for E{p['stage']} {p['label']}")

    time.sleep(0.5)

output = {
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "data": results
}

with open('weather.json', 'w') as f:
    json.dump(output, f, indent=2)

total = sum(1 for v in results.values() if v)
print(f"\nDone. {updated} updated, {total} / {len(results)} points available.")
