#!/usr/bin/env python3
import os
import struct
import math
from PIL import Image, ImageDraw, ImageFont

WIKI_IDX_PATH = "./sd_out"
OUT_DIR = "./sd_out"
OUT_PATH = os.path.join(OUT_DIR, "atlas.bin")

MAP_W = 440
MAP_H = 240

def load_wiki_titles():
    with open(WIKI_IDX_PATH, "rb") as f:
        b = f.read()
    titles = set()
    for page_start in range(32, 1048608, 4096):
        cnt = int.from_bytes(b[page_start:page_start+2], "little")
        off = page_start + 2
        prev = b""
        for _ in range(cnt):
            plen = b[off]
            slen = b[off+1]
            s = b[off+8:off+8+slen]
            cur = prev[:plen] + s
            prev = cur
            titles.add(cur.decode("utf-8", errors="ignore"))
            off += 8 + slen
    return titles

def pack_utf8(text: str, size: int) -> bytes:
    raw = text.encode("utf-8")
    if len(raw) >= size:
        words = text.rstrip(".").split()
        while words and len((" ".join(words) + ".").encode("utf-8")) >= size:
            words.pop()
        s = (" ".join(words) + ".") if words else ""
        raw = s.encode("utf-8")[:size - 1]
    return raw + b"\x00" * (size - len(raw))

# Projection: lon in [-10.5, 47.5], lat in [29.0, 58.5] -> (440, 240)
LON_MIN, LON_MAX = -10.5, 47.5
LAT_MIN, LAT_MAX = 29.0, 58.5

def ll_to_xy(lon: float, lat: float):
    x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * MAP_W
    y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * MAP_H
    return (int(round(x)), int(round(y)))

def poly_xy(coords):
    return [ll_to_xy(lon, lat) for lon, lat in coords]

# Accurate geographic polygons (lon, lat) for Europe, Mediterranean & Near East
CONTINENTAL_EUROPE = [
    # Iberia
    (-9.2, 38.7), (-9.3, 43.0), (-7.5, 43.7), (-1.8, 43.4),
    # France Atlantic & Channel
    (-1.2, 46.0), (-4.7, 48.4), (-1.6, 48.6), (-1.8, 49.6), (0.1, 49.5), (1.6, 50.9),
    # Low Countries, Jutland, Baltic
    (3.4, 51.4), (4.5, 52.5), (7.0, 53.5), (8.6, 54.0), (8.2, 56.5), (10.5, 57.7),
    (10.2, 55.0), (9.8, 54.4), (12.0, 54.2), (14.2, 54.0), (18.6, 54.4), (20.5, 54.8),
    (21.1, 55.8), (24.0, 57.0), (24.7, 59.0), (30.0, 59.5),
    # Eastern edge (Russia down to North Caucasus)
    (48.0, 59.5), (48.0, 45.0),
    # Sea of Azov & Crimea & North Black Sea
    (39.0, 47.2), (37.5, 47.1), (35.2, 46.2), (36.5, 45.3), (34.4, 44.4),
    (33.5, 44.6), (33.7, 45.5), (32.5, 46.1), (31.9, 46.6), (30.7, 46.4),
    # West Black Sea (Romania, Bulgaria, Thrace)
    (29.7, 45.2), (28.6, 44.2), (27.9, 43.2), (27.5, 42.5), (28.9, 41.2),
    # Aegean North & Greece + Peloponnese
    (26.8, 40.5), (26.0, 40.9), (24.4, 40.8), (23.0, 40.5), (22.6, 39.8),
    (23.2, 39.2), (24.0, 38.2), (23.4, 37.9), (23.0, 37.9),
    (23.5, 37.4), (22.8, 36.5), (22.4, 36.4), (21.6, 36.8), (21.3, 37.7),
    (21.9, 38.3), (20.8, 38.9), (20.0, 39.8), (19.4, 40.5), (19.5, 41.8),
    # Adriatic East (Dalmatia, Istria)
    (18.1, 42.6), (16.4, 43.5), (15.2, 44.1), (14.5, 45.3), (13.6, 45.2), (13.8, 45.6),
    # Venice & Italian Boot!
    (12.3, 45.4), (12.3, 44.5), (12.6, 44.0), (13.6, 43.6), (14.2, 42.5),
    (15.5, 41.9), (16.2, 41.8), (15.9, 41.5), (16.8, 41.1), (18.4, 40.1),
    (18.0, 40.0), (17.2, 40.4), (16.6, 40.0), (17.1, 39.0), (16.5, 38.8),
    (15.7, 37.9), (15.6, 38.2), (16.2, 38.8), (15.8, 39.8), (15.2, 40.0),
    (14.8, 40.6), (14.2, 40.8), (13.0, 41.2), (12.2, 41.7), (11.1, 42.4),
    (10.3, 43.7), (9.8, 44.1), (8.9, 44.4), (8.2, 43.9),
    # French Riviera & Mediterranean Spain
    (7.3, 43.7), (6.6, 43.2), (5.4, 43.3), (3.5, 43.3), (3.1, 42.4),
    (2.2, 41.4), (0.8, 40.7), (-0.3, 39.5), (0.1, 38.7), (-0.7, 37.6),
    (-2.2, 36.7), (-4.4, 36.7), (-5.4, 36.0), (-6.3, 36.5), (-7.0, 37.2), (-8.9, 37.0)
]

ANATOLIA_NEAR_EAST_AFRICA = [
    # Bosphorus & Black Sea South Coast
    (29.1, 41.1), (31.5, 41.3), (32.8, 41.8), (35.1, 42.0), (36.5, 41.3),
    (38.5, 41.0), (41.6, 41.6), (41.0, 43.0), (40.0, 43.5),
    # Caucasus & East edge (Iran / Mesopotamia)
    (48.0, 44.0), (48.0, 29.0),
    # North Africa West edge back up to Morocco
    (-10.5, 29.0), (-10.5, 32.0), (-9.3, 33.0), (-6.8, 34.0), (-5.8, 35.8),
    # Mediterranean Coast of Morocco, Algeria, Tunisia
    (-5.3, 35.9), (-3.0, 35.2), (-0.6, 35.7), (3.0, 36.8), (5.0, 36.8),
    (7.8, 36.9), (9.9, 37.3), (10.3, 36.8), (11.0, 37.0), (10.6, 35.8),
    (10.1, 33.9), (11.5, 33.2),
    # Libya (Tripolitania, Gulf of Sidra, Cyrenaica)
    (13.2, 32.9), (15.2, 32.4), (16.5, 31.2), (19.0, 30.3), (20.1, 32.1),
    (21.9, 32.9), (23.2, 32.6), (25.1, 31.6),
    # Egypt & Nile Delta & Sinai
    (27.2, 31.4), (29.9, 31.2), (31.0, 31.5), (32.3, 31.3), (33.8, 31.2),
    # Levant (Gaza, Tyre, Beirut, Antioch) & Cilicia & Aegean Anatolia
    (34.5, 31.6), (35.1, 33.0), (35.5, 33.9), (35.8, 35.5), (36.1, 36.6),
    (35.5, 36.8), (34.0, 36.3), (32.3, 36.0), (30.7, 36.9), (30.4, 36.2),
    (29.1, 36.5), (27.4, 37.0), (27.1, 38.4), (26.3, 38.3), (26.9, 39.0),
    (26.1, 39.5), (26.2, 40.0), (26.7, 40.4), (27.9, 40.4), (28.9, 40.4),
    (29.4, 40.8)
]

GREAT_BRITAIN = [
    (-5.2, 50.0), (-3.5, 50.3), (-1.9, 50.7), (0.2, 50.8), (1.4, 51.3),
    (0.8, 51.5), (1.7, 52.5), (0.5, 52.9), (0.1, 53.5), (-0.4, 54.2),
    (-1.5, 55.0), (-2.1, 55.8), (-3.2, 56.0), (-1.8, 57.5), (-4.0, 57.8),
    (-3.1, 58.6), (-5.0, 58.6), (-5.8, 57.0), (-5.5, 55.3), (-4.8, 54.7),
    (-3.5, 54.5), (-3.0, 53.4), (-4.5, 53.3), (-4.1, 52.5), (-5.2, 51.8),
    (-3.2, 51.4), (-4.2, 51.1)
]

IRELAND = [
    (-9.8, 51.5), (-6.5, 52.2), (-6.0, 53.3), (-5.5, 54.4), (-6.2, 55.2),
    (-7.5, 55.3), (-8.5, 54.9), (-10.0, 53.9), (-9.9, 52.6)
]

SCANDINAVIA = [
    (5.2, 59.5), (5.0, 58.5), (7.0, 58.0), (8.0, 58.1), (10.5, 59.2),
    (11.2, 58.9), (12.0, 57.7), (12.8, 56.0), (14.2, 55.4), (16.0, 56.2),
    (16.6, 57.5), (18.2, 59.3), (18.5, 59.5)
]

SICILY = [(12.4, 37.8), (15.6, 38.2), (15.2, 36.7), (13.5, 37.2)]
SARDINIA = [(8.2, 41.2), (9.7, 41.2), (9.6, 39.1), (8.4, 38.9)]
CORSICA = [(8.6, 42.9), (9.5, 43.0), (9.4, 41.4), (8.6, 41.6)]
CRETE = [(23.5, 35.5), (26.3, 35.2), (26.2, 34.9), (23.6, 35.2)]
CYPRUS = [(32.3, 35.1), (34.6, 35.6), (34.0, 34.6), (32.4, 34.7)]
MALLORCA = [(2.3, 39.6), (3.4, 39.8), (3.4, 39.3), (2.5, 39.4)]

CASPIAN_SEA = [
    (48.0, 44.5), (46.8, 43.5), (47.5, 42.0), (48.0, 40.5)
]

ALL_LAND_POLYS = [
    CONTINENTAL_EUROPE,
    ANATOLIA_NEAR_EAST_AFRICA,
    GREAT_BRITAIN,
    IRELAND,
    SCANDINAVIA,
    SICILY,
    SARDINIA,
    CORSICA,
    CRETE,
    CYPRUS,
    MALLORCA,
]

RIVERS = [
    # Nile
    [(31.1, 29.0), (31.2, 30.1), (30.4, 31.4)],
    [(31.2, 30.1), (31.8, 31.4)],
    # Euphrates & Tigris
    [(38.5, 38.0), (39.0, 36.0), (41.0, 34.5), (44.4, 32.5), (47.5, 30.5)],
    [(40.5, 37.8), (43.1, 36.3), (44.4, 33.3), (47.5, 30.5)],
    # Danube
    [(8.5, 48.0), (11.5, 48.8), (16.4, 48.2), (19.0, 47.5), (20.4, 44.8), (24.0, 43.8), (28.0, 44.3), (29.7, 45.2)],
    # Rhine
    [(8.5, 47.6), (8.2, 50.0), (6.9, 50.9), (4.5, 52.0)],
    # Rhone
    [(6.1, 46.2), (4.8, 45.7), (4.8, 43.4)],
    # Po
    [(7.7, 45.1), (9.5, 45.1), (12.3, 44.9)],
    # Dnieper
    [(30.5, 50.4), (35.0, 48.4), (32.6, 46.6)],
]

def create_base_land_mask():
    mask = Image.new("1", (MAP_W, MAP_H), 0)
    draw = ImageDraw.Draw(mask)
    for poly in ALL_LAND_POLYS:
        draw.polygon(poly_xy(poly), fill=1)
    return mask

LAND_MASK = create_base_land_mask()

def load_fonts():
    try:
        font_sm = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 8)
        font_md = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 9)
        font_lg = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 10)
    except Exception:
        font_sm = ImageFont.load_default()
        font_md = font_sm
        font_lg = font_sm
    return font_sm, font_md, font_lg

FONT_SM, FONT_MD, FONT_LG = load_fonts()

def boxes_overlap(a, b, pad=2):
    return not (a[2] + pad < b[0] or a[0] - pad > b[2] or a[3] + pad < b[1] or a[1] - pad > b[3])

def find_free_box(cx, cy, tw, th, placed_boxes, centered=False):
    if centered:
        candidates = [
            (cx - tw // 2, cy - th // 2),
            (cx - tw // 2, cy - th - 6),
            (cx - tw // 2, cy + 6),
            (cx - tw - 6, cy - th // 2),
            (cx + 6, cy - th // 2),
            (cx - tw // 2, cy - th - 14),
            (cx - tw // 2, cy + 14),
        ]
    else:
        candidates = [
            (cx + 5, cy - th // 2),
            (cx - tw - 5, cy - th // 2),
            (cx - tw // 2, cy - th - 5),
            (cx - tw // 2, cy + 5),
            (cx + 5, cy - th - 4),
            (cx + 5, cy + 4),
            (cx - tw - 5, cy - th - 4),
            (cx - tw - 5, cy + 4),
            (cx - tw // 2, cy - th - 13),
            (cx - tw // 2, cy + 13),
            (cx + 8, cy - th - 10),
            (cx - tw - 8, cy + 10),
        ]
    best = None
    best_pen = 1e9
    for x0, y0 in candidates:
        x0 = max(5, min(MAP_W - tw - 6, x0))
        y0 = max(18, min(MAP_H - th - 5, y0))
        box = (x0, y0, x0 + tw, y0 + th)
        overlaps = sum(1 for pb in placed_boxes if boxes_overlap(box, pb))
        if overlaps == 0:
            placed_boxes.append(box)
            return x0, y0
        if overlaps < best_pen:
            best_pen = overlaps
            best = (x0, y0, box)
    placed_boxes.append(best[2])
    return best[0], best[1]

def draw_halo_text_smart(draw, cx, cy, text, font, placed_boxes):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x, y = find_free_box(cx, cy, tw, th, placed_boxes, centered=False)
    draw.rectangle([x - 1, y, x + tw + 1, y + th], fill=0)
    draw.text((x, y - 1), text, fill=1, font=font)

def draw_boxed_label_smart(draw, lon, lat, text, font, placed_boxes):
    cx, cy = ll_to_xy(lon, lat)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0] + 4
    th = bbox[3] - bbox[1] + 2
    x0, y0 = find_free_box(cx, cy, tw, th, placed_boxes, centered=True)
    draw.rectangle([x0, y0, x0 + tw, y0 + th], fill=0, outline=1)
    draw.text((x0 + 2, y0), text, fill=1, font=font)

def render_era_map(era_def):
    # In PIL '1' mode: we use 0 = white background, 1 = black ink
    img = Image.new("1", (MAP_W, MAP_H), 0)
    pix = img.load()
    land_pix = LAND_MASK.load()

    # 1. Sea stipple (classic copperplate water texture)
    for y in range(MAP_H):
        for x in range(MAP_W):
            if not land_pix[x, y]:
                if (x % 4 == 0 and y % 4 == 0) or (x % 4 == 2 and y % 4 == 2):
                    pix[x, y] = 1

    draw = ImageDraw.Draw(img)

    # 2. Empire / Polity shaded zones clipped to land!
    for idx, zone in enumerate(era_def.get("zones", [])):
        zmask = Image.new("1", (MAP_W, MAP_H), 0)
        zdraw = ImageDraw.Draw(zmask)
        zdraw.polygon(poly_xy(zone["poly"]), fill=1)
        zpix = zmask.load()
        style = zone.get("style", idx % 3)
        for y in range(MAP_H):
            for x in range(MAP_W):
                if zpix[x, y] and land_pix[x, y]:
                    if style == 0:
                        # Forward diagonal hatch
                        if (x + y) % 4 == 0:
                            pix[x, y] = 1
                    elif style == 1:
                        # Backward diagonal hatch
                        if (x - y) % 4 == 0:
                            pix[x, y] = 1
                    else:
                        # Dotted grid hatch
                        if (x % 3 == 0 and y % 3 == 0):
                            pix[x, y] = 1
        # Draw dashed or solid frontier around the zone on land
        pts = poly_xy(zone["poly"])
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            dist = max(1, int(math.hypot(x1 - x0, y1 - y0)))
            for s in range(0, dist, 2):
                px = int(x0 + (x1 - x0) * s / dist)
                py = int(y0 + (y1 - y0) * s / dist)
                if 2 <= px < MAP_W - 2 and 2 <= py < MAP_H - 2 and land_pix[px, py]:
                    if (s // 3) % 2 == 0:
                        pix[px, py] = 1
                        pix[px + 1, py] = 1

    # 3. Draw major rivers (dotted 1px on land)
    for r in RIVERS:
        rpts = poly_xy(r)
        for i in range(len(rpts) - 1):
            x0, y0 = rpts[i]
            x1, y1 = rpts[i + 1]
            dist = max(1, int(math.hypot(x1 - x0, y1 - y0)))
            for s in range(dist):
                if s % 2 == 0:
                    px = int(x0 + (x1 - x0) * s / dist)
                    py = int(y0 + (y1 - y0) * s / dist)
                    if 0 <= px < MAP_W and 0 <= py < MAP_H and land_pix[px, py]:
                        pix[px, py] = 1

    # 4. Crisp 2px coastlines for all landmasses
    for poly in ALL_LAND_POLYS:
        pts = poly_xy(poly)
        draw.line(pts + [pts[0]], fill=1, width=2)

    # 5. Draw historical frontier lines (e.g. Limes, East-West split, Iron Curtain)
    for fline in era_def.get("frontiers", []):
        fpts = poly_xy(fline)
        draw.line(fpts, fill=1, width=2)

    placed_boxes = [(0, 0, 220, 18), (0, MAP_H - 34, 34, MAP_H)]
    for lon, lat, _ in era_def.get("cities", []) + era_def.get("battles", []):
        mx, my = ll_to_xy(lon, lat)
        placed_boxes.append((mx - 3, my - 3, mx + 3, my + 3))

    # 6. Draw Capital Cities / Key Centers first
    for lon, lat, name in era_def.get("cities", []):
        cx, cy = ll_to_xy(lon, lat)
        draw.rectangle([cx - 3, cy - 3, cx + 3, cy + 3], fill=0, outline=1)
        draw.rectangle([cx - 1, cy - 1, cx + 1, cy + 1], fill=1)
        draw_halo_text_smart(draw, cx, cy, name, FONT_SM, placed_boxes)

    # 7. Draw Battle / Event Markers ('X' crossed swords icon + label)
    for lon, lat, name in era_def.get("battles", []):
        bx, by = ll_to_xy(lon, lat)
        draw.rectangle([bx - 3, by - 3, bx + 3, by + 3], fill=0)
        draw.line([bx - 3, by - 3, bx + 3, by + 3], fill=1, width=1)
        draw.line([bx - 3, by + 3, bx + 3, by - 3], fill=1, width=1)
        draw_halo_text_smart(draw, bx, by, "X " + name, FONT_SM, placed_boxes)

    # 8. Draw Boxed Polity Banner Labels
    for banner in era_def.get("banners", []):
        draw_boxed_label_smart(draw, banner[0], banner[1], banner[2], FONT_SM, placed_boxes)

    # 9. Top-left Era Cartouche Header Box
    cartouche = f" {era_def['year']} | {era_def['map_tag']} "
    bbox = draw.textbbox((0, 0), cartouche, font=FONT_MD)
    cw = bbox[2] - bbox[0] + 6
    ch = bbox[3] - bbox[1] + 4
    draw.rectangle([3, 3, 3 + cw, 3 + ch], fill=0, outline=1)
    draw.rectangle([4, 4, 2 + cw, 2 + ch], outline=1)
    draw.text((6, 4), cartouche, fill=1, font=FONT_MD)

    # 10. Compass Rose in bottom-left corner & Double Outer Frame
    rx, ry = 18, MAP_H - 18
    draw.ellipse([rx - 10, ry - 10, rx + 10, ry + 10], fill=0, outline=1)
    draw.line([rx, ry - 9, rx, ry + 9], fill=1, width=1)
    draw.line([rx - 9, ry, rx + 9, ry], fill=1, width=1)
    draw.polygon([(rx, ry - 9), (rx - 3, ry - 2), (rx + 3, ry - 2)], fill=1)
    draw.rectangle([0, 0, MAP_W - 1, MAP_H - 1], outline=1)
    draw.rectangle([2, 2, MAP_W - 3, MAP_H - 3], outline=1)

    # Convert to 13,200 bytes (stride 55 bytes per row, MSB first, 1 = black ink, 0 = white)
    buf = bytearray(MAP_W * MAP_H // 8)
    for y in range(MAP_H):
        row_off = y * (MAP_W // 8)
        for x in range(MAP_W):
            if pix[x, y]:
                buf[row_off + (x >> 3)] |= (0x80 >> (x & 7))
    return bytes(buf), img

ERAS = [
    # 1. 3000 BC
    {
        "year": "3000 BC",
        "map_tag": "BRONZE AGE DAWN",
        "title": "BRONZE AGE DAWN: SUMER, EGYPT & AEGEAN",
        "subtitle": "Yazının icadı, Sümer şehir devletleri ve Eski Mısır birliği",
        "overview": (
            "MÖ 3000 civarında Bereketli Hilal ve Nil Vadisi'nde insanlık tarihinin ilk kentsel devrimi yaşandı. "
            "Güney Mezopotamya'da Fırat ve Dicle kıyılarındaki Uruk, Ur ve Eridu gibi Sümer şehir devletleri sulama "
            "kanalları, tapınak ekonomisi ve çivi yazısı (cuneiform) ile bürokrasiyi kurdu. Aynı dönemde Narmer (Menes) "
            "Yukarı ve Aşağı Mısır'ı birleştirerek Memphis merkezli ilk hanedanı ve hiyeroglif geleneğini başlattı. "
            "Ege Denizi'nde Kiklad adaları ve Girit'te erken Tunç Çağı deniz ticareti filizlenirken, Anadolu ve Yakın Doğu "
            "bakır ile kalay ticaret yollarının kesişim noktası haline geldi."
        ),
        "powers": [
            ("Sumerian City-States", "Güney Mezopotamya'da Uruk, Ur, Lagaş ve Kiş merkezli ilk yazılı kent uygarlığı.", "Sumer"),
            ("Old Kingdom Egypt", "Yukarı ve Aşağı Nil'in birleşmesiyle kurulan Memphis merkezli firavun devleti.", "Old Kingdom of Egypt"),
            ("Minoan Crete", "Girit adasında Knossos etrafında yükselen erken Ege deniz ticaret kültürü.", "Minoan civilization"),
            ("Fertile Crescent", "Mezopotamya, Levant ve Anadolu'yu birbirine bağlayan tarım ve maden kuşağı.", "Mesopotamia"),
        ],
        "events": [
            ("Invention of Cuneiform", "Uruk tapınak kayıtlarından doğan, kil tabletler üzerine yazılan ilk yazı sistemi.", "Cuneiform"),
            ("Unification of Egypt", "Kral Narmer'in iki tacı birleştirerek Mısır'da hanedanlar çağını başlatması.", "Ancient Egypt"),
            ("Egyptian Hieroglyphs", "Anıtsal taş yazıtlar ve kraliyet mühürlerinde gelişen kutsal Mısır yazısı.", "Egyptian hieroglyphs"),
            ("Early Bronze Metallurgy", "Bakır ve kalay alaşımıyla tunç alet, silah ve deniz ticaret ağlarının doğuşu.", "Bronze Age"),
        ],
        "thinkers": [
            ("Imhotep", "Djoser Basamaklı Piramidi'nin mimarı, hekim ve bilge vezir.", "Imhotep"),
            ("Epic of Gilgamesh", "Uruk kralı Gılgamış'ın ölümsüzlük arayışını anlatan en eski destan geleneği.", "Epic of Gilgamesh"),
            ("Ptahhotep", "Mısır'da devlet yönetimi, tevazu ve adalet üzerine bilgelik öğütlerinin yazarı.", "The Maxims of Ptahhotep"),
            ("Enheduanna", "Ur'da Ay tanrıçası Nanna'nın başrahibesi; tarihte adı bilinen ilk yazar ve şair.", "Enheduanna"),
        ],
        "zones": [
            {"poly": [(38.0, 37.5), (48.0, 37.5), (48.0, 29.5), (40.0, 31.0)], "style": 0},
            {"poly": [(28.0, 32.0), (35.0, 32.0), (35.0, 29.0), (28.0, 29.0)], "style": 1},
            {"poly": [(22.0, 38.5), (28.0, 38.5), (28.0, 34.5), (22.0, 34.5)], "style": 2},
        ],
        "banners": [
            (43.0, 34.5, "SUMER"),
            (31.0, 29.8, "OLD EGYPT"),
            (25.0, 36.2, "AEGEAN"),
        ],
        "cities": [
            (45.6, 31.3, "URUK"),
            (31.2, 29.9, "MEMPHIS"),
            (25.1, 35.3, "KNOSSOS"),
            (35.6, 34.1, "BYBLOS"),
        ],
        "battles": [
            (31.0, 30.8, "NARMER UNIFICATION"),
        ],
    },
    # 2. 450 BC
    {
        "year": "450 BC",
        "map_tag": "CLASSICAL GREECE",
        "title": "CLASSICAL GREECE: ATHENS, SPARTA & PERSIA",
        "subtitle": "Perikles Çağı Atina'sı, Pers İmparatorluğu ve Erken Roma",
        "overview": (
            "MÖ 450'de Doğu Akdeniz, Yunan-Pers Savaşları'nın ardından Atina'nın önderliğindeki Attika-Delos Deniz Birliği "
            "ile Ahameniş Pers İmparatorluğu arasındaki güç dengesiyle şekilleniyordu. Perikles yönetimindeki Atina; "
            "doğrudan demokrasi, felsefe, tragedya ve Akropolis'in inşasıyla altın çağını yaşarken, kara gücü Sparta ve "
            "Peloponnesos Birliği Atina'nın yükselişini kuşkuyla izliyordu. Batıda ise yeni kurulan Roma Cumhuriyeti "
            "On İki Levha Kanunları'nı hazırlıyor, Güney İtalya (Magna Graecia) ve Sicilya'da Siraküza gibi Yunan "
            "kolonileri kültür ve ticarette parlıyordu."
        ),
        "powers": [
            ("Classical Athens", "Attika-Delos Deniz Birliği'ne liderlik eden Perikles dönemi deniz ve kültür gücü.", "Classical Athens"),
            ("Sparta", "Peloponnesos Birliği'nin lideri, disiplinli hoplit ordusuyla ünlü oligarşik kara devleti.", "Sparta"),
            ("Achaemenid Empire", "Anadolu ve Mısır'dan İndus'a uzanan çok uluslu Pers cihan imparatorluğu.", "Achaemenid Empire"),
            ("Early Roman Republic", "Krallığı devirip Senato ve konsül sistemini kuran Orta İtalya cumhuriyeti.", "Roman Republic"),
        ],
        "events": [
            ("Greco-Persian Wars", "Yunan şehir devletlerinin Pers istilasına karşı bağımsızlığını koruduğu savaşlar.", "Greco-Persian Wars"),
            ("Battle of Marathon", "MÖ 490'da Atina hoplitlerinin Pers ordusunu durdurduğu tarihi zafer.", "Battle of Marathon"),
            ("Battle of Salamis", "Themistokles komutasındaki Yunan donanmasının Pers filosunu yendiği deniz savaşı.", "Battle of Salamis"),
            ("Delian League", "Atina'nın Ege adaları ve İyonya kentleriyle kurduğu deniz savunma ve imparatorluk ağı.", "Delian League"),
        ],
        "thinkers": [
            ("Socrates", "Sorgulanmamış hayatın yaşanmaya değmediğini savunan, Batı ahlak felsefesinin kurucusu.", "Socrates"),
            ("Herodotus", "Pers-Yunan savaşlarını araştırarak 'Tarihin Babası' unvanını kazanan Halikarnaslı tarihçi.", "Herodotus"),
            ("Pericles", "Atina demokrasisini ve Akropolis'in görkemli imarını yöneten devlet adamı ve hatip.", "Pericles"),
            ("Aeschylus", "Oresteia üçlemesi ve Persler tragedyasıyla klasik Yunan tiyatrosunu kuran şair.", "Aeschylus"),
        ],
        "zones": [
            {"poly": [(19.5, 41.5), (27.5, 41.5), (27.5, 35.0), (19.5, 35.0)], "style": 0},
            {"poly": [(27.5, 42.0), (48.0, 42.0), (48.0, 29.0), (28.0, 29.0)], "style": 1},
            {"poly": [(11.5, 43.0), (17.5, 41.5), (16.5, 36.5), (12.0, 37.5)], "style": 2},
        ],
        "banners": [
            (23.5, 39.5, "HELLAS"),
            (37.0, 38.5, "PERSIAN EMPIRE"),
            (13.0, 42.2, "ROME"),
        ],
        "cities": [
            (23.7, 38.0, "ATHENS"),
            (22.4, 37.1, "SPARTA"),
            (12.5, 41.9, "ROME"),
            (15.3, 37.1, "SYRACUSE"),
            (28.0, 38.5, "SARDIS"),
        ],
        "battles": [
            (24.0, 38.1, "MARATHON"),
            (23.5, 37.9, "SALAMIS"),
        ],
    },
    # 3. 264 BC
    {
        "year": "264 BC",
        "map_tag": "HELLENISTIC & PUNIC",
        "title": "HELLENISTIC WORLD & FIRST PUNIC WAR",
        "subtitle": "Roma-Kartaca rekabeti ve İskender sonrası Helenistik krallıklar",
        "overview": (
            "MÖ 264 yılı Batı Akdeniz'de kader anıydı: İtalya yarımadasını birleştiren Roma Cumhuriyeti, Sicilya boğazındaki "
            "Messana krizi nedeniyle deniz ticaret imparatorluğu Kartaca ile Birinci Pön Savaşı'na girdi. Doğu Akdeniz'de ise "
            "Büyük İskender'in mirası üzerinde yükselen üç büyük Helenistik güç hüküm sürüyordu: Mısır'da İskenderiye "
            "Kütüphanesi ile bilim merkezi olan Ptolemaios Krallığı, Suriye'den Mezopotamya'ya uzanan Seleukos İmparatorluğu "
            "ve Makedonya Krallığı. Arşimet, Öklid, Zenon ve Epikuros ile bilim ve felsefe altın çağındaydı."
        ),
        "powers": [
            ("Roman Republic", "İtalya yarımadasını hakimiyeti altına alıp Akdeniz'e açılan yükselen cumhuriyet.", "Roman Republic"),
            ("Carthaginian Empire", "Kuzey Afrika, İberya, Sardinya ve Batı Sicilya'ya hükmeden Fenike kökenli deniz gücü.", "Carthage"),
            ("Ptolemaic Kingdom", "İskenderiye merkezli, Mısır ve Doğu Akdeniz kıyılarını yöneten Helenistik krallık.", "Ptolemaic Kingdom"),
            ("Seleucid Empire", "Anadolu, Suriye ve Mezopotamya'dan İran'a uzanan en geniş Helenistik imparatorluk.", "Seleucid Empire"),
        ],
        "events": [
            ("First Punic War", "Roma ve Kartaca arasında Sicilya ve deniz hakimiyeti için başlayan 23 yıllık savaş.", "First Punic War"),
            ("Punic Wars", "Akdeniz'in tek hakiminin kim olacağını belirleyen üç büyük Roma-Kartaca savaşı.", "Punic Wars"),
            ("Hellenistic Period", "Büyük İskender'den sonra Yunan dili ve biliminin Doğu uygarlıklarıyla sentezi.", "Hellenistic period"),
            ("Library of Alexandria", "Antik dünyanın tüm bilgisini papirüs rulolarında toplayan araştırma enstitüsü.", "Library of Alexandria"),
        ],
        "thinkers": [
            ("Archimedes", "Siraküzalı matematikçi, fizikçi ve mühendis; hidrostatik ve kaldıraç yasalarının mucidi.", "Archimedes"),
            ("Euclid", "İskenderiye'de yazdığı 'Elementler' eseriyle geometrinin aksiyomatik temelini kuran bilgin.", "Euclid"),
            ("Zeno of Citium", "Atina'da Stoa Okulu'nu kurarak akıl, doğaya uyum ve içsel dinginlik felsefesini başlatan düşünür.", "Zeno of Citium"),
            ("Epicurus", "Ruhsal dinginlik (ataraksia), dostluk ve doğa felsefesini öğreten Bahçe Okulu'nun kurucusu.", "Epicurus"),
        ],
        "zones": [
            {"poly": [(9.0, 44.5), (18.5, 42.0), (18.5, 38.0), (12.0, 41.0)], "style": 0},
            {"poly": [(-7.0, 38.0), (13.5, 38.5), (13.5, 32.0), (-7.0, 32.0)], "style": 1},
            {"poly": [(26.0, 41.0), (48.0, 41.0), (48.0, 29.0), (26.0, 29.0)], "style": 2},
        ],
        "banners": [
            (13.0, 43.0, "ROMAN REP."),
            (6.0, 35.0, "CARTHAGE"),
            (38.0, 36.5, "SELEUCIDS"),
            (30.5, 30.0, "PTOLEMIES"),
        ],
        "cities": [
            (12.5, 41.9, "ROME"),
            (10.3, 36.8, "CARTHAGE"),
            (29.9, 31.2, "ALEXANDRIA"),
            (36.2, 36.2, "ANTIOCH"),
        ],
        "battles": [
            (15.5, 38.2, "MESSANA"),
            (15.3, 37.1, "SYRACUSE"),
        ],
    },
    # 4. 117 AD
    {
        "year": "117 AD",
        "map_tag": "PAX ROMANA ZENITH",
        "title": "PAX ROMANA: ROMAN EMPIRE AT ITS ZENITH",
        "subtitle": "İmparator Trajan döneminde İskoçya'dan Basra Körfezi'ne Mare Nostrum",
        "overview": (
            "MS 117'de İmparator Trajan'ın Daçya, Arabistan ve Mezopotamya fetihleriyle Roma İmparatorluğu tarihteki en "
            "geniş sınırlarına (yaklaşık 5 milyon km²) ulaştı. Akdeniz tamamen bir Roma iç gölü ('Mare Nostrum') haline "
            "gelmişti. Britanya'dan Mısır'a, İberya'dan Dicle kıylarındaki Ktesifon'a kadar tek bir hukuk, para birimi "
            "ve 80.000 kilometrelik taş döşeli yol ağı işliyordu. Pax Romana (Roma Barışı) sayesinde şehirleşme, ticaret, "
            "mimari (Pantheon, Trajan Forumu) ve Stoacı felsefe imparatorluğun dört bir yanında zirveye çıktı."
        ),
        "powers": [
            ("Roman Empire", "İskoçya sınırından Basra Körfezi'ne uzanan, tüm Akdeniz havzasını birleştiren imparatorluk.", "Roman Empire"),
            ("Parthian Empire", "İran platosu ve doğu ticaret yollarını kontrol eden Roma'nın doğudaki baş rakibi.", "Parthian Empire"),
            ("Province of Dacia", "Trajan tarafından fethedilen, altın madenleriyle ünlü Tuna'nın kuzeyindeki eyalet.", "Dacia"),
            ("Kushan Empire", "İpek Yolu üzerinden Roma ve Çin arasındaki ticareti bağlayan Orta Asya-Hindistan gücü.", "Kushan Empire"),
        ],
        "events": [
            ("Pax Romana", "Augustus'tan Marcus Aurelius'a uzanan iki yüzyıllık iç istikrar, hukuk ve refah dönemi.", "Pax Romana"),
            ("Hadrian's Wall", "Trajan'ın halefi Hadrianus'un Kuzey Britanya sınırını tahkim etmek için kurduğu sur.", "Hadrian's Wall"),
            ("Roman Roads Network", "Lejyonları ve ticareti Roma'ya bağlayan mühendislik harikası taş yollar sistemi.", "Roman roads"),
            ("Pantheon in Rome", "Devasa kubbesiyle Roma beton mühendisliğinin zirvesini simgeleyen anıtsal tapınak.", "Pantheon, Rome"),
        ],
        "thinkers": [
            ("Trajan", "Senato tarafından 'Optimus Princeps' (En İyi Hükümdar) ilan edilen başarılı Roma imparatoru.", "Trajan"),
            ("Tacitus", "Annales ve Historiae eserleriyle imparatorluk siyasetini keskin bir dille inceleyen tarihçi.", "Tacitus"),
            ("Plutarch", "Yunan ve Romalı devlet adamlarını karşılaştırdığı 'Paralel Yaşamlar'ın yazarı filozof.", "Plutarch"),
            ("Epictetus", "Hierapolis doğumlu Stoacı filozof; irade özgürlüğü ve içsel güç öğretisinin ustası.", "Epictetus"),
        ],
        "zones": [
            {"poly": [(-9.5, 55.0), (5.0, 52.0), (18.0, 48.0), (29.0, 47.0), (45.0, 38.0), (47.0, 30.0), (-9.5, 29.5)], "style": 0},
            {"poly": [(44.0, 40.0), (48.0, 40.0), (48.0, 29.5), (45.0, 29.5)], "style": 1},
        ],
        "frontiers": [
            [(4.5, 52.0), (8.5, 49.0), (16.4, 48.2), (21.0, 45.0), (26.0, 47.0), (29.5, 45.2)],
        ],
        "banners": [
            (14.0, 38.0, "IMPERIUM ROMANUM (MARE NOSTRUM)"),
            (44.5, 35.5, "PARTHIA"),
        ],
        "cities": [
            (12.5, 41.9, "ROME"),
            (29.9, 31.2, "ALEXANDRIA"),
            (36.2, 36.2, "ANTIOCH"),
            (-0.1, 51.5, "LONDINIUM"),
            (44.6, 33.1, "CTESIPHON"),
        ],
        "battles": [
            (23.2, 45.6, "SARMIZEGETUSA"),
        ],
    },
    # 5. 565 AD
    {
        "year": "565 AD",
        "map_tag": "JUSTINIAN RECONQUEST",
        "title": "JUSTINIAN'S EMPIRE: BYZANTINE RECONQUEST",
        "subtitle": "Ayasofya, Roma Hukuku (Corpus Juris) ve İtalya'nın geri alınışı",
        "overview": (
            "MS 565'te İmparator I. Justinianus öldüğünde, Doğu Roma (Bizans) İmparatorluğu Batı Akdeniz'i yeniden "
            "fethetmeyi başarmıştı. Komutanlar Belisarius ve Narses; Kuzey Afrika'daki Vandalları, İtalya'daki Ostrogotları "
            "ve Güney İspanya'daki Vizigot kıyılarını geri alarak Roma'yı, Ravenna'yı ve Kartaca'yı Konstantinopolis'e "
            "bağladı. Ayasofya'nın muazzam kubbesi inşa edildi ve tüm modern Avrupa hukukunun temeli olan Corpus Juris "
            "Civilis derlendi. Ancak uzun Gotlar Savaşı ve Justinianus Vebası imparatorluğun kaynaklarını zorladı."
        ),
        "powers": [
            ("Byzantine Empire", "Konstantinopolis merkezli, İtalya ve Kuzey Afrika'yı yeniden birleştiren Doğu Roma.", "Byzantine Empire"),
            ("Sasanian Empire", "Hüsrev Anuşirvan yönetiminde Doğu sınırında Bizans ile rekabet eden İran imparatorluğu.", "Sasanian Empire"),
            ("Kingdom of the Franks", "Merovenj hanedanı altında Galya ve Ren havzasında yükselen Cermen krallığı.", "Francia"),
            ("Ostrogothic Italy", "Ravenna merkezli olup Belisarius ve Narses'in seferleriyle yıkılan İtalya krallığı.", "Ostrogothic Kingdom"),
        ],
        "events": [
            ("Gothic War in Italy", "Bizans'ın İtalya yarımadasını ve Roma'yı Ostrogotlardan geri aldığı 20 yıllık savaş.", "Gothic War (535–554)"),
            ("Corpus Juris Civilis", "Justinianus'un emriyle Tribonianus'un derlediği anıtsal Roma Medeni Hukuku külliyatı.", "Corpus Juris Civilis"),
            ("Building Hagia Sophia", "Anthemios ve İsidoros'un tasarladığı, bin yıl boyunca dünyanın en büyük katedrali.", "Hagia Sophia"),
            ("Plague of Justinian", "541'de Akdeniz limanlarını vuran, nüfusu ve vergi gelirlerini sarsan ilk veba salgını.", "Plague of Justinian"),
        ],
        "thinkers": [
            ("Justinian I", "'Uyumayan İmparator'; Roma İmparatorluğu'nu ihya etmeye adanmış hukukçu ve hükümdar.", "Justinian I"),
            ("Boethius", "'Felsefenin Tesellisi' eseriyle antik felsefeyi Orta Çağ'a aktaran Romalı düşünür.", "Boethius"),
            ("Procopius", "Justinianus'un savaşlarını, yapılarını ve 'Gizli Tarih'ini kaleme alan baş tarihçi.", "Procopius"),
            ("Belisarius", "Kuzey Afrika, Sicilya, Napoli ve Roma'yı fetheden efsanevi Bizans başkomutanı.", "Belisarius"),
        ],
        "zones": [
            {"poly": [(-6.0, 37.5), (18.5, 45.5), (29.5, 45.0), (39.0, 41.0), (36.0, 29.5), (-6.0, 31.0)], "style": 0},
            {"poly": [(39.0, 42.0), (48.0, 42.0), (48.0, 29.0), (39.0, 29.0)], "style": 1},
            {"poly": [(-4.0, 51.0), (11.0, 51.0), (10.0, 43.5), (-2.0, 43.5)], "style": 2},
        ],
        "banners": [
            (23.0, 36.0, "BYZANTINE EMPIRE"),
            (3.0, 47.5, "FRANCIA"),
            (43.5, 35.0, "SASANIANS"),
        ],
        "cities": [
            (28.9, 41.0, "CONSTANTINOPLE"),
            (12.2, 44.4, "RAVENNA"),
            (12.5, 41.9, "ROME"),
            (10.3, 36.8, "CARTHAGE"),
        ],
        "battles": [
            (12.8, 43.2, "TAGINAE"),
        ],
    },
    # 6. 800 AD
    {
        "year": "800 AD",
        "map_tag": "CHARLEMAGNE & ABBASIDS",
        "title": "800 AD: CHARLEMAGNE, BYZANTIUM & ABBASIDS",
        "subtitle": "Şarlman'ın Roma'da taç giyişi ve Bağdat'ta İslam Altın Çağı",
        "overview": (
            "MS 800 yılı Noel gününde Papa III. Leo, Roma'da Frank Kralı Şarlman'a (Charlemagne) 'Romalıların İmparatoru' "
            "tacını giydirerek Batı Avrupa'da siyasi birliği yeniden canlandırdı. Aynı dönemde dünyada üç büyük güç merkezi "
            "vardı: Aachen merkezli Karolenj İmparatorluğu, Konstantinopolis merkezli Bizans İmparatorluğu ve Harun Reşid "
            "yönetiminde Bağdat'ta Beytü'l-Hikme ile bilim ve felsefenin zirvesine çıkan Abbasi Halifeliği. İberya'da ise "
            "Kurtuba merkezli Endülüs Emevileri Avrupa'nın en gelişmiş kentsel kültürünü inşa ediyordu."
        ),
        "powers": [
            ("Carolingian Empire", "Şarlman yönetiminde Fransa, Almanya ve Kuzey İtalya'yı birleştiren Batı imparatorluğu.", "Carolingian Empire"),
            ("Byzantine Empire", "İmparatoriçe İrini döneminde Anadolu, Yunanistan ve Güney İtalya'yı koruyan Doğu Roma.", "Byzantine Empire"),
            ("Abbasid Caliphate", "Bağdat merkezli, Kuzey Afrika'dan Orta Asya'ya uzanan İslam Altın Çağı imparatorluğu.", "Abbasid Caliphate"),
            ("Al-Andalus (Cordoba)", "İber yarımadasında Kurtuba merkezli bilim, mimari ve hoşgörü medeniyeti.", "Al-Andalus"),
        ],
        "events": [
            ("Coronation of Charlemagne", "800 Noel'inde Roma'da Batı İmparatorluğu fikrinin yeniden diriltilmesi.", "Charlemagne"),
            ("Carolingian Renaissance", "Manastır okulları, Karolenj yazı stili ve antik Latince eserlerin kopyalanması hamlesi.", "Carolingian Renaissance"),
            ("Dawn of the Viking Age", "793 Lindisfarne baskınıyla başlayan İskandinav denizcilerinin Avrupa seferleri.", "Viking Age"),
            ("Rise of Papal States", "Orta İtalya'da Papalık dünyevi hakimiyetinin Frank ittifakıyla güçlenmesi.", "Papal States"),
        ],
        "thinkers": [
            ("Alcuin of York", "Şarlman'ın Aachen saray okulunu yöneten, yedi özgür sanat müfredatını kuran bilgin.", "Alcuin"),
            ("Harun al-Rashid", "Binbir Gece Masalları'na konu olan, Bağdat'ı dünya bilim başkenti yapan Abbasi halifesi.", "Harun al-Rashid"),
            ("Al-Khwarizmi", "Cebir (el-Cebr) ve algoritma kavramlarının isim babası olan matematikçi ve astronom.", "Al-Khwarizmi"),
            ("Al-Farabi", "Aristo ve Platon felsefesini İslam dünyasında sentezleyen 'Muallim-i Sani' (İkinci Öğretmen).", "Al-Farabi"),
        ],
        "zones": [
            {"poly": [(-2.0, 53.0), (14.0, 53.0), (15.0, 42.0), (1.0, 42.0)], "style": 0},
            {"poly": [(19.0, 43.0), (36.0, 42.0), (34.0, 36.0), (15.0, 37.5)], "style": 1},
            {"poly": [(10.0, 37.0), (48.0, 38.0), (48.0, 29.0), (-9.0, 29.0), (-9.0, 41.0), (-1.0, 41.0)], "style": 2},
        ],
        "banners": [
            (6.0, 48.5, "CAROLINGIANS"),
            (28.0, 39.5, "BYZANTIUM"),
            (41.0, 33.5, "ABBASIDS"),
            (-4.5, 38.5, "AL-ANDALUS"),
        ],
        "cities": [
            (6.1, 50.8, "AACHEN"),
            (12.5, 41.9, "ROME"),
            (28.9, 41.0, "CONSTANTINOPLE"),
            (44.4, 33.3, "BAGHDAD"),
            (-4.8, 37.9, "CORDOBA"),
        ],
        "battles": [
            (-1.3, 43.0, "RONCEVAUX"),
        ],
    },
    # 7. 1095 AD
    {
        "year": "1095 AD",
        "map_tag": "FIRST CRUSADE EVE",
        "title": "1095 AD: SELJUKS, PAPACY & FIRST CRUSADE",
        "subtitle": "Malazgirt sonrası Anadolu, Clermont Çağrısı ve İtalyan Deniz Cumhuriyetleri",
        "overview": (
            "1095 yılında Akdeniz dünyası köklü bir dönüşümün eşiğindeydi. 1071 Malazgirt Zaferi'nin ardından Selçuklu "
            "Türkleri Anadolu'ya yerleşmiş ve İznik'e (Nicaea) kadar ilerlemişti. Bizans İmparatoru I. Aleksios Komnenos'un "
            "yardım talebi üzerine Papa II. Urbanus, Kasım 1095'te Clermont Konsili'nde Birinci Haçlı Seferi çağrısını "
            "yaptı. Batı'da Kutsal Roma İmparatorluğu ile Papalık arasında Atama Kavgası (Investiture Controversy) "
            "sürerken, Venedik, Ceneviz, Pisa ve Amalfi gibi İtalyan deniz cumhuriyetleri Doğu Akdeniz ticaretini ele geçiriyordu."
        ),
        "powers": [
            ("Seljuk Empire", "İran, Mezopotamya, Suriye ve Anadolu'da hakimiyet kuran büyük Türk-İslam imparatorluğu.", "Seljuk Empire"),
            ("Byzantine Empire", "I. Aleksios Komnenos yönetiminde toparlanma mücadelesi veren Doğu Roma İmparatorluğu.", "Byzantine Empire"),
            ("Holy Roman Empire", "Almanya ve Kuzey İtalya üzerinde hüküm süren, Papalık ile yetki mücadelesindeki imparatorluk.", "Holy Roman Empire"),
            ("Republic of Venice", "Adriyatik ve Doğu Akdeniz'de donanmasıyla ticaret ayrıcalıkları kazanan deniz cumhuriyeti.", "Republic of Venice"),
        ],
        "events": [
            ("First Crusade", "1095 Clermont çağrısıyla başlayan, İznik, Antakya ve Kudüs'e yönelen Haçlı seferi.", "First Crusade"),
            ("Battle of Manzikert", "1071'de Sultan Alparslan'ın Bizans ordusunu yenerek Anadolu'nun kapılarını açtığı zafer.", "Battle of Manzikert"),
            ("Investiture Controversy", "Papa VII. Gregorius ile İmparator IV. Heinrich arasındaki ruhani-dünyevi iktidar çatışması.", "Investiture Controversy"),
            ("Crusading Movement", "Batı Avrupa feodal şövalyelerini ve İtalyan filolarını Doğu Akdeniz'e taşıyan dalga.", "Crusades"),
        ],
        "thinkers": [
            ("Pope Urban II", "Clermont'ta yaptığı konuşmayla Birinci Haçlı Seferi'ni başlatan reformcu Papa.", "Pope Urban II"),
            ("Alexios I Komnenos", "Diplomasisi ve askeri reformlarıyla Bizans'ta Komnenos restorasyonunu başlatan imparator.", "Alexios I Komnenos"),
            ("Anselm of Canterbury", "Skolastik felsefenin kurucusu; Tanrı'nın varlığına dair ontolojik kanıtın sahibi.", "Anselm of Canterbury"),
            ("Omar Khayyam", "Rubaileri, Celali takvimi ve üçüncü dereceden denklemlerin çözümüyle ünlü bilge.", "Omar Khayyam"),
        ],
        "zones": [
            {"poly": [(29.0, 41.0), (48.0, 41.0), (48.0, 30.0), (34.0, 31.0)], "style": 0},
            {"poly": [(6.0, 54.0), (17.0, 54.0), (16.0, 43.0), (7.0, 44.0)], "style": 1},
            {"poly": [(19.0, 44.0), (29.0, 44.0), (29.0, 36.0), (19.0, 36.0)], "style": 2},
        ],
        "banners": [
            (37.5, 38.5, "SELJUK EMPIRE"),
            (11.0, 49.5, "HOLY ROMAN EMP."),
            (23.0, 41.0, "BYZANTIUM"),
        ],
        "cities": [
            (28.9, 41.0, "CONSTANTINOPLE"),
            (12.3, 45.4, "VENICE"),
            (12.5, 41.9, "ROME"),
            (35.2, 31.8, "JERUSALEM"),
            (3.1, 45.8, "CLERMONT"),
        ],
        "battles": [
            (42.5, 39.1, "MANZIKERT"),
            (36.2, 36.2, "ANTIOCH"),
        ],
    },
    # 8. 1204 AD
    {
        "year": "1204 AD",
        "map_tag": "VENICE & 4TH CRUSADE",
        "title": "1204 AD: FOURTH CRUSADE & VENETIAN EMPIRE",
        "subtitle": "Konstantinopolis'in yağmalanması ve Venedik Deniz İmparatorluğu",
        "overview": (
            "1204 yılı Doğu ile Batı arasındaki tarihsel kırılma noktası oldu. Venedik Doju Enrico Dandolo'nun yönlendirdiği "
            "Dördüncü Haçlı Seferi ordusu, Mısır yerine Hristiyan Konstantinopolis'e saldırarak şehri ele geçirdi ve "
            "yağmaladı. Bizans toprakları paylaşıldı; Venedik 'İmparatorluğun dörtte biri ve yarısının efendisi' unvanıyla "
            "Girit, Eğriboz, Kiklad adaları ve Adriyatik limanlarını alarak bir deniz imparatorluğuna (Stato da Màr) "
            "dönüştü. Aynı yüzyıl başında İtalya'da Assisili Francesco ve matematikçi Fibonacci yeni bir kültür çağını açıyordu."
        ),
        "powers": [
            ("Republic of Venice", "Adriyatik, Ege adaları ve Girit'i kontrol eden en güçlü Akdeniz deniz cumhuriyeti.", "Republic of Venice"),
            ("Latin Empire", "1204'te Haçlıların Konstantinopolis'te kurduğu kısa ömürlü feodal devlet.", "Latin Empire"),
            ("Holy Roman Empire", "Hohenstaufen hanedanı altında Almanya'dan Sicilya Krallığı'na uzanan imparatorluk.", "Holy Roman Empire"),
            ("Ayyubid Sultanate", "Selahaddin Eyyubi'nin mirası üzerinde Mısır, Kudüs ve Suriye'ye hükmeden devlet.", "Ayyubid dynasty"),
        ],
        "events": [
            ("Fourth Crusade", "Amacından saparak Zara ve Konstantinopolis'in işgaliyle sonuçlanan 1202-1204 seferi.", "Fourth Crusade"),
            ("Sack of Constantinople", "Bin yıllık Doğu Roma başkentinin Haçlılarca yağmalanması ve sanat eserlerinin taşınması.", "Sack of Constantinople"),
            ("Magna Carta (1215)", "İngiltere'de Kral John'un yetkilerini sınırlayarak anayasal hukukun temelini atan belge.", "Magna Carta"),
            ("Spanish Reconquista", "1212 Las Navas de Tolosa zaferiyle İberya'da Hristiyan krallıkların üstünlüğü ele alması.", "Reconquista"),
        ],
        "thinkers": [
            ("Enrico Dandolo", "90'lı yaşlarında ve kör olmasına rağmen 4. Haçlı Seferi'ni yöneten Venedik Doju.", "Enrico Dandolo"),
            ("Pope Innocent III", "Orta Çağ Papalık kudretinin zirvesini temsil eden, 4. Lateran Konsili'ni toplayan Papa.", "Pope Innocent III"),
            ("Francis of Assisi", "Yoksulluk, doğa sevgisi ve kardeşlik öğretisiyle Fransisken tarikatını kuran İtalyan aziz.", "Francis of Assisi"),
            ("Fibonacci", "1202 'Liber Abaci' eseriyle Hint-Arap rakamlarını ve Fibonacci dizisini Avrupa'ya tanıtan Pisalı.", "Fibonacci"),
        ],
        "zones": [
            {"poly": [(12.0, 46.0), (27.0, 41.5), (27.0, 34.8), (19.0, 35.5), (13.0, 43.0)], "style": 0},
            {"poly": [(6.0, 54.0), (16.5, 54.0), (16.5, 37.0), (8.0, 44.0)], "style": 1},
            {"poly": [(28.0, 37.5), (42.0, 37.5), (42.0, 29.0), (28.0, 29.0)], "style": 2},
        ],
        "banners": [
            (19.5, 38.5, "VENETIAN MARITIME"),
            (11.0, 49.5, "HOLY ROMAN EMP."),
            (33.5, 31.0, "AYYUBIDS"),
        ],
        "cities": [
            (12.3, 45.4, "VENICE"),
            (28.9, 41.0, "CONSTANTINOPLE"),
            (10.4, 43.7, "PISA"),
            (31.2, 30.0, "CAIRO"),
        ],
        "battles": [
            (28.9, 41.0, "1204 SACK"),
            (-3.6, 38.3, "LAS NAVAS"),
        ],
    },
    # 9. 1347 AD
    {
        "year": "1347 AD",
        "map_tag": "BLACK DEATH & TRECENTO",
        "title": "1347 AD: THE BLACK DEATH & ITALIAN TRECENTO",
        "subtitle": "Kara Veba'nın Kefe'den İtalya'ya gelişi ve Dante-Petrarca-Boccaccio çağı",
        "overview": (
            "1347 sonbaharında Kırım'daki Kefe (Caffa) limanından kalkan Ceneviz ticaret kadırgaları, Messina, Cenova, "
            "Pisa ve Venedik limanlarına Kara Veba'yı (Black Death) taşıdı. Birkaç yıl içinde Avrupa nüfusunun üçte "
            "birinden fazlası hayatını kaybetti; feodal serflik sistemi çözüldü ve emek değeri yükseldi. Bu büyük trajedinin "
            "ortasında İtalya'da Trecento (1300'ler) kültür devrimi yaşanıyordu: Dante İtalyancayı edebiyat dili yapmış, "
            "Petrarca hümanizmi başlatmış, Boccaccio Veba günlerinde geçen 'Decameron'u yazmış, Giotto resim sanatında "
            "üç boyutlu duygusal gerçekçiliğin kapısını açmıştı."
        ),
        "powers": [
            ("Republic of Venice", "Doğu Akdeniz ticaret ağlarını elinde tutan 'La Serenissima' Venedik Cumhuriyeti.", "Republic of Venice"),
            ("Republic of Genoa", "Karadeniz (Kefe), Galata ve Batı Akdeniz'de Venedik'le yarışan deniz cumhuriyeti.", "Republic of Genoa"),
            ("Kingdom of Naples", "Anjou hanedanı yönetiminde Güney İtalya'ya hükmeden krallık.", "Kingdom of Naples"),
            ("Rising Ottoman Beylik", "Orhan Gazi döneminde Bursa ve İznik'i alıp Rumeli'ye geçmeye hazırlanan Osmanlılar.", "Ottoman Empire"),
        ],
        "events": [
            ("The Black Death", "1347-1351 arasında Avrupa ve Akdeniz dünyasını sarsan tarihin en yıkıcı veba salgını.", "Black Death"),
            ("Hundred Years' War", "İngiltere ve Fransa krallıkları arasında Crécy (1346) ile şiddetlenen uzun savaş.", "Hundred Years' War"),
            ("Avignon Papacy", "Papalığın 1309-1377 arasında Roma yerine Güney Fransa'daki Avignon'da ikamet etmesi.", "Avignon Papacy"),
            ("Early Renaissance Dawn", "Floransa ve Toskana şehirlerinde bankacılık, hümanizm ve yeni sanat anlayışının doğuşu.", "Italian Renaissance"),
        ],
        "thinkers": [
            ("Dante Alighieri", "'İlahi Komedya' (Divina Commedia) ile modern İtalyan dilinin babası olan Floransalı şair.", "Dante Alighieri"),
            ("Petrarch", "Antik elyazmalarını toplayan ve lirik soneleriyle Rönesans Hümanizmi'ni kuran şair.", "Petrarch"),
            ("Giovanni Boccaccio", "1348 Floransa vebasından kaçan 10 gencin anlattığı 100 öykülük 'Decameron'un yazarı.", "Giovanni Boccaccio"),
            ("Giotto di Bondone", "Scrovegni Şapeli freskleriyle Bizans ikona geleneğini aşan öncü Floransalı ressam.", "Giotto"),
        ],
        "zones": [
            {"poly": [(8.5, 46.0), (18.5, 45.0), (18.5, 37.0), (11.0, 38.0)], "style": 0},
            {"poly": [(-4.0, 51.0), (6.0, 50.0), (5.0, 43.0), (-2.0, 43.5)], "style": 1},
            {"poly": [(26.0, 41.5), (33.0, 41.5), (33.0, 38.0), (26.0, 38.0)], "style": 2},
        ],
        "banners": [
            (12.5, 43.0, "ITALIAN STATES"),
            (2.0, 47.0, "100 YEARS WAR"),
            (29.5, 39.5, "EARLY OTTOMANS"),
        ],
        "cities": [
            (11.2, 43.8, "FLORENCE"),
            (12.3, 45.4, "VENICE"),
            (8.9, 44.4, "GENOA"),
            (35.4, 45.0, "CAFFA"),
            (4.8, 43.9, "AVIGNON"),
        ],
        "battles": [
            (15.5, 38.2, "MESSINA PLAGUE PORT"),
            (1.9, 50.2, "CRECY 1346"),
        ],
    },
    # 10. 1453 AD
    {
        "year": "1453 AD",
        "map_tag": "FALL OF CONSTANTINOPLE",
        "title": "1453 AD: FALL OF CONSTANTINOPLE & NEW AGE",
        "subtitle": "Fatih Sultan Mehmed'in İstanbul fethi, Gutenberg matbaası ve Lodi Barışı",
        "overview": (
            "29 Mayıs 1453'te 21 yaşındaki Osmanlı Padişahı II. Mehmed (Fatih), devasa Şahi topları ve Haliç'e indirilen "
            "gemilerle 53 günlük kuşatmanın ardından Konstantinopolis'i fethetti. Bin yıllık Doğu Roma İmparatorluğu "
            "sona ererken Osmanlı Devleti cihan imparatorluğuna dönüştü. Aynı yıllarda Avrupa'da Orta Çağ'ı kapatan "
            "diğer gelişmeler yaşandı: Gutenberg hareketli metal harfli matbaayı icat etti, İngiltere ile Fransa arasındaki "
            "Yüzyıl Savaşları sona erdi ve İtalya'da Medici Floransa'sı, Venedik, Milano, Napoli ve Papalık arasında "
            "1454 Lodi Barışı ile 40 yıllık Rönesans dengesi kuruldu."
        ),
        "powers": [
            ("Ottoman Empire", "İstanbul'un fethiyle Balkanlar ve Anadolu'yu tek merkezde birleştiren süper güç.", "Ottoman Empire"),
            ("Republic of Venice", "Ege ve Doğu Akdeniz'de Osmanlı donanmasıyla karşı karşıya gelen deniz cumhuriyeti.", "Republic of Venice"),
            ("Republic of Florence", "Cosimo de' Medici liderliğinde bankacılık, felsefe ve Rönesans sanatının başkenti.", "Republic of Florence"),
            ("Papal States", "Rönesans papaları yönetiminde Roma'yı yeniden imar eden Orta İtalya devleti.", "Papal States"),
        ],
        "events": [
            ("Fall of Constantinople", "29 Mayıs 1453'te II. Mehmed'in İstanbul'u fethederek Orta Çağ'ı kapatması.", "Fall of Constantinople"),
            ("Gutenberg Printing Press", "Mainz'da hareketli metal harfli matbaanın icadıyla bilgi devriminin başlaması.", "Printing press"),
            ("Italian Balance of Power", "Lodi Barışı (1454) ile 5 büyük İtalyan devleti arasında kurulan diplomatik denge.", "Italian Renaissance"),
            ("End of 100 Years' War", "1453 Castillon Savaşı ile Fransa'nın ulusal toprak bütünlüğünü sağlaması.", "Hundred Years' War"),
        ],
        "thinkers": [
            ("Mehmed the Conqueror", "Doğu ve Batı dillerine hakim, 'Kayser-i Rum' unvanını kullanan vizyoner Osmanlı sultanı.", "Mehmed II"),
            ("Cosimo de' Medici", "Floransa'da Platon Akademisi'ni ve Rönesans sanatçılarını destekleyen 'Pater Patriae'.", "Cosimo de' Medici"),
            ("Leon Battista Alberti", "Mimar, sanat kuramcısı, şifrebilimci ve hümanist; 'Rönesans İnsanı'nın ilk örneği.", "Leon Battista Alberti"),
            ("Johannes Gutenberg", "Matbaa tekniğini geliştirerek kitap üretimini ve okuryazarlığı dönüştüren mucit.", "Johannes Gutenberg"),
        ],
        "zones": [
            {"poly": [(19.5, 45.0), (38.0, 42.0), (36.0, 36.5), (20.0, 36.5)], "style": 0},
            {"poly": [(8.0, 46.0), (18.5, 45.0), (18.5, 37.0), (9.0, 40.0)], "style": 1},
            {"poly": [(-4.0, 50.0), (6.0, 50.0), (6.0, 43.0), (-2.0, 43.0)], "style": 2},
        ],
        "banners": [
            (28.0, 39.5, "OTTOMAN EMPIRE"),
            (12.0, 43.0, "RENAISSANCE ITALY"),
            (2.0, 47.0, "FRANCE"),
        ],
        "cities": [
            (28.9, 41.0, "ISTANBUL (1453)"),
            (11.2, 43.8, "FLORENCE"),
            (12.3, 45.4, "VENICE"),
            (8.3, 50.0, "MAINZ"),
        ],
        "battles": [
            (28.9, 41.0, "1453 SIEGE"),
            (-0.0, 44.8, "CASTILLON"),
        ],
    },
    # 11. 1494 AD
    {
        "year": "1494 AD",
        "map_tag": "HIGH RENAISSANCE",
        "title": "1494 AD: HIGH RENAISSANCE & ITALIAN WARS",
        "subtitle": "Leonardo, Machiavelli, Michelangelo ve İtalya Savaşları'nın başlangıcı",
        "overview": (
            "1494 yılı İtalyan Rönesansı'nın hem sanatsal zirvesi hem de siyasi trajedisinin başlangıcıdır. Muhteşem "
            "Lorenzo'nun (Lorenzo de' Medici) 1492'deki ölümünün ardından, 1494'te Fransa Kralı VIII. Charles modern "
            "topçu ordusuyla Alpleri aşarak İtalya'ya girdi ve yarımadayı 60 yıl sürecek İtalya Savaşları'nın savaş "
            "alanına çevirdi. Tam bu kaosun ortasında Leonardo da Vinci Milano'da 'Son Akşam Yemeği'ni yapıyor, genç "
            "Michelangelo mermeri işliyor ve Floransa Cumhuriyeti sekreteri Niccolò Machiavelli modern siyaset bilimini "
            "doğuracak gözlemlerini topluyordu."
        ),
        "powers": [
            ("Republic of Florence", "Medici hanedanı, Savonarola ve Cumhuriyet dönemlerinde Rönesans'ın kalbi.", "Republic of Florence"),
            ("Republic of Venice", "Kara topraklarını (Terraferma) ve deniz ticaretini savunan zengin cumhuriyet.", "Republic of Venice"),
            ("Papal States", "Borgia ve Julius II döneminde Orta İtalya'da askeri ve sanatsal güç kazanan Papalık.", "Papal States"),
            ("Kingdom of France", "1494'te Napoli tahtı iddiasıyla İtalya'yı istila eden Avrupa'nın en kalabalık krallığı.", "Kingdom of France"),
        ],
        "events": [
            ("Italian Wars (1494)", "Fransa ve İspanya/Habsburg hanedanlarının İtalya hakimiyeti için yürüttüğü savaşlar.", "Italian Wars"),
            ("Treaty of Tordesillas", "1494'te İspanya ve Portekiz'in Yeni Dünya'yı meridyen çizgisiyle paylaşması.", "Treaty of Tordesillas"),
            ("Alhambra & 1492", "Granada'nın düşüşü ve Kolomb'un seferi sonrası Akdeniz'den Atlantik'e kayan ticaret.", "Alhambra"),
            ("Columbian Exchange", "Eski ve Yeni Dünya arasında bitkiler, madenler ve kültürlerin küresel dolaşımı.", "Columbian exchange"),
        ],
        "thinkers": [
            ("Leonardo da Vinci", "Ressam, anatomist, doğa bilgini ve mühendis; evrensel Rönesans dehası.", "Leonardo da Vinci"),
            ("Niccolò Machiavelli", "'Prens' (Il Principe) ve 'Söylevler' ile gerçekçi siyaset biliminin kurucusu Floransalı.", "Niccolò Machiavelli"),
            ("Michelangelo", "'Davut' heykeli ve Sistina Şapeli tavan freskleriyle Yüksek Rönesans'ın dev sanatçısı.", "Michelangelo"),
            ("Lorenzo de' Medici", "'Il Magnifico'; Floransa'nın altın çağını ve genç sanatçıları himaye eden devlet adamı.", "Lorenzo de' Medici"),
        ],
        "zones": [
            {"poly": [(7.5, 46.2), (18.5, 45.5), (18.5, 37.0), (8.0, 41.0)], "style": 0},
            {"poly": [(-4.5, 50.5), (7.5, 49.0), (7.5, 43.0), (-2.0, 43.0)], "style": 1},
            {"poly": [(-9.5, 43.5), (3.0, 42.5), (0.0, 36.0), (-9.5, 36.5)], "style": 2},
        ],
        "banners": [
            (12.5, 43.0, "ITALIAN STATES"),
            (2.0, 47.0, "FRANCE"),
            (-4.0, 40.0, "SPAIN"),
        ],
        "cities": [
            (11.2, 43.8, "FLORENCE"),
            (9.2, 45.5, "MILAN"),
            (12.3, 45.4, "VENICE"),
            (12.5, 41.9, "ROME"),
            (14.3, 40.8, "NAPLES"),
        ],
        "battles": [
            (10.1, 44.7, "FORNOVO 1495"),
        ],
    },
    # 12. 1555 AD
    {
        "year": "1555 AD",
        "map_tag": "HABSBURG vs OTTOMAN",
        "title": "1555 AD: PEACE OF AUGSBURG & SULEIMAN'S APOGEE",
        "subtitle": "Kanuni Sultan Süleyman, V. Karl, Reformasyon ve Augsburg Barışı",
        "overview": (
            "1555 yılı Avrupa ve Akdeniz'de iki devasa imparatorluğun ve dini bölünmenin zirvesiydi. Doğuda Kanuni "
            "Sultan Süleyman yönetimindeki Osmanlı İmparatorluğu Budin'den Bağdat'a, Cezayir'den Kırım'a hükmediyor; "
            "Barbaros Hayreddin Paşa'nın Preveze zaferiyle Akdeniz'de üstünlüğü elinde tutuyordu. Batıda ise Kutsal Roma "
            "İmparatoru V. Karl (Charles V), İspanya, Hollanda, Avusturya, Milano ve Napoli'yi kapsayan Habsburg "
            "topraklarında Martin Luther'in başlattığı Protestan Reformu ile mücadele ettikten sonra 1555 Augsburg "
            "Barışı ('Cuius regio, eius religio' - Kimin ülkesiyse onun dini) ile mezhep bölünmesini resmen tanıdı."
        ),
        "powers": [
            ("Ottoman Empire", "Kanuni Sultan Süleyman döneminde üç kıtada zirvesine ulaşan cihan imparatorluğu.", "Ottoman Empire"),
            ("Spanish Habsburg Empire", "İspanya, Güney İtalya, Milano, Hollanda ve Amerika'ya hükmeden küresel güç.", "Spanish Empire"),
            ("Holy Roman Empire", "Augsburg Barışı ile Katolik ve Lutherci prenslikler arasında dengelenen imparatorluk.", "Holy Roman Empire"),
            ("Republic of Venice", "Habsburg ve Osmanlı devleri arasında diplomasi ve deniz ticaretiyle yaşayan cumhuriyet.", "Republic of Venice"),
        ],
        "events": [
            ("Peace of Augsburg", "1555'te Kutsal Roma İmparatorluğu'nda Lutherciliği hukuken tanıyan antlaşma.", "Peace of Augsburg"),
            ("Protestant Reformation", "1517'de Martin Luther'in 95 Tezi ile başlayan Avrupa'nın dini ve siyasi dönüşümü.", "Reformation"),
            ("Council of Trent", "1545-1563 arasında Katolik Kilisesi'nin Karşı-Reform kararlarını aldığı konsil.", "Council of Trent"),
            ("Battle of Lepanto", "Doğu Akdeniz deniz hakimiyeti için Osmanlı ve Kutsal İttifak donanmalarının mücadelesi.", "Battle of Lepanto"),
        ],
        "thinkers": [
            ("Suleiman the Magnificent", "Avrupa'da 'Muhteşem', Osmanlı'da 'Kanuni' olarak anılan 46 yıllık padişah.", "Suleiman the Magnificent"),
            ("Charles V (Habsburg)", "'Üzerinde güneş batmayan imparatorluğu' yöneten ve 1556'da tahttan feragat eden hükümdar.", "Charles V, Holy Roman Emperor"),
            ("Martin Luther", "İncil'i Almancaya çevirerek Protestan Reformu'nu başlatan ilahiyatçı.", "Martin Luther"),
            ("Nicolaus Copernicus", "1543 'Göksel Kürelerin Dönüşleri' eseriyle Güneş merkezli evren modelini kuran bilgin.", "Nicolaus Copernicus"),
        ],
        "zones": [
            {"poly": [(16.0, 48.0), (40.0, 47.0), (48.0, 38.0), (48.0, 29.0), (3.0, 32.0), (19.0, 42.0)], "style": 0},
            {"poly": [(-9.5, 43.5), (3.0, 43.0), (16.0, 41.5), (16.0, 36.5), (-9.5, 36.0)], "style": 1},
            {"poly": [(6.0, 54.0), (18.0, 54.0), (17.0, 46.0), (6.0, 47.0)], "style": 2},
        ],
        "banners": [
            (28.0, 39.0, "OTTOMAN EMPIRE"),
            (-4.0, 40.0, "SPANISH HABSBURGS"),
            (11.0, 50.5, "HOLY ROMAN EMP."),
        ],
        "cities": [
            (28.9, 41.0, "ISTANBUL"),
            (16.4, 48.2, "VIENNA"),
            (10.9, 48.4, "AUGSBURG"),
            (11.1, 46.1, "TRENT"),
            (-3.7, 40.4, "MADRID"),
        ],
        "battles": [
            (20.7, 38.9, "PREVEZA"),
            (21.4, 38.3, "LEPANTO"),
        ],
    },
    # 13. 1648 AD
    {
        "year": "1648 AD",
        "map_tag": "PEACE OF WESTPHALIA",
        "title": "1648 AD: PEACE OF WESTPHALIA & SOVEREIGNTY",
        "subtitle": "Otuz Yıl Savaşları'nın sonu, modern ulus-devlet sistemi ve Bilim Devrimi",
        "overview": (
            "1648'de Münster ve Osnabrück'te imzalanan Vestfalya Barışı (Peace of Westphalia), Orta Avrupa'yı harap "
            "eden Otuz Yıl Savaşları'nı (1618-1648) sona erdirdi ve modern uluslararası ilişkilerin temelini oluşturan "
            "'egemen devlet' (Westphalian sovereignty) ilkesini kurdu. Hollanda ve İsviçre'nin bağımsızlığı resmen "
            "tanındı, Fransa ve İsveç yükselirken Kutsal Roma İmparatorluğu 300'den fazla özerk prensliğe bölündü. "
            "Aynı dönemde Galileo, Descartes, Hobbes ve Spinoza ile Avrupa'da Bilim Devrimi ve rasyonalist felsefe doğdu."
        ),
        "powers": [
            ("Kingdom of France", "Kardinal Richelieu ve Mazarin'in stratejisiyle Avrupa'nın başat kara gücü olan krallık.", "Kingdom of France"),
            ("Holy Roman Empire", "Vestfalya sonrası gevşek bir prenslikler konfederasyonuna dönüşen Orta Avrupa yapısı.", "Holy Roman Empire"),
            ("Dutch Republic", "İspanya'dan bağımsızlığını kazanan, Amsterdam merkezli küresel deniz ve finans gücü.", "Netherlands"),
            ("Ottoman Empire", "Girit Savaşı (Kandiye Kuşatması) ile Venedik'e karşı Doğu Akdeniz'de mücadele eden güç.", "Ottoman Empire"),
        ],
        "events": [
            ("Peace of Westphalia", "1648'de din savaşlarını bitirip devletlerin iç egemenliği ilkesini kuran antlaşma.", "Peace of Westphalia"),
            ("Thirty Years' War", "1618-1648 arasında Almanya nüfusunun üçte birini yok eden yıkıcı Avrupa savaşı.", "Thirty Years' War"),
            ("English Civil War", "İngiltere'de Parlamento ile Kral I. Charles arasındaki iç savaş ve mutlakiyetin sarsılması.", "English Civil War"),
            ("Scientific Revolution", "Gözlem, deney ve matematiksel doğa yasalarıyla modern bilimin kuruluşu.", "Scientific Revolution"),
        ],
        "thinkers": [
            ("Galileo Galilei", "Teleskop gözlemleri ve hareket yasalarıyla modern fiziğin ve astronominin kurucusu İtalyan bilgin.", "Galileo Galilei"),
            ("René Descartes", "'Cogito, ergo sum' (Düşünüyorum, öyleyse varım) diyerek modern felsefeyi kuran düşünür.", "René Descartes"),
            ("Thomas Hobbes", "1651 'Leviathan' eseriyle toplumsal sözleşme ve egemen devlet kuramını kuran filozof.", "Thomas Hobbes"),
            ("Baruch Spinoza", "Amsterdam'da yetişen, 'Etika' eseriyle panteist rasyonalizmi ve düşünce özgürlüğünü savunan filozof.", "Baruch Spinoza"),
        ],
        "zones": [
            {"poly": [(-4.5, 50.5), (7.5, 49.5), (7.0, 42.5), (-2.0, 43.0)], "style": 0},
            {"poly": [(7.0, 54.0), (19.0, 54.0), (18.0, 46.0), (7.0, 46.5)], "style": 1},
            {"poly": [(18.0, 47.0), (38.0, 47.0), (38.0, 35.0), (19.0, 35.0)], "style": 2},
        ],
        "banners": [
            (2.0, 46.5, "FRANCE"),
            (11.5, 50.0, "WESTPHALIAN HRE"),
            (27.0, 40.0, "OTTOMANS"),
        ],
        "cities": [
            (7.6, 52.0, "MUNSTER"),
            (4.9, 52.4, "AMSTERDAM"),
            (2.3, 48.9, "PARIS"),
            (11.2, 43.8, "FLORENCE"),
        ],
        "battles": [
            (12.3, 51.3, "LUTZEN"),
            (25.1, 35.3, "CANDIA SIEGE"),
        ],
    },
    # 14. 1789 AD
    {
        "year": "1789 AD",
        "map_tag": "FRENCH REVOLUTION",
        "title": "1789 AD: ENLIGHTENMENT & FRENCH REVOLUTION",
        "subtitle": "Bastille Baskını, İnsan Hakları Bildirgesi ve Aydınlanma Felsefesi",
        "overview": (
            "14 Temmuz 1789'da Paris halkının Bastille Hapishanesi'ni basmasıyla Fransız Devrimi patlak verdi ve Avrupa'nın "
            "bin yıllık mutlak monarşi ve feodal imtiyaz düzeni (Ancien Régime) temelden sarsıldı. Ağustos 1789'da "
            "'İnsan ve Yurttaş Hakları Bildirgesi' kabul edilerek özgürlük, eşitlik ve ulusal egemenlik ilkeleri ilan "
            "edildi. Bu devrim; Voltaire, Rousseau, Montesquieu, Königsberg'de 'Aydınlanma Nedir?' diye soran Immanuel "
            "Kant ve Milano'da modern ceza hukukunu kuran Cesare Beccaria'nın Aydınlanma Çağı fikirlerinin ürünüydü."
        ),
        "powers": [
            ("Revolutionary France", "Ancien Régime'i yıkarak ulusal meclis ve yurttaşlık düzenini kuran Fransa.", "Kingdom of France"),
            ("Great Britain", "Sanayi Devrimi'ne öncülük eden parlamenter monarşi ve küresel deniz imparatorluğu.", "Kingdom of Great Britain"),
            ("Habsburg Monarchy", "Viyana merkezli, Orta Avrupa ve Kuzey İtalya (Lombardiya) üzerinde etkili güç.", "Habsburg monarchy"),
            ("Russian Empire", "II. Katerina (Büyük Katerina) döneminde Karadeniz ve Polonya'ya doğru genişleyen imparatorluk.", "Russian Empire"),
        ],
        "events": [
            ("French Revolution", "1789'da başlayıp Avrupa ve dünya siyasetini kökten değiştiren büyük devrim.", "French Revolution"),
            ("Storming of the Bastille", "14 Temmuz 1789'da kraliyet istibdadının sembolü olan kalenin halkça ele geçirilmesi.", "Storming of the Bastille"),
            ("March on Versailles", "Ekim 1789'da Paris halkının Versay Sarayı'na yürüyerek Kral XVI. Louis'yi Paris'e getirmesi.", "Palace of Versailles"),
            ("Age of Enlightenment", "Akıl, bilim, laiklik ve insan haklarını merkeze alan 18. yüzyıl düşünce hareketi.", "Age of Enlightenment"),
        ],
        "thinkers": [
            ("Immanuel Kant", "'Saf Aklın Eleştirisi' ve ödev ahlakıyla modern felsefeyi dönüştüren Königsbergli filozof.", "Immanuel Kant"),
            ("Jean-Jacques Rousseau", "'Toplum Sözleşmesi' ile genel irade ve halk egemenliği fikrini kuran düşünür.", "Jean-Jacques Rousseau"),
            ("Voltaire", "Hoşgörü, ifade özgürlüğü ve dogmatizm karşıtlığının keskin kalemi Fransız aydınlanmacı.", "Voltaire"),
            ("Cesare Beccaria", "1764 'Suçlar ve Cezalar Hakkında' eseriyle işkence ve idama karşı çıkan Milanolu hukukçu.", "Cesare Beccaria"),
        ],
        "zones": [
            {"poly": [(-4.8, 51.0), (8.0, 49.0), (7.5, 42.5), (-2.0, 43.0)], "style": 0},
            {"poly": [(12.0, 51.0), (24.0, 50.0), (22.0, 44.0), (9.0, 45.0)], "style": 1},
            {"poly": [(24.0, 59.0), (48.0, 59.0), (48.0, 45.0), (28.0, 46.0)], "style": 2},
        ],
        "banners": [
            (2.0, 46.8, "REV. FRANCE"),
            (16.5, 47.8, "HABSBURGS"),
            (36.0, 53.0, "RUSSIA"),
        ],
        "cities": [
            (2.3, 48.9, "PARIS"),
            (20.5, 54.7, "KONIGSBERG"),
            (9.2, 45.5, "MILAN"),
            (-0.1, 51.5, "LONDON"),
            (16.4, 48.2, "VIENNA"),
        ],
        "battles": [
            (2.4, 48.9, "BASTILLE 1789"),
        ],
    },
    # 15. 1812 AD
    {
        "year": "1812 AD",
        "map_tag": "NAPOLEONIC PEAK",
        "title": "1812 AD: NAPOLEONIC EMPIRE AT ITS PEAK",
        "subtitle": "Madrid'den Moskova kapılarına Napolyon Avrupası ve Medeni Kanun",
        "overview": (
            "1812 yazında Napolyon Bonapart yönetimindeki Birinci Fransız İmparatorluğu ve bağlı devletleri Madrid'den "
            "Varşova'ya, Roma ve İlirya'dan Hamburg'a kadar tüm Kıta Avrupası'na hükmediyordu. Napolyon İtalya'da bin "
            "yıllık Venedik Cumhuriyeti'ne son vermiş, İtalya Krallığı'nı kurmuş ve gittiği her yere 'Code Napoléon' "
            "(Medeni Kanun), metrik sistem ve modern idareyi taşımıştı. Ancak Haziran 1812'de 600.000 kişilik Grande "
            "Armée ile başlattığı Rusya Seferi, Borodino Savaşı ve Moskova yangınının ardından kış soğuğunda felaketle "
            "sonuçlanarak imparatorluğun çöküşünü başlattı."
        ),
        "powers": [
            ("First French Empire", "Napolyon yönetiminde Roma, Amsterdam ve Hamburg'u doğrudan içeren imparatorluk.", "First French Empire"),
            ("United Kingdom", "Trafalgar zaferiyle denizleri kontrol eden ve Kıta Ablukası'na direnen baş rakip.", "United Kingdom"),
            ("Russian Empire", "Çar I. Aleksandr yönetiminde 1812 Vatanseverlik Savaşı ile Napolyon'u durduran güç.", "Russian Empire"),
            ("Austrian Empire", "Austerlitz ve Wagram yenilgileri sonrası Napolyon ile zorunlu ittifak yapan Habsburg devleti.", "Austrian Empire"),
        ],
        "events": [
            ("Invasion of Russia (1812)", "Grande Armée'nin Moskova'ya yürüyüşü ve yıkıcı kış çekilmesi.", "French invasion of Russia"),
            ("Napoleonic Wars", "1803-1815 arasında Avrupa haritasını ve ordularını dönüştüren koalisyon savaşları.", "Napoleonic Wars"),
            ("Peninsular War", "İspanya ve Portekiz'de Fransız işgaline karşı yürütülen yıpratıcı gerilla ve cephe savaşı.", "Peninsular War"),
            ("Napoleonic Code", "1804'te yürürlüğe giren, kanun önünde eşitlik ve mülkiyet hukukunu kuran medeni kanun.", "Napoleonic Code"),
        ],
        "thinkers": [
            ("Napoleon Bonaparte", "Fransız Devrimi'nin generali, imparator ve modern devlet kurumlarının kurucusu.", "Napoleon"),
            ("G.W.F. Hegel", "1806 Jena'da Napolyon'u gördüğünde 'At üzerindeki Dünya Ruhu' diyen Alman idealist filozof.", "Georg Wilhelm Friedrich Hegel"),
            ("J.W. von Goethe", "'Faust'un yazarı; Weimar klasisizminin ve dünya edebiyatı (Weltliteratur) kavramının öncüsü.", "Johann Wolfgang von Goethe"),
            ("Ugo Foscolo", "Venedik'in Napolyon tarafından Avusturya'ya verilmesi üzerine 'Jacopo Ortis'i yazan İtalyan şair.", "Ugo Foscolo"),
        ],
        "zones": [
            {"poly": [(-9.0, 43.5), (22.0, 54.5), (22.0, 40.0), (-9.0, 36.5)], "style": 0},
            {"poly": [(24.0, 59.0), (48.0, 59.0), (48.0, 45.0), (24.0, 47.0)], "style": 1},
            {"poly": [(-6.0, 58.0), (2.0, 58.0), (2.0, 50.0), (-6.0, 50.0)], "style": 2},
        ],
        "banners": [
            (7.0, 47.5, "FRENCH EMPIRE & ALLIES"),
            (36.0, 53.0, "RUSSIAN EMPIRE"),
            (-2.0, 54.0, "BRITAIN"),
        ],
        "cities": [
            (2.3, 48.9, "PARIS"),
            (37.6, 55.8, "MOSCOW"),
            (9.2, 45.5, "MILAN"),
            (-3.7, 40.4, "MADRID"),
        ],
        "battles": [
            (35.8, 55.5, "BORODINO 1812"),
            (16.8, 49.1, "AUSTERLITZ"),
        ],
    },
    # 16. 1848 AD
    {
        "year": "1848 AD",
        "map_tag": "RISORGIMENTO & 1848",
        "title": "1848 AD: SPRINGTIME OF NATIONS & RISORGIMENTO",
        "subtitle": "Avrupa'da 1848 Devrimleri, Torino/Piyemonte ve İtalyan Risorgimento'su",
        "overview": (
            "1848 yılı Avrupa tarihinde 'Ulusların Baharı' (Springtime of Nations) olarak patlak verdi. Ocak 1848'de "
            "Palermo'da başlayan ayaklanmalar Şubat'ta Paris'e, Mart'ta Viyana, Berlin, Budapeşte, Milano ve Venedik'e "
            "yayıldı. İtalya'da Milano halkı 'Beş Gün' (Cinque Giornate) ayaklanmasıyla Avusturya Mareşali Radetzky'yi "
            "şehirden çıkardı; Torino merkezli Sardinya-Piyemonte Kralı Carlo Alberto anayasa (Statuto Albertino) ilan "
            "ederek Birinci İtalyan Bağımsızlık Savaşı'nı başlattı; Mazzini ve Garibaldi ise 1849'da Roma Cumhuriyeti'ni "
            "savundu. İlk dalga bastırılsa da İtalya'nın birleşmesi (Risorgimento) geri dönülmez biçimde başladı."
        ),
        "powers": [
            ("Kingdom of Sardinia", "Torino merkezli, Statuto Albertino anayasasıyla İtalyan birleşmesine liderlik eden krallık.", "Kingdom of Sardinia"),
            ("Austrian Empire", "Lombardiya-Venedik ve Orta Avrupa'da 1848 devrimlerini bastırmaya çalışan güç.", "Austrian Empire"),
            ("French Republic", "Şubat 1848 devrimiyle krallığı devirip genel oy hakkını getiren İkinci Cumhuriyet.", "France"),
            ("Kingdom of Prussia", "Frankfurt Parlamentosu ve Alman birliği tartışmalarının merkezindeki Kuzey Alman gücü.", "Kingdom of Prussia"),
        ],
        "events": [
            ("Revolutions of 1848", "Avrupa genelinde anayasa, basın özgürlüğü ve ulusal birlik talep eden devrim dalgası.", "Revolutions of 1848"),
            ("Unification of Italy", "Risorgimento: Bölünmüş İtalya yarımadasının tek bir ulus-devlet olma mücadelesi.", "Unification of Italy"),
            ("Communist Manifesto", "Şubat 1848'de Karl Marx ve Friedrich Engels'in Londra'da yayımladığı manifesto.", "The Communist Manifesto"),
            ("Five Days of Milan", "Mart 1848'de Milano halkının barikatlarla Avusturya garnizonuna karşı direnişi.", "Revolutions of 1848"),
        ],
        "thinkers": [
            ("Giuseppe Garibaldi", "'İki Dünyanın Kahramanı'; Kırmızı Gömlekliler ile İtalya'yı birleştiren halk önderi.", "Giuseppe Garibaldi"),
            ("Giuseppe Mazzini", "'Giovine Italia' (Genç İtalya) hareketinin kurucusu, demokratik cumhuriyetçi düşünür.", "Giuseppe Mazzini"),
            ("Giacomo Leopardi", "'Canti' şiirleri ve 'Zibaldone' notlarıyla 19. yüzyıl İtalyan edebiyatının en derin filozof-şairi.", "Giacomo Leopardi"),
            ("Alessandro Manzoni", "'I Promessi Sposi' (Nişanlılar) romanıyla modern standart İtalyan nesrini kuran yazar.", "Alessandro Manzoni"),
        ],
        "zones": [
            {"poly": [(6.5, 46.5), (10.5, 46.0), (10.0, 39.0), (7.5, 39.0)], "style": 0},
            {"poly": [(10.5, 51.0), (24.0, 50.0), (22.0, 44.5), (10.5, 45.0)], "style": 1},
            {"poly": [(-4.5, 50.5), (7.5, 49.0), (7.0, 42.5), (-2.0, 43.0)], "style": 2},
        ],
        "banners": [
            (8.0, 44.8, "PIEDMONT"),
            (16.0, 47.5, "AUSTRIA"),
            (2.0, 46.8, "FRANCE 1848"),
        ],
        "cities": [
            (7.7, 45.1, "TURIN"),
            (9.2, 45.5, "MILAN"),
            (12.3, 45.4, "VENICE"),
            (12.5, 41.9, "ROME"),
            (2.3, 48.9, "PARIS"),
        ],
        "battles": [
            (10.7, 45.4, "CUSTOZA"),
            (13.3, 38.1, "PALERMO"),
        ],
    },
    # 17. 1871 AD
    {
        "year": "1871 AD",
        "map_tag": "ITALY & GERMANY UNIFIED",
        "title": "1871 AD: UNIFICATION OF ITALY & GERMAN EMPIRE",
        "subtitle": "Roma'nın İtalya başkenti oluşu ve Bismarck'ın Alman İmparatorluğu",
        "overview": (
            "1870-1871 yılları Avrupa haritasının merkezini yeniden çizdi. Başbakan Cavour'un diplomasisi, Garibaldi'nin "
            "Binler Seferi (Spedizione dei Mille) ve Kral II. Vittorio Emanuele'nin liderliğiyle 1861'de Torino'da ilan "
            "edilen İtalya Krallığı, 20 Eylül 1870'te Porta Pia gedik açma harekatıyla Roma'ya girdi ve 1871'de Roma "
            "resmen birleşik İtalya'nın başkenti ('Roma Capitale') oldu. Aynı anda Otto von Bismarck yönetimindeki "
            "Prusya, Fransa-Prusya Savaşı'nı kazanarak Ocak 1871'de Versay Sarayı'nda Alman İmparatorluğu'nu ilan etti."
        ),
        "powers": [
            ("Unified Kingdom of Italy", "Torino ve Floransa'nın ardından 1871'de Roma'yı başkent yapan birleşik İtalya.", "Italy"),
            ("German Empire", "Bismarck'ın 'kan ve demir' politikasıyla Prusya liderliğinde kurulan imparatorluk.", "German Empire"),
            ("Third French Republic", "Sedan yenilgisi ve Paris Komünü sonrası Fransa'da kurulan cumhuriyet rejimi.", "France"),
            ("Austria-Hungary", "1867 Uzlaşması (Ausgleich) ile kurulan Viyana-Budapeşte ikili monarşisi.", "Austria-Hungary"),
        ],
        "events": [
            ("Unification of Italy", "1861-1871 arasında İtalya yarımadasının tek bayrak altında birleşmesinin tamamlanması.", "Unification of Italy"),
            ("Franco-Prussian War", "1870-1871'de hem Alman hem İtalyan birleşmesinin önünü açan savaş.", "Franco-Prussian War"),
            ("Paris Commune (1871)", "Mart-Mayıs 1871'de kuşatma altındaki Paris'te kurulan devrimci yerel yönetim.", "Paris Commune"),
            ("2nd Industrial Revolution", "Çelik, demiryolları, telgraf ve elektrikle Avrupa sanayisinin sıçraması.", "Second Industrial Revolution"),
        ],
        "thinkers": [
            ("Count of Cavour", "Piyemonte Başbakanı; İtalyan birleşmesinin diplomatik ve ekonomik mimarı.", "Camillo Benso, Count of Cavour"),
            ("Victor Emmanuel II", "Birleşik İtalya'nın ilk kralı; İtalyanca 'Padre della Patria' (Vatanın Babası).", "Victor Emmanuel II"),
            ("Giuseppe Verdi", "'Nabucco' (Va, pensiero) ve 'Aida' operalarıyla Risorgimento ruhunun bestecisi.", "Giuseppe Verdi"),
            ("Friedrich Nietzsche", "'Tragedyaların Doğuşu' ve 'Böyle Buyurdu Zerdüşt' ile modern kültürün radikal eleştirmeni.", "Friedrich Nietzsche"),
        ],
        "zones": [
            {"poly": [(6.8, 46.2), (18.5, 45.5), (18.5, 36.8), (8.0, 38.5)], "style": 0},
            {"poly": [(6.0, 55.0), (21.5, 55.0), (19.0, 47.5), (7.0, 47.5)], "style": 1},
            {"poly": [(12.0, 50.5), (26.0, 49.5), (25.0, 43.0), (13.5, 45.0)], "style": 2},
        ],
        "banners": [
            (12.5, 42.5, "KINGDOM OF ITALY"),
            (12.0, 52.0, "GERMAN EMPIRE"),
            (19.0, 47.0, "AUSTRIA-HUNGARY"),
        ],
        "cities": [
            (12.5, 41.9, "ROME (CAPITALE)"),
            (7.7, 45.1, "TURIN"),
            (13.4, 52.5, "BERLIN"),
            (2.3, 48.9, "PARIS"),
        ],
        "battles": [
            (4.9, 49.7, "SEDAN 1870"),
            (12.5, 41.9, "PORTA PIA"),
        ],
    },
    # 18. 1914 AD
    {
        "year": "1914 AD",
        "map_tag": "GREAT WAR (WWI)",
        "title": "1914 AD: THE GREAT WAR & FALL OF EMPIRES",
        "subtitle": "Saraybosna Suikastı, İtilaf-İttifak blokları ve Çanakkale'den Marne'a",
        "overview": (
            "28 Haziran 1914'te Saraybosna'da Avusturya-Macaristan Veliahtı Franz Ferdinand'ın suikasta uğraması, "
            "Avrupa'daki gizli ittifak mekanizmalarını tetikleyerek Birinci Dünya Savaşı'nı başlattı. Almanya, "
            "Avusturya-Macaristan ve Osmanlı İmparatorluğu (İttifak Devletleri) ile Britanya, Fransa, Rusya ve 1915'te "
            "katılan İtalya (İtilaf Devletleri) siper savaşlarında karşı karşıya geldi. Marne, Verdun, Somme, Isonzo "
            "ve Çanakkale (Gallipoli) cephelerinde milyonlarca insan hayatını kaybederken dört büyük imparatorluk "
            "(Osmanlı, Rus, Avusturya-Macaristan, Alman) yıkıldı."
        ),
        "powers": [
            ("British Empire", "Kraliyet Donanması ve küresel kaynaklarıyla İtilaf bloğunun deniz ve finans gücü.", "British Empire"),
            ("German Empire", "Batı ve Doğu cephelerinde aynı anda savaşan İttifak bloğunun ana askeri gücü.", "German Empire"),
            ("French Republic", "Marne ve Verdun cephelerinde vatan topraklarını savunan İtilaf devleti.", "France"),
            ("Ottoman Empire", "Çanakkale, Kafkasya, Irak ve Filistin cephelerinde savaşan Doğu gücü.", "Ottoman Empire"),
        ],
        "events": [
            ("World War I", "1914-1918 arasında modern endüstriyel silahlarla yürütülen ilk küresel topyekûn savaş.", "World War I"),
            ("Sarajevo Assassination", "28 Haziran 1914'te Temmuz Krizini ve savaşı tetikleyen suikast.", "Assassination of Archduke Franz Ferdinand"),
            ("Battle of the Marne", "Eylül 1914'te Alman Schlieffen Planı'nı durdurup Batı Cephesi'ni siperlere kilitleyen savaş.", "First Battle of the Marne"),
            ("Gallipoli Campaign", "1915'te Osmanlı ordusunun ve Mustafa Kemal'in İtilaf donanmasını durdurduğu destansı savunma.", "Gallipoli campaign"),
        ],
        "thinkers": [
            ("Albert Einstein", "1915'te Genel Görelilik Kuramı'nı tamamlayarak uzay, zaman ve kütleçekimi anlayışını değiştiren fizikçi.", "Albert Einstein"),
            ("Sigmund Freud", "Viyana'da psikanaliz kuramını ve bilinçdışı kavramını geliştiren nörolog ve düşünür.", "Sigmund Freud"),
            ("Luigi Pirandello", "Kimlik, maske ve görecelik temalarıyla modern tiyatroyu dönüştüren Nobel ödüllü İtalyan yazar.", "Luigi Pirandello"),
            ("Max Weber", "'Protestan Ahlakı' ve bürokrasi/otorite analizleriyle modern sosyolojinin kurucusu.", "Max Weber"),
        ],
        "zones": [
            {"poly": [(6.0, 55.0), (23.0, 54.0), (26.0, 42.0), (42.0, 41.0), (42.0, 31.0), (13.0, 45.0)], "style": 0},
            {"poly": [(-5.0, 55.0), (7.0, 50.0), (18.0, 40.0), (-5.0, 40.0)], "style": 1},
            {"poly": [(23.0, 59.0), (48.0, 59.0), (48.0, 44.0), (26.0, 45.0)], "style": 2},
        ],
        "banners": [
            (15.0, 49.0, "CENTRAL POWERS"),
            (2.0, 46.5, "TRIPLE ENTENTE"),
            (33.0, 52.0, "RUSSIA"),
        ],
        "cities": [
            (18.4, 43.9, "SARAJEVO"),
            (2.3, 48.9, "PARIS"),
            (13.4, 52.5, "BERLIN"),
            (28.9, 41.0, "ISTANBUL"),
        ],
        "battles": [
            (26.2, 40.2, "GALLIPOLI 1915"),
            (3.5, 49.0, "MARNE"),
            (13.6, 45.9, "ISONZO"),
        ],
    },
    # 19. 1942 AD
    {
        "year": "1942 AD",
        "map_tag": "WWII TURNING POINT",
        "title": "1942 AD: WORLD WAR II TURNING POINT",
        "subtitle": "Stalingrad ve El-Alameyn dönüm noktaları, Direniş ve Varoluşçuluk",
        "overview": (
            "1942 sonbaharında Mihver Devletleri (Axis) Avrupa ve Kuzey Afrika'da en geniş işgal sınırlarına ulaşmıştı; "
            "ancak savaşın kaderi tam bu noktada döndü. Kasım 1942'de Kuzey Afrika'da El-Alameyn ve Volga kıyısında "
            "Stalingrad kuşatmasıyla Müttefikler stratejik üstünlüğü ele geçirdi. 1943'te Müttefiklerin Sicilya çıkarması "
            "sonrası İtalya'da faşist rejim çöktü ve Kuzey İtalya'da özellikle Torino, Milano ve dağlarda antifaşist "
            "Partizan Direnişi (Resistenza) yükseldi. Bu karanlık yıllarda Gramsci, Croce, Camus ve Torino doğumlu "
            "kimyager-yazar Primo Levi insanlık onurunun hafızasını kayda geçirdi."
        ),
        "powers": [
            ("Allies of WWII", "Birleşik Krallık, ABD, SSCB ve Özgür Avrupa direniş güçlerinden oluşan koalisyon.", "Allies of World War II"),
            ("Axis Powers", "Nazi Almanyası ve Faşist İtalya liderliğindeki işgal bloğu.", "Axis powers"),
            ("Soviet Union", "Doğu Cephesi'nde Stalingrad ve Kursk'ta savaşın yükünü taşıyan süper güç.", "Soviet Union"),
            ("United Kingdom", "Britanya Savaşı ve Kuzey Afrika'da Avrupa'nın düşmesini engelleyen ada devleti.", "United Kingdom"),
        ],
        "events": [
            ("World War II", "1939-1945 arasında insanlık tarihinin en büyük ve en yıkıcı küresel savaşı.", "World War II"),
            ("Battle of Stalingrad", "1942-1943 kışında Alman 6. Ordusu'nun kuşatılmasıyla savaşın kırılma noktası.", "Battle of Stalingrad"),
            ("Normandy Landings", "6 Haziran 1944 D-Day çıkarmasıyla Batı Avrupa'nın kurtuluşunun başlaması.", "Normandy landings"),
            ("Collapse of Fascism", "İtalya'da 1943-1945 arasında Mussolini rejiminin çöküşü ve partizan direnişi.", "Italian fascism"),
        ],
        "thinkers": [
            ("Antonio Gramsci", "'Hapishane Defterleri'nde kültürel hegemonya kavramını geliştiren İtalyan düşünür.", "Antonio Gramsci"),
            ("Benedetto Croce", "Tarihselcilik, estetik ve özgürlük felsefesini savunan Napolili liberal filozof.", "Benedetto Croce"),
            ("Albert Camus", "1942'de 'Yabancı' ve 'Sisifos Söylenini' yayımlayan, Fransız Direnişi'nin gazeteci-filozofu.", "Albert Camus"),
            ("Primo Levi", "Torinolu kimyager; 'Bunlar da mı İnsan?' (Se questo è un uomo) eseriyle tanıklık edebiyatının zirvesi.", "Primo Levi"),
        ],
        "zones": [
            {"poly": [(-2.0, 50.0), (38.0, 55.0), (42.0, 44.0), (25.0, 35.0), (-2.0, 43.0)], "style": 0},
            {"poly": [(38.0, 59.0), (48.0, 59.0), (48.0, 42.0), (42.0, 44.0)], "style": 1},
            {"poly": [(-6.0, 58.0), (2.0, 58.0), (2.0, 50.0), (-6.0, 50.0)], "style": 2},
        ],
        "banners": [
            (13.0, 49.0, "AXIS OCCUPIED EUROPE"),
            (41.5, 53.0, "USSR"),
            (-2.0, 54.0, "ALLIES"),
        ],
        "cities": [
            (-0.1, 51.5, "LONDON"),
            (37.6, 55.8, "MOSCOW"),
            (7.7, 45.1, "TURIN"),
            (12.5, 41.9, "ROME"),
        ],
        "battles": [
            (44.5, 48.7, "STALINGRAD"),
            (28.9, 30.8, "EL ALAMEIN"),
            (-0.8, 49.3, "NORMANDY"),
        ],
    },
    # 20. 1989 AD
    {
        "year": "1989 AD",
        "map_tag": "FALL OF IRON CURTAIN",
        "title": "1989 AD: BERLIN WALL FALLS & UNITED EUROPE",
        "subtitle": "Berlin Duvarı'nın yıkılışı, Soğuk Savaş'ın sonu ve Avrupa Birliği",
        "overview": (
            "9 Kasım 1989 gecesi Berlin Duvarı'nın yıkılmasıyla, 1945'ten beri Avrupa'yı Stettin'den Trieste'ye ikiye "
            "bölen Demir Perde (Iron Curtain) ve Soğuk Savaş sona erdi. Polonya'da Dayanışma (Solidarność) hareketiyle "
            "başlayan 1989 Devrimleri, Prag'da Kadife Devrim ve Orta-Doğu Avrupa'da barışçıl demokratik dönüşümle "
            "devam etti. 1957 Roma Antlaşması ile temeli atılan Avrupa bütünleşmesi, Doğu ve Batı Avrupa'yı yeniden "
            "birleştirerek Avrupa Birliği'ne dönüştü. İtalyan ve Avrupa düşüncesinde Calvino, Umberto Eco, Arendt ve "
            "Foucault modern dünyayı yeniden yorumladı."
        ),
        "powers": [
            ("European Community / EU", "1957 Roma Antlaşması'ndan doğup kıtayı barış ve ortak pazarda birleştiren birlik.", "European Union"),
            ("NATO Alliance", "Kuzey Atlantik ve Batı Avrupa'nın ortak savunma ve güvenlik ittifakı.", "NATO"),
            ("Soviet Union", "Mihail Gorbaçov'un Glasnost ve Perestroyka reformları döneminde çözülen doğu süper gücü.", "Soviet Union"),
            ("Italian Republic", "1946'da kurulan, Avrupa Topluluğu'nun 6 kurucu üyesinden biri olan sanayi ve kültür gücü.", "Italy"),
        ],
        "events": [
            ("Fall of Berlin Wall", "9 Kasım 1989'da Doğu ve Batı Berlin arasındaki duvarın halk tarafından yıkılması.", "Fall of the Berlin Wall"),
            ("Revolutions of 1989", "Orta ve Doğu Avrupa'da tek parti rejimlerinin yıkıldığı demokratik dönüşüm dalgası.", "Revolutions of 1989"),
            ("End of the Cold War", "ABD ve SSCB arasındaki 45 yıllık ideolojik ve nükleer kutuplaşmanın sona ermesi.", "Cold War"),
            ("Treaty of Rome (1957)", "Roma'da İtalya, Fransa, Almanya ve Benelüks'ün Avrupa Ekonomik Topluluğu'nu kurması.", "Treaty of Rome"),
        ],
        "thinkers": [
            ("Italo Calvino", "'Görünmez Kentler' ve 'Bir Kış Gecesi Eğer Bir Yolcu' ile dünya edebiyatının ustası İtalyan yazar.", "Italo Calvino"),
            ("Umberto Eco", "Bologna Üniversitesi göstergebilim profesörü ve 'Gülün Adı' (Il nome della rosa) yazarı.", "Umberto Eco"),
            ("Hannah Arendt", "Totalitarizmin Kökenleri ve 'İnsanlık Durumu' eserleriyle 20. yüzyılın en önemli siyaset filozofu.", "Hannah Arendt"),
            ("Michel Foucault", "İktidar, bilgi, söylem ve modern kurumların soykütüğünü inceleyen Fransız düşünür.", "Michel Foucault"),
        ],
        "zones": [
            {"poly": [(-9.5, 58.0), (13.5, 54.0), (13.8, 45.6), (26.0, 36.0), (-9.5, 36.0)], "style": 0},
            {"poly": [(13.5, 55.0), (48.0, 58.0), (48.0, 42.0), (14.0, 45.5)], "style": 1},
        ],
        "frontiers": [
            [(10.8, 54.0), (13.4, 52.5), (12.0, 50.0), (16.5, 48.0), (13.8, 45.6)],
        ],
        "banners": [
            (3.0, 47.0, "WESTERN EUROPE / EC"),
            (25.0, 51.0, "EASTERN BLOC (1989)"),
        ],
        "cities": [
            (13.4, 52.5, "BERLIN (1989)"),
            (12.5, 41.9, "ROME"),
            (4.4, 50.8, "BRUSSELS"),
            (14.4, 50.1, "PRAGUE"),
            (21.0, 52.2, "WARSAW"),
        ],
        "battles": [
            (13.4, 52.5, "BERLIN WALL FALLS"),
            (18.6, 54.4, "GDANSK"),
        ],
    },
]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    wiki_titles = load_wiki_titles()
    print(f"Loaded {len(wiki_titles)} Wikipedia titles from titles.0.idx")

    assert len(ERAS) == 20, f"Expected 20 eras, got {len(ERAS)}"

    # Verify all 240 wikiTitle strings exist in titles.0.idx!
    for era in ERAS:
        for group_key in ("powers", "events", "thinkers"):
            items = era[group_key]
            assert len(items) == 4, f"{era['year']} {group_key} must have 4 items"
            for name, detail, wtitle in items:
                assert wtitle in wiki_titles, f"Missing wikiTitle in titles.0.idx: {wtitle!r}"
                assert len(name.encode("utf-8")) < 36, f"name too long: {name}"
                assert len(wtitle.encode("utf-8")) < 48, f"wtitle too long: {wtitle}"
        assert len(era["year"].encode("utf-8")) < 24

    # Pack Header: 16 bytes
    # char magic[8] = "CNAT0001", uint16_t eraCount = 20, uint16_t mapW = 440, uint16_t mapH = 240, uint16_t reserved = 0
    out_bytes = bytearray()
    out_bytes += struct.pack("<8sHHHH", b"CNAT0001", len(ERAS), MAP_W, MAP_H, 0)
    assert len(out_bytes) == 16

    preview_indices = [0, 3, 7, 10, 14, 16, 19]
    for idx, era in enumerate(ERAS):
        rec = bytearray()
        rec += pack_utf8(era["year"], 24)
        rec += pack_utf8(era["title"], 48)
        rec += pack_utf8(era["subtitle"], 64)
        rec += pack_utf8(era["overview"], 640)
        for group_key in ("powers", "events", "thinkers"):
            for name, detail, wtitle in era[group_key]:
                rec += pack_utf8(name, 36)
                rec += pack_utf8(detail, 96)
                rec += pack_utf8(wtitle, 48)
        bmp_bytes, img = render_era_map(era)
        assert len(bmp_bytes) == 13200
        rec += bmp_bytes
        assert len(rec) == 16136, f"Unexpected record size {len(rec)}"
        out_bytes += rec

        if idx in preview_indices:
            # Invert for standard PNG viewing (black ink = 0, white bg = 255)
            preview = img.point(lambda p: 0 if p else 255, mode="L")
            preview_path = f"/tmp/atlas_preview_{idx:02d}_{era['year'].replace(' ', '_')}.png"
            preview.save(preview_path)
            print(f"Saved preview: {preview_path}")

    with open(OUT_PATH, "wb") as f:
        f.write(out_bytes)

    print(f"Successfully wrote {OUT_PATH}: {len(out_bytes)} bytes ({len(ERAS)} eras x 16136 + 16 header)")

if __name__ == "__main__":
    main()
