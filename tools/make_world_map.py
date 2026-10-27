#!/usr/bin/env python3
"""產生 events.html 用的演出地圖 images/world-map.svg。

有新的演出國家/城市時，改下面的 COUNTRIES / CITIES 再跑一次：
  python3 tools/make_world_map.py
國界資料：world-atlas@2.0.2 countries-50m.json（Natural Earth，公有領域），
第一次跑會自動下載到 tools/countries-50m.json。

城市點的活動清單由 js/world-map.js 在網頁上直接比對 events.html 卡片的地點產生
（卡片英文地點裡有城市英文名就算），所以加活動卡片不用重跑這支。
活動頁沒有卡片、只在履歷裡的早年演出寫在 EXTRA_EVENTS。
"""
import html
import json
import math
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOPO = os.path.join(HERE, "countries-50m.json")
OUT = os.path.join(HERE, "..", "images", "world-map.svg")
TOPO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json"

# world-atlas 國名 -> (顯示英文, 中文)
COUNTRIES = {
    "Taiwan": ("Taiwan", "台灣"),
    "United States of America": ("USA", "美國"),
    "Canada": ("Canada", "加拿大"),
    "Mexico": ("Mexico", "墨西哥"),
    "Ecuador": ("Ecuador", "厄瓜多"),
    "Brazil": ("Brazil", "巴西"),
    "Argentina": ("Argentina", "阿根廷"),
    "United Kingdom": ("United Kingdom", "英國"),
    "Ireland": ("Ireland", "愛爾蘭"),
    "France": ("France", "法國"),
    "Germany": ("Germany", "德國"),
    "Italy": ("Italy", "義大利"),
    "Austria": ("Austria", "奧地利"),
    "Croatia": ("Croatia", "克羅埃西亞"),
    "Czechia": ("Czechia", "捷克"),
    "Finland": ("Finland", "芬蘭"),
    "Cyprus": ("Cyprus", "賽普勒斯"),
    "South Korea": ("South Korea", "韓國"),
    "Japan": ("Japan", "日本"),
    "Hong Kong": ("Hong Kong", "香港"),
    "Malaysia": ("Malaysia", "馬來西亞"),
    "Australia": ("Australia", "澳洲"),
}

# (英文名＝比對卡片地點用, 中文名, 緯度, 經度, 國家)
CITIES = [
    ("Taipei", "台北", 25.033, 121.565, "Taiwan"),
    ("Taoyuan", "桃園", 24.994, 121.301, "Taiwan"),
    ("Hsinchu", "新竹", 24.794, 120.993, "Taiwan"),
    ("Taichung", "台中", 24.148, 120.674, "Taiwan"),
    ("Kaohsiung", "高雄", 22.627, 120.301, "Taiwan"),
    ("New York", "紐約", 40.713, -74.006, "United States of America"),
    ("Boston", "波士頓", 42.360, -71.059, "United States of America"),
    ("West Lafayette", "西拉法葉", 40.426, -86.908, "United States of America"),
    ("Indianapolis", "印第安納波利斯", 39.768, -86.158, "United States of America"),
    ("Madison", "麥迪遜", 43.073, -89.401, "United States of America"),
    ("Carbondale", "卡本代爾", 37.727, -89.217, "United States of America"),
    ("Calgary", "卡加利", 51.045, -114.072, "Canada"),
    ("Mexico City", "墨西哥市", 19.433, -99.133, "Mexico"),
    ("Quito", "基多", -0.180, -78.468, "Ecuador"),
    ("Guayaquil", "瓜亞基爾", -2.170, -79.922, "Ecuador"),
    ("Manta", "曼塔", -0.967, -80.709, "Ecuador"),
    ("Curitiba", "庫里提巴", -25.429, -49.271, "Brazil"),
    ("Buenos Aires", "布宜諾斯艾利斯", -34.604, -58.382, "Argentina"),
    ("London", "倫敦", 51.507, -0.128, "United Kingdom"),
    ("Cheltenham", "切爾滕納姆", 51.900, -2.078, "United Kingdom"),
    ("Stoke-on-Trent", "特倫特河畔斯托克", 53.003, -2.180, "United Kingdom"),
    ("Limerick", "利默里克", 52.668, -8.630, "Ireland"),
    ("Paris", "巴黎", 48.857, 2.352, "France"),
    ("Lyon", "里昂", 45.764, 4.836, "France"),
    ("Grenoble", "格勒諾勃", 45.188, 5.725, "France"),
    ("Hamburg", "漢堡", 53.551, 9.994, "Germany"),
    ("Lüneburg", "呂訥堡", 53.249, 10.414, "Germany"),
    ("Cologne", "科隆", 50.938, 6.960, "Germany"),
    ("Milan", "米蘭", 45.464, 9.190, "Italy"),
    ("Venice", "威尼斯", 45.441, 12.316, "Italy"),
    ("Minturno", "明圖爾諾", 41.263, 13.747, "Italy"),
    ("Foggia", "福賈", 41.462, 15.544, "Italy"),
    ("Linz", "林茲", 48.306, 14.286, "Austria"),
    ("Prague", "布拉格", 50.088, 14.420, "Czechia"),
    ("Zagreb", "札格瑞布", 45.815, 15.982, "Croatia"),
    ("Helsinki", "赫爾辛基", 60.170, 24.938, "Finland"),
    ("Limassol", "利馬索", 34.707, 33.022, "Cyprus"),
    ("Seoul", "首爾", 37.567, 126.978, "South Korea"),
    ("Bucheon", "富川", 37.503, 126.766, "South Korea"),
    ("Tokyo", "東京", 35.676, 139.650, "Japan"),
    ("Hong Kong", "香港", 22.319, 114.169, "Hong Kong"),
    ("Kuala Lumpur", "吉隆坡", 3.139, 101.687, "Malaysia"),
    ("Sydney", "雪梨", -33.869, 151.209, "Australia"),
    ("Melbourne", "墨爾本", -37.814, 144.963, "Australia"),
    ("Brisbane", "布里斯本", -27.470, 153.026, "Australia"),
]

# 履歷裡有、活動頁沒有卡片的演出：城市 -> [(英文, 中文)]
EXTRA_EVENTS = {
    "Madison": [("2004–2008 · Premieres at UW–Madison (Morphy & Mills Halls)",
                 "2004–2008 · 威斯康辛大學麥迪遜分校多部作品首演（Morphy、Mills 音樂廳）")],
    "Kuala Lumpur": [("Aug 5, 2008 · Reminisce of the Three Kingdoms, British Council",
                      "2008年8月5日 · 《赤壁懷古》，British Council")],
    "Prague": [("Jul 27, 2010 · Reminisce of the Three Kingdoms, CASMI, Dvořák Museum",
                "2010年7月27日 · 《赤壁懷古》，CASMI 國際作曲音樂營，德弗札克博物館")],
    "Taichung": [("Sep 2022 · Premiere of OWt's World", "2022年9月 · 《OWt's World》首演")],
}

LAND = "#e3edf6"
LAND_STROKE = "#ffffff"
VISITED = "#2f6fad"
DOT = "#f08a3c"
DOT_STROKE = "#ffffff"

W = 1000
A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2


def equal_earth(lon, lat):
    lam, phi = math.radians(max(-200, min(200, lon))), math.radians(lat)
    t = math.asin(M * math.sin(phi))
    t2, t6 = t * t, t ** 6
    x = lam * math.cos(t) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, y


XMAX = equal_earth(180, 0)[0]
YTOP = equal_earth(0, 84)[1]
YBOT = equal_earth(0, -58)[1]  # 裁掉南極洲
SCALE = W / (2 * XMAX)
H = round((YTOP - YBOT) * SCALE)


def proj(lon, lat):
    x, y = equal_earth(lon, lat)
    return (x + XMAX) * SCALE, (YTOP - y) * SCALE


def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def ring_coords(ring, arcs):
    pts = []
    for i in ring:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a if not pts else a[1:])
    return pts


def unwrap(pts):
    # 跨換日線的國界（俄羅斯、斐濟）經度會從 180 跳到 -180，改成連續的，超出畫面的部分由 viewBox 裁掉
    out, shift, prev = [], 0, None
    for lon, lat in pts:
        if prev is not None and abs(lon + shift - prev) > 180:
            shift += 360 if prev > lon + shift else -360
        prev = lon + shift
        out.append((prev, lat))
    return out


def ring_path(pts, keep_small=False):
    out, last = [], None
    for lon, lat in unwrap(pts):
        if lat < -60:
            continue
        x, y = proj(lon, lat)
        # 一般國家 0.5px 精度、點距 1px，檔案才不會太大；演出過的國家網頁上會放大看，留細一點
        q, step = (10, 0.3) if keep_small else (2, 1.0)
        p = (round(x * q) / q, round(y * q) / q)
        if last is None or abs(p[0] - last[0]) + abs(p[1] - last[1]) >= step:
            out.append(p)
            last = p
    if len(out) < 3:
        return ""
    area = abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(out, out[1:] + out[:1]))) / 2
    if area < 1.5 and not keep_small:  # 太小的島嶼畫不出來，直接略過
        return ""
    return "M" + "L".join(f"{x:g},{y:g}" for x, y in out) + "Z"


def geom_path(g, arcs, keep_small=False):
    if g["type"] == "Polygon":
        polys = [g["arcs"]]
    elif g["type"] == "MultiPolygon":
        polys = g["arcs"]
    else:
        return ""
    return "".join(ring_path(ring_coords(r, arcs), keep_small) for poly in polys for r in poly)


def attr(s):
    return html.escape(s, quote=True)


def main():
    if not os.path.exists(TOPO):
        urllib.request.urlretrieve(TOPO_URL, TOPO)
    topo = json.load(open(TOPO))
    arcs = decode_arcs(topo)
    geoms = topo["objects"]["countries"]["geometries"]
    names = {g["properties"]["name"] for g in geoms}
    missing = [c for c in COUNTRIES if c not in names]
    if missing:
        raise SystemExit(f"找不到國名：{missing}")
    bad = [c[0] for c in CITIES if c[4] not in COUNTRIES] + [c for c in EXTRA_EVENTS if c not in {x[0] for x in CITIES}]
    if bad:
        raise SystemExit(f"城市資料對不上：{bad}")

    land, visited = [], []
    for g in geoms:
        name = g["properties"]["name"]
        if name == "Antarctica":
            continue
        hit = name in COUNTRIES
        d = geom_path(g, arcs, keep_small=hit)
        if not d:
            continue
        if hit:
            en, zh = COUNTRIES[name]
            visited.append(f'<path class="country" data-en="{attr(en)}" data-zh="{attr(zh)}" d="{d}"/>')
        else:
            land.append(d)

    dots = []
    for en, zh, lat, lon, country in CITIES:
        x, y = proj(lon, lat)
        cen, czh = COUNTRIES[country]
        extra = EXTRA_EVENTS.get(en)
        extra_attr = f' data-extra="{attr(json.dumps(extra, ensure_ascii=False))}"' if extra else ""
        dots.append(f'<circle class="city" cx="{x:.1f}" cy="{y:.1f}" r="4.6" data-en="{attr(en)}" data-zh="{attr(zh)}" '
                    f'data-country-en="{attr(cen)}" data-country-zh="{attr(czh)}"{extra_attr}/>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Map of countries and cities where Zoe Lin's music has been presented">
<path class="land" fill="{LAND}" stroke="{LAND_STROKE}" stroke-width="0.4" d="{''.join(land)}"/>
<g class="countries" fill="{VISITED}" stroke="{LAND_STROKE}" stroke-width="0.4">{''.join(visited)}</g>
<g class="cities" fill="{DOT}" stroke="{DOT_STROKE}" stroke-width="1">{''.join(dots)}</g>
</svg>
'''
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"{OUT}: {len(COUNTRIES)} countries, {len(CITIES)} cities, {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
