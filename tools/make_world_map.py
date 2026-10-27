#!/usr/bin/env python3
"""產生 events.html 用的演出地圖 images/world-map.svg。

有新的演出國家/城市時，改下面的 COUNTRIES / CITIES 再跑一次：
  python3 tools/make_world_map.py
國界資料：world-atlas@2.0.2 countries-50m.json（Natural Earth，公有領域），
第一次跑會自動下載到 tools/countries-50m.json。
"""
import json
import math
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOPO = os.path.join(HERE, "countries-50m.json")
OUT = os.path.join(HERE, "..", "images", "world-map.svg")
TOPO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json"

# world-atlas 裡的國名
COUNTRIES = [
    "Taiwan", "United States of America", "Canada", "Mexico", "Ecuador", "Brazil",
    "Argentina", "United Kingdom", "Ireland", "France", "Germany", "Italy", "Austria",
    "Croatia", "Czechia", "Finland", "Cyprus", "South Korea", "Japan", "Hong Kong", "Malaysia",
    "Australia",
]

# (名稱, 緯度, 經度)
CITIES = [
    ("Taipei", 25.033, 121.565), ("Taichung", 24.148, 120.674), ("Kaohsiung", 22.627, 120.301), ("New York", 40.713, -74.006), ("Boston", 42.360, -71.059),
    ("West Lafayette", 40.426, -86.908), ("Madison", 43.073, -89.401),
    ("Carbondale", 37.727, -89.217),
    ("Calgary", 51.045, -114.072), ("Mexico City", 19.433, -99.133),
    ("Quito", -0.180, -78.468), ("Guayaquil", -2.170, -79.922), ("Manta", -0.967, -80.709),
    ("Paris", 48.857, 2.352), ("Lyon", 45.764, 4.836), ("Grenoble", 45.188, 5.725),
    ("Milan", 45.464, 9.190), ("Venice", 45.441, 12.316), ("Foggia", 41.462, 15.544),
    ("Minturno", 41.263, 13.747), ("Linz", 48.306, 14.286), ("Hamburg", 53.551, 9.994),
    ("Cologne", 50.938, 6.960), ("Lüneburg", 53.249, 10.414), ("Helsinki", 60.170, 24.938),
    ("Limassol", 34.707, 33.022), ("Prague", 50.088, 14.420), ("Seoul", 37.567, 126.978), ("Tokyo", 35.676, 139.650),
    ("Hong Kong", 22.319, 114.169), ("Kuala Lumpur", 3.139, 101.687), ("Sydney", -33.869, 151.209),
    ("Melbourne", -37.814, 144.963), ("Brisbane", -27.470, 153.026),
]

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
        p = (round(x * 2) / 2, round(y * 2) / 2)  # 0.5px 精度，檔案才不會太大
        if last is None or abs(p[0] - last[0]) + abs(p[1] - last[1]) >= 1.0:
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

    land, visited = [], []
    for g in geoms:
        if g["properties"]["name"] == "Antarctica":
            continue
        hit = g["properties"]["name"] in COUNTRIES
        d = geom_path(g, arcs, keep_small=hit)
        if d:
            (visited if hit else land).append(d)

    dots = []
    for name, lat, lon in CITIES:
        x, y = proj(lon, lat)
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6"><title>{name}</title></circle>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Map of countries and cities where Zoe Lin's music has been presented">
<path fill="{LAND}" stroke="{LAND_STROKE}" stroke-width="0.4" d="{''.join(land)}"/>
<path fill="{VISITED}" stroke="{LAND_STROKE}" stroke-width="0.4" d="{''.join(visited)}"/>
<g fill="{DOT}" stroke="{DOT_STROKE}" stroke-width="1">{''.join(dots)}</g>
</svg>
'''
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"{OUT}: {len(COUNTRIES)} countries, {len(CITIES)} cities, {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
