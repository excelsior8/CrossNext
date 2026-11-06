#!/usr/bin/env python3
import os
import struct
import math
from PIL import Image, ImageDraw, ImageFont

WV_IDX_PATH = "./sd_out"
OUT_DIR = "./sd_out"
OUT_PATH = os.path.join(OUT_DIR, "cities.bin")

MAP_W = 440
MAP_H = 240

def load_wv_titles():
    with open(WV_IDX_PATH, "rb") as f:
        b = f.read()
    num_pages = int.from_bytes(b[12:16], "little")
    titles = set()
    for p in range(num_pages):
        page_start = 32 + p * 4096
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
        while words and len(" ".join(words).encode("utf-8")) >= size:
            words.pop()
        s = " ".join(words) if words else ""
        raw = s.encode("utf-8")[:size - 1].decode("utf-8", errors="ignore").encode("utf-8")
    assert len(raw) <= size - 1
    return raw + b"\x00" * (size - len(raw))

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
            (cx + 6, cy - th // 2),
            (cx - tw - 6, cy - th // 2),
            (cx - tw // 2, cy - th - 6),
            (cx - tw // 2, cy + 6),
            (cx + 6, cy - th - 5),
            (cx + 6, cy + 5),
            (cx - tw - 6, cy - th - 5),
            (cx - tw - 6, cy + 5),
            (cx - tw // 2, cy - th - 14),
            (cx - tw // 2, cy + 14),
            (cx + 10, cy - th - 10),
            (cx - tw - 10, cy + 10),
        ]
    best = None
    best_pen = 1e9
    for x0, y0 in candidates:
        x0 = max(6, min(MAP_W - tw - 6, x0))
        y0 = max(20, min(MAP_H - th - 22, y0))
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

def render_city_map(city_def):
    # PIL '1' mode: 0 = white background, 1 = black ink
    img = Image.new("1", (MAP_W, MAP_H), 0)
    pix = img.load()
    draw = ImageDraw.Draw(img)

    # 1. Subtle urban grid background (light street blocks)
    for y in range(20, MAP_H - 6, 22):
        for x in range(6, MAP_W - 6, 4):
            pix[x, y] = 1
    for x in range(24, MAP_W - 6, 28):
        for y in range(20, MAP_H - 6, 4):
            pix[x, y] = 1

    # 2. Water polygons (sea / bay / lake / wide lagoon) with stipple & 2px shore
    water_mask = Image.new("1", (MAP_W, MAP_H), 0)
    wdraw = ImageDraw.Draw(water_mask)
    for wpoly in city_def.get("water_polys", []):
        wdraw.polygon(wpoly, fill=1)
    wpix = water_mask.load()
    for y in range(MAP_H):
        for x in range(MAP_W):
            if wpix[x, y]:
                pix[x, y] = 1 if ((x % 4 == 0 and y % 4 == 0) or (x % 4 == 2 and y % 4 == 2)) else 0
    for wpoly in city_def.get("water_polys", []):
        draw.line(wpoly + [wpoly[0]], fill=1, width=2)

    # 3. Shaded district zones (clipped outside water)
    for idx, dzone in enumerate(city_def.get("district_zones", [])):
        zmask = Image.new("1", (MAP_W, MAP_H), 0)
        zdraw = ImageDraw.Draw(zmask)
        zdraw.polygon(dzone["poly"], fill=1)
        zpix = zmask.load()
        style = idx % 3
        for y in range(MAP_H):
            for x in range(MAP_W):
                if zpix[x, y] and not wpix[x, y]:
                    if style == 0 and (x + y) % 5 == 0:
                        pix[x, y] = 1
                    elif style == 1 and (x - y) % 5 == 0:
                        pix[x, y] = 1
                    elif style == 2 and (x % 4 == 0 and y % 4 == 0):
                        pix[x, y] = 1
        # Dashed district boundary
        pts = dzone["poly"]
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            dist = max(1, int(math.hypot(x1 - x0, y1 - y0)))
            for s in range(0, dist, 4):
                px = int(x0 + (x1 - x0) * s / dist)
                py = int(y0 + (y1 - y0) * s / dist)
                if 3 <= px < MAP_W - 3 and 3 <= py < MAP_H - 3:
                    pix[px, py] = 1

    # 4. Rivers / Canals (double-banked water channel with stipple interior and bridges)
    for rline, width in city_def.get("rivers", []):
        draw.line(rline, fill=1, width=width + 4)
        draw.line(rline, fill=0, width=width)
        # centerline flow dots
        for i in range(len(rline) - 1):
            x0, y0 = rline[i]
            x1, y1 = rline[i + 1]
            dist = max(1, int(math.hypot(x1 - x0, y1 - y0)))
            for s in range(0, dist, 5):
                px = int(x0 + (x1 - x0) * s / dist)
                py = int(y0 + (y1 - y0) * s / dist)
                if 0 <= px < MAP_W and 0 <= py < MAP_H:
                    pix[px, py] = 1
                # Add schematic bridges every ~45px
                if s > 10 and s % 45 == 0:
                    dx = -(y1 - y0) / dist
                    dy = (x1 - x0) / dist
                    bx0, by0 = int(px - dx * (width // 2 + 3)), int(py - dy * (width // 2 + 3))
                    bx1, by1 = int(px + dx * (width // 2 + 3)), int(py + dy * (width // 2 + 3))
                    draw.line([(bx0, by0), (bx1, by1)], fill=1, width=2)

    # 5. Main Avenues, Ring Roads & Rail Lines
    for ave in city_def.get("avenues", []):
        draw.line(ave, fill=1, width=2)
    for rail in city_def.get("rails", []):
        draw.line(rail, fill=1, width=1)
        for i in range(len(rail) - 1):
            x0, y0 = rail[i]
            x1, y1 = rail[i + 1]
            dist = max(1, int(math.hypot(x1 - x0, y1 - y0)))
            for s in range(0, dist, 6):
                px = int(x0 + (x1 - x0) * s / dist)
                py = int(y0 + (y1 - y0) * s / dist)
                dx = -(y1 - y0) / dist
                dy = (x1 - x0) / dist
                draw.line([(int(px - dx * 2), int(py - dy * 2)), (int(px + dx * 2), int(py + dy * 2))], fill=1, width=1)

    placed_boxes = [
        (0, 0, 270, 20),                 # Top-left cartouche
        (0, MAP_H - 36, 44, MAP_H),      # Bottom-left compass
        (MAP_W - 115, MAP_H - 24, MAP_W, MAP_H), # Bottom-right scale bar
    ]
    for px, py, _ in city_def.get("pois", []):
        placed_boxes.append((px - 4, py - 4, px + 4, py + 4))

    # 6. District Boxes (centered boxed banner labels)
    for dx, dy, dname in city_def.get("district_boxes", []):
        bbox = draw.textbbox((0, 0), dname, font=FONT_SM)
        tw = bbox[2] - bbox[0] + 6
        th = bbox[3] - bbox[1] + 4
        x0, y0 = find_free_box(dx, dy, tw, th, placed_boxes, centered=True)
        draw.rectangle([x0, y0, x0 + tw, y0 + th], fill=0, outline=1)
        draw.text((x0 + 3, y0 + 1), dname, fill=1, font=FONT_SM)

    # 7. Labeled POI Markers ([■] icon + halo text)
    for px, py, pname in city_def.get("pois", []):
        draw.rectangle([px - 4, py - 4, px + 4, py + 4], fill=0, outline=1)
        draw.rectangle([px - 2, py - 2, px + 2, py + 2], fill=1)
        label = f"[■] {pname}"
        bbox = draw.textbbox((0, 0), label, font=FONT_SM)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        lx, ly = find_free_box(px, py, tw, th, placed_boxes, centered=False)
        draw.rectangle([lx - 1, ly - 1, lx + tw + 1, ly + th + 1], fill=0)
        draw.text((lx, ly), label, fill=1, font=FONT_SM)

    # 8. Top-left Cartouche Header Box
    cartouche = f" {city_def['map_title']} | {city_def['year']} "
    bbox = draw.textbbox((0, 0), cartouche, font=FONT_MD)
    cw = bbox[2] - bbox[0] + 6
    ch = bbox[3] - bbox[1] + 4
    draw.rectangle([3, 3, 3 + cw, 3 + ch], fill=0, outline=1)
    draw.rectangle([4, 4, 2 + cw, 2 + ch], outline=1)
    draw.text((6, 4), cartouche, fill=1, font=FONT_MD)

    # 9. Bottom-left North Arrow & Compass Rose
    rx, ry = 20, MAP_H - 20
    draw.ellipse([rx - 12, ry - 12, rx + 12, ry + 12], fill=0, outline=1)
    draw.line([rx, ry - 10, rx, ry + 10], fill=1, width=1)
    draw.line([rx - 10, ry, rx + 10, ry], fill=1, width=1)
    draw.polygon([(rx, ry - 10), (rx - 3, ry - 2), (rx + 3, ry - 2)], fill=1)
    draw.rectangle([rx - 4, ry - 19, rx + 5, ry - 11], fill=0)
    draw.text((rx - 3, ry - 19), "N", fill=1, font=FONT_SM)

    # 10. Bottom-right Scale Bar
    sx0, sy0 = MAP_W - 108, MAP_H - 18
    draw.rectangle([sx0 - 4, sy0 - 4, MAP_W - 5, MAP_H - 4], fill=0, outline=1)
    draw.line([sx0, sy0 + 6, sx0 + 48, sy0 + 6], fill=1, width=2)
    draw.line([sx0, sy0 + 2, sx0, sy0 + 8], fill=1, width=1)
    draw.line([sx0 + 24, sy0 + 3, sx0 + 24, sy0 + 8], fill=1, width=1)
    draw.line([sx0 + 48, sy0 + 2, sx0 + 48, sy0 + 8], fill=1, width=1)
    draw.text((sx0 + 53, sy0 - 1), city_def.get("scale", "1 km"), fill=1, font=FONT_SM)

    # 11. Double Outer Frame
    draw.rectangle([0, 0, MAP_W - 1, MAP_H - 1], outline=1)
    draw.rectangle([2, 2, MAP_W - 3, MAP_H - 3], outline=1)

    # Pack 440x240 1-bit MSB-first (55 bytes/row * 240 rows = 13,200 bytes)
    buf = bytearray(MAP_W * MAP_H // 8)
    for y in range(MAP_H):
        row_off = y * (MAP_W // 8)
        for x in range(MAP_W):
            if pix[x, y]:
                buf[row_off + (x >> 3)] |= (0x80 >> (x & 7))
    return bytes(buf), img


CITIES = [
    # 1. TORINO
    {
        "year": "ITALY • PIEDMONT",
        "map_title": "TORINO (TURIN)",
        "title": "TORINO: ROYAL SAVOY CAPITAL & PO RIVER",
        "subtitle": "Barok bulvarlar, 18 km portikolar, Po nehri ve Politecnico",
        "overview": (
            "Alplerin eteğinde Po ve Dora Riparia nehirlerinin birleştiği noktada kurulan Torino, İtalya Krallığı'nın "
            "ilk başkenti (1861) ve Savoy Hanedanı'nın barok mücevheridir. Roma döneminden (Augusta Taurinorum) kalan "
            "dik açılı ızgara sokakları, yağmurda bile şehri boydan boya yürümeyi sağlayan 18 kilometrelik kemerli "
            "portikoları (portici), tarihi kafeleri (bicerin ve gianduiotto geleneği) ve Politecnico di Torino ile "
            "hem mühendislik/endüstri hem de entelektüel kültür başkentidir."
        ),
        "powers": [
            ("Centro & Piazza Castello", "Kraliyet Sarayı, Palazzo Madama ve Via Roma/Via Po portikolarının kalbi.", "Turin"),
            ("Quadrilatero Romano", "Roma surları üzerine kurulu dar sokaklar, Porte Palatine ve akşam apericena bölgesi.", "Turin"),
            ("San Salvario & Valentino", "Po kıyısındaki Parco del Valentino, Ortaçağ Köyü ve çok kültürlü öğrenci mahallesi.", "Turin"),
            ("Crocetta & Cit Turin", "Politecnico di Torino kampüsü ve Art Nouveau (Liberty) mimarisiyle ünlü zarif semt.", "Turin"),
        ],
        "events": [
            ("Mole Antonelliana", "167,5 m yüksekliğindeki simge kule ve Ulusal Sinema Müzesi; panoramik Alp manzarası.", "Turin"),
            ("Museo Egizio", "Kahire'den sonra dünyanın en zengin Mısır arkeoloji koleksiyonu (Via Accademia delle Scienze).", "Turin"),
            ("Palazzo Reale & Cappella", "Savoy Kraliyet Sarayı, Kraliyet Cephaneliği ve Guarini'nin Kutsal Kefen Şapeli.", "Turin"),
            ("Monte dei Cappuccini & Superga", "Po nehrinin karşı kıyısından şehir ve Alp silüetini gören en iyi bakış noktaları.", "Turin"),
        ],
        "thinkers": [
            ("Bicerin & Gianduiotto", "Al Bicerin (1763): sıcak çikolata, espresso ve süt kreması katmanlı geleneksel Torino içeceği.", "Turin"),
            ("Agnolotti del Plin & Brasato", "Piemonte mutfağının el yapımı et dolgulu makarnası ve Barolo şarabında pişmiş dana eti.", "Piedmont"),
            ("GTT Metro & Tram #7/#15", "Porta Nuova ve Porta Susa garlarını Politecnico ve Lingotto'ya bağlayan otomatik metro.", "Turin"),
            ("Piemonte & Langhe Gezisi", "Trenle 1 saatte Alba, Barolo bağları, Sacra di San Michele ve Aosta Vadisi rotaları.", "Piedmont"),
        ],
        "rivers": [
            ([(300, 235), (310, 175), (325, 115), (350, 55), (380, 15)], 10), # Po River
            ([(20, 65), (140, 62), (255, 68), (345, 60)], 5),                  # Dora Riparia
        ],
        "avenues": [
            [(220, 95), (315, 130)],  # Via Po
            [(220, 95), (210, 185)],  # Via Roma
            [(80, 130), (220, 95)],   # Via Garibaldi
            [(130, 185), (310, 185)], # Corso Vittorio Emanuele II
        ],
        "rails": [
            [(115, 110), (205, 185), (210, 235)], # Porta Susa -> Porta Nuova
        ],
        "district_zones": [
            {"poly": [(165, 75), (285, 75), (305, 145), (175, 155)]},
            {"poly": [(215, 155), (305, 155), (295, 225), (215, 225)]},
        ],
        "district_boxes": [
            (175, 65, "QUADRILATERO"),
            (255, 195, "SAN SALVARIO"),
            (95, 195, "POLITECNICO"),
        ],
        "pois": [
            (225, 100, "P.CASTELLO"),
            (278, 110, "MOLE ANTONELLIANA"),
            (215, 128, "MUSEO EGIZIO"),
            (205, 178, "PORTA NUOVA"),
            (300, 190, "PARCO VALENTINO"),
        ],
    },
    # 2. ROMA
    {
        "year": "ITALY • LAZIO",
        "map_title": "ROMA (ROME)",
        "title": "ROMA: THE ETERNAL CITY & TIBER CURVE",
        "subtitle": "Yedi tepe, Kolezyum, Forum, Pantheon, Vatikan ve Trastevere",
        "overview": (
            "Tiber (Tevere) nehrinin kıvrımları ve Yedi Tepe üzerine kurulu Roma, 2.800 yıllık kesintisiz kentsel "
            "katmanlarıyla antik imparatorluk forumlarını, Rönesans saraylarını, Bernini ile Borromini'nin barok "
            "meydanlarını ve Vatikan'ı tek bir açık hava müzesinde birleştirir. Centro Storico'nun arnavut kaldırımlı "
            "sokakları, Pantheon'un 43 metrelik kubbesi ve Trastevere'nin akşam trattoria kültürü yürüyerek keşfedilir."
        ),
        "powers": [
            ("Centro Storico", "Pantheon, Piazza Navona, Campo de' Fiori ve Trevi Çeşmesi arasındaki tarihi yaya kalbi.", "Rome"),
            ("Monti & Antik Roma", "Kolezyum, Roma Forumu ve Palatino Tepesi'nin hemen kuzeyindeki bohem zanaatkar semti.", "Rome"),
            ("Trastevere & Gianicolo", "Tiber'in batı yakasında Santa Maria in Trastevere ve panoramik Gianicolo tepesi.", "Rome"),
            ("Vaticano & Prati", "Aziz Petrus Bazilikası, Vatikan Müzeleri ve Castel Sant'Angelo çevresi.", "Vatican City"),
        ],
        "events": [
            ("Colosseo & Foro Romano", "MS 80'de tamamlanan Flavianus Amfitiyatrosu, Via Sacra ve Palatino saray kalıntıları.", "Rome"),
            ("Pantheon (Rotonda)", "Hadrianus döneminden kalan, dünyanın en büyük donatısız beton kubbeli antik tapınağı.", "Rome"),
            ("Basilica di San Pietro", "Michelangelo'nun kubbesi, Pietà heykeli ve Sistina Şapeli freskleri.", "Vatican City"),
            ("Galleria Borghese", "Bernini'nin Apollon ve Dafne ile Davut heykellerini barındıran Villa Borghese müzesi.", "Rome"),
        ],
        "thinkers": [
            ("Carbonara, Cacio e Pepe, Amatriciana", "Guanciale, Pecorino Romano ve karabiber üçlüsüne dayanan klasik Roma makarnaları.", "Rome"),
            ("Supplì & Carciofi alla Giudia", "Kızarmış pirinç/mozzarella topları ve Yahudi Mahallesi'nin (Ghetto) çıtır enginarı.", "Rome"),
            ("Metro A/B & Termini", "Roma Termini ana garından Kolezyum (Metro B) ve Vatikan/Ottaviano (Metro A) bağlantısı.", "Rome"),
            ("Ostia Antica & Tivoli", "Banliyö treniyle 30 dakikada antik liman kenti Ostia ve Hadrianus Villası (Villa Adriana).", "Tivoli"),
        ],
        "rivers": [
            ([(215, 15), (195, 70), (145, 105), (175, 145), (160, 195), (135, 235)], 10), # Tiber
        ],
        "avenues": [
            [(220, 55), (225, 135)],  # Via del Corso
            [(225, 135), (285, 165)], # Via dei Fori Imperiali
            [(85, 95), (150, 95)],    # Via della Conciliazione
        ],
        "rails": [
            [(340, 110), (420, 140)], # Termini rail
        ],
        "district_zones": [
            {"poly": [(165, 75), (255, 75), (255, 145), (165, 145)]},
            {"poly": [(85, 150), (165, 150), (160, 220), (85, 220)]},
        ],
        "district_boxes": [
            (115, 190, "TRASTEVERE"),
            (295, 125, "MONTI"),
            (255, 42, "VILLA BORGHESE"),
        ],
        "pois": [
            (78, 95, "VATICANO"),
            (205, 112, "PANTHEON"),
            (288, 168, "COLOSSEO"),
            (248, 158, "FORO ROMANO"),
            (335, 105, "TERMINI"),
        ],
    },
    # 3. FIRENZE
    {
        "year": "ITALY • TUSCANY",
        "map_title": "FIRENZE (FLORENCE)",
        "title": "FIRENZE: CRADLE OF THE RENAISSANCE & ARNO",
        "subtitle": "Brunelleschi Kubbesi, Uffizi, Ponte Vecchio ve Oltrarno atölyeleri",
        "overview": (
            "Arno nehrinin iki yakasında kurulan Floransa, 14. ve 15. yüzyıllarda Medici ailesi, loncalar, Dante, "
            "Brunelleschi, Leonardo ve Michelangelo ile İtalyan Rönesansı'nın doğduğu şehirdir. Kuzey yakasında "
            "Santa Maria del Fiore (Duomo), Piazza della Signoria ve Uffizi yükselirken, Ponte Vecchio köprüsüyle "
            "geçilen güney yakası (Oltrarno) Palazzo Pitti, Boboli Bahçeleri ve zanaatkar atölyeleriyle ünlüdür."
        ),
        "powers": [
            ("Piazza del Duomo & Centro", "Brunelleschi'nin kubbesi, Giotto'nun Çan Kulesi ve Vaftizhane'nin mermer merkezi.", "Florence"),
            ("Piazza della Signoria", "Palazzo Vecchio, Loggia dei Lanzi heykelleri ve Uffizi Galerisi koridoru.", "Florence"),
            ("Oltrarno & Santo Spirito", "Arno'nun güney yakasında Pitti Sarayı, Boboli Bahçeleri ve otantik trattoria meydanı.", "Florence"),
            ("Santa Croce & San Lorenzo", "Michelangelo, Galileo ve Machiavelli'nin mezarları ile Medici Şapelleri ve Mercato Centrale.", "Florence"),
        ],
        "events": [
            ("Galleria degli Uffizi", "Botticelli'nin Venüs'ün Doğuşu ve İlkbahar tabloları ile Rönesans başyapıtları.", "Florence"),
            ("Galleria dell'Accademia", "Michelangelo'nun 5,17 metrelik orijinal mermer Davut (David) heykeli ve Tutsaklar serisi.", "Florence"),
            ("Ponte Vecchio", "1345'ten kalan, üstünden Vasari Koridoru geçen tarihi kuyumcular köprüsü.", "Florence"),
            ("Piazzale Michelangelo", "Güney tepesinden gün batımında tüm Floransa kubbelerini ve Arno köprülerini gören teras.", "Florence"),
        ],
        "thinkers": [
            ("Bistecca alla Fiorentina & Lampredotto", "Chianina sığırından T-bone biftek ve sokak tezgahlarının geleneksel sandviçi.", "Florence"),
            ("Ribollita, Pappa al Pomodoro & Chianti", "Toskana'nın ekmekli sebze çorbası ve Chianti Classico şarap geleneği.", "Chianti"),
            ("Santa Maria Novella (SMN)", "Tarihi merkeze 5 dakika yürüme mesafesindeki ana yüksek hızlı tren garı.", "Florence"),
            ("Siena, Pisa & San Gimignano", "Floransa'dan günübirlik tren/otobüsle ulaşılabilen Ortaçağ Toskana şehirleri.", "Tuscany"),
        ],
        "rivers": [
            ([(10, 130), (140, 140), (260, 148), (430, 160)], 11), # Arno River
        ],
        "avenues": [
            [(220, 75), (220, 145)],  # Via dei Calzaiuoli -> Ponte Vecchio
            [(135, 65), (220, 75), (310, 125)],
        ],
        "rails": [
            [(40, 50), (135, 65)],    # SMN Station approach
        ],
        "district_zones": [
            {"poly": [(140, 45), (315, 45), (315, 138), (140, 132)]},
            {"poly": [(130, 152), (320, 158), (320, 225), (130, 225)]},
        ],
        "district_boxes": [
            (180, 185, "OLTRARNO"),
            (315, 115, "SANTA CROCE"),
        ],
        "pois": [
            (225, 75, "DUOMO"),
            (225, 122, "UFFIZI & SIGNORIA"),
            (215, 146, "PONTE VECCHIO"),
            (195, 175, "PALAZZO PITTI"),
            (335, 198, "P.MICHELANGELO"),
        ],
    },
    # 4. VENEZIA
    {
        "year": "ITALY • VENETO",
        "map_title": "VENEZIA (VENICE)",
        "title": "VENEZIA: LA SERENISSIMA & GRAND CANAL",
        "subtitle": "118 ada, ters S biçimli Canal Grande, San Marco ve 6 Sestieri",
        "overview": (
            "Adriyatik lagününde 118 adacık ve milyonlarca ahşap kazık üzerine kurulan Venedik (La Serenissima), "
            "bin yıl boyunca Akdeniz ve Doğu ticaretinin deniz cumhuriyetiydi. Otomobilin olmadığı şehirde ulaşım "
            "ters 'S' çizen Canal Grande üzerindeki vaporetto hatları, traghetto kayıkları ve 400'den fazla köprüyle "
            "birbirine bağlanan dar calle sokakları ve campo meydanları üzerinden sağlanır."
        ),
        "powers": [
            ("San Marco & Castello", "San Marco Bazilikası, Dükler Sarayı (Palazzo Ducale), Arsenale tersanesi ve Bienal bahçeleri.", "Venice"),
            ("San Polo & Rialto", "Rialto Köprüsü, sabah balık/sebze pazarı (Mercato di Rialto) ve Frari Bazilikası.", "Venice"),
            ("Dorsoduro", "Gallerie dell'Accademia, Peggy Guggenheim Koleksiyonu, Salute Bazilikası ve öğrenci meydanları.", "Venice"),
            ("Cannaregio", "Tarihi Yahudi Gettosu (1516), sakin kanallar ve yerlilerin akşam cicchetti barları (Fondamenta).", "Venice"),
        ],
        "events": [
            ("Piazza & Basilica di San Marco", "Bizans altın mozaikleri, Çan Kulesi (Campanile) ve Palazzo Ducale ile Ahlar Köprüsü.", "Venice"),
            ("Ponte di Rialto & Canal Grande", "Vaporetto Hat 1 ile Santa Lucia garından San Marco'ya saray cepheleri boyunca geçiş.", "Venice"),
            ("Gallerie dell'Accademia", "Bellini, Giorgione, Tiziano, Tintoretto ve Veronese ile Venedik resim okulunun zirvesi.", "Venice"),
            ("Murano, Burano & Torcello", "Lagün vapuruyla cam atölyeleri adası Murano, renkli evleriyle Burano ve 7. yy Torcello.", "Venice"),
        ],
        "thinkers": [
            ("Cicchetti & Ombra di Vino", "Bacarò şarap barlarında kızarmış deniz ürünleri, baccalà mantecato ve küçük kadeh şarap.", "Venice"),
            ("Risotto al Nero di Seppia & Sarde in Saor", "Mürekkep balıklı siyah risotto ve tatlı-ekşi soğanlı/çam fıstıklı marine sardalya.", "Venice"),
            ("Vaporetto #1 / #2 & Traghetto", "ACTV deniz otobüsleri ve Canal Grande'yi 2 Euro'ya karşıya geçiren gondol-feribotlar.", "Venice"),
            ("Padova, Verona & Dolomitler", "Trenle 30 dakikada Giotto'nun Scrovegni Şapeli (Padova) ve Verona Arenası.", "Veneto"),
        ],
        "water_polys": [
            [(3, 3), (436, 3), (436, 236), (3, 236)], # Lagoon background
        ],
        "district_zones": [
            {"poly": [(85, 45), (345, 50), (385, 130), (285, 165), (110, 155), (75, 100)]}, # Main islands
            {"poly": [(115, 185), (330, 185), (320, 215), (115, 210)]},                     # Giudecca
        ],
        "rivers": [
            ([(115, 80), (195, 68), (235, 100), (190, 135), (255, 152)], 10), # Grand Canal S-curve
        ],
        "rails": [
            [(5, 78), (95, 78)], # Ponte della Libertà causeway
        ],
        "district_boxes": [
            (185, 52, "CANNAREGIO"),
            (155, 152, "DORSODURO"),
            (225, 198, "GIUDECCA"),
        ],
        "pois": [
            (105, 82, "S.LUCIA"),
            (225, 98, "PONTE RIALTO"),
            (285, 138, "SAN MARCO"),
            (205, 145, "ACCADEMIA"),
            (360, 120, "ARSENALE"),
        ],
    },
    # 5. MILANO
    {
        "year": "ITALY • LOMBARDY",
        "map_title": "MILANO (MILAN)",
        "title": "MILANO: DUOMO, NAVIGLI CANALS & DESIGN",
        "subtitle": "Gotik katedral, Sforza Kalesi, Leonardo'nun Son Akşam Yemeği ve Navigli",
        "overview": (
            "Lombardiya Ovası'nın kalbindeki Milano, İtalya'nın finans, endüstriyel tasarım, mimarlık ve moda "
            "başkentidir. Eşmerkezli halkalar halinde büyüyen şehirde mermer Duomo ve Galleria Vittorio Emanuele II "
            "tarihi çekirdeği oluştururken, Brera sanat galerileri, Leonardo da Vinci'nin tasarladığı Navigli "
            "kanalları ve Porta Nuova'nın Bosco Verticale gökdelenleri geçmiş ile geleceği birleştirir."
        ),
        "powers": [
            ("Centro & Piazza del Duomo", "Duomo, Galleria Vittorio Emanuele II, La Scala Operası ve Quadrilatero della Moda.", "Milan"),
            ("Brera & Castello Sforzesco", "Pinacoteca di Brera, Sforza Kalesi, Parco Sempione ve tarihi ressam sokakları.", "Milan"),
            ("Navigli & Porta Ticinese", "Naviglio Grande ve Pavese kanalları, Sant'Eustorgio ve akşam aperitivo rıhtımları.", "Milan"),
            ("Porta Nuova & Isola", "Piazza Gae Aulenti, Bosco Verticale (Dikey Orman) ve çağdaş mimari bölgesi.", "Milan"),
        ],
        "events": [
            ("Duomo di Milano", "600 yılda tamamlanan, 135 mermer kulesi ve çatı teraslarıyla dünyanın en büyük Gotik katedrali.", "Milan"),
            ("Cenacolo Vinciano (Last Supper)", "Santa Maria delle Grazie manastırında Leonardo da Vinci'nin Son Akşam Yemeği duvar resmi.", "Milan"),
            ("Pinacoteca di Brera & Sforza", "Mantegna, Raffaello ve Caravaggio tabloları ile Michelangelo'nun Rondanini Pietà'sı.", "Milan"),
            ("Fondazione Prada & Museo del 900", "20. yüzyıl İtalyan fütürizmi ve Rem Koolhaas tasarımlı çağdaş sanat yerleşkesi.", "Milan"),
        ],
        "thinkers": [
            ("Risotto alla Milanese & Cotoletta", "Safranlı kemik iliği risottosu (ossobuco ile) ve kemikli dana şnitzeli.", "Milan"),
            ("Panettone & Negroni Sbagliato", "Milano'nun geleneksel Noel çöreği ve Bar Basso'da doğan köpüklü aperitivo klasiği.", "Milan"),
            ("MM1–MM5 Metro & Tarihi Tramvaylar", "1928 model turuncu Carrelli tramvayları (Hat 1) ve Linate/Centrale metro ağı.", "Milan"),
            ("Como Gölü & Bergamo Città Alta", "Trenle 40 dakikada Como Gölü (Varenna, Bellagio) ve Venedik surlu Bergamo.", "Como"),
        ],
        "rivers": [
            ([(35, 195), (185, 175)], 6),  # Naviglio Grande
            ([(185, 175), (205, 235)], 6), # Naviglio Pavese
        ],
        "avenues": [
            [(145, 70), (295, 70), (335, 130), (285, 185), (155, 185), (115, 130), (145, 70)], # Cerchia
            [(180, 95), (235, 125)],
        ],
        "rails": [
            [(265, 25), (305, 45)], # Milano Centrale
        ],
        "district_zones": [
            {"poly": [(145, 70), (295, 70), (320, 130), (285, 175), (155, 175), (125, 130)]},
        ],
        "district_boxes": [
            (225, 78, "BRERA"),
            (115, 198, "NAVIGLI"),
            (255, 35, "PORTA NUOVA"),
        ],
        "pois": [
            (235, 128, "DUOMO & SCALA"),
            (175, 98, "CASTELLO SFORZESCO"),
            (115, 128, "CENACOLO (LAST SUPPER)"),
            (185, 175, "DARSENA"),
            (295, 42, "CENTRALE"),
        ],
    },
    # 6. NAPOLI
    {
        "year": "ITALY • CAMPANIA",
        "map_title": "NAPOLI & POMPEII",
        "title": "NAPOLI: BAY OF NAPLES, VESUVIUS & POMPEII",
        "subtitle": "Spaccanapoli, Vezüv Yanardağı, Pompeii kalıntıları ve Amalfi kıyısı",
        "overview": (
            "Vezüv Yanardağı'nın gölgesinde ve Tiren Denizi'nin en dramatik körfezinde yükselen Napoli, MÖ 8. yüzyılda "
            "Yunan kolonisi Neapolis olarak kurulmuş, Avrupa'nın en yoğun ve canlı tarihi merkezlerinden biridir. "
            "Eski şehri jilet gibi ikiye bölen Spaccanapoli caddesi, yeraltı tünelleri, eşsiz Arkeoloji Müzesi ve "
            "hemen güneyindeki Pompeii, Herculaneum, Capri ve Amalfi Kıyısı ile eşsiz bir coğrafyadır."
        ),
        "powers": [
            ("Centro Storico & Spaccanapoli", "Greko-Romen ızgara planlı Decumani caddeleri, San Gregorio Armeno ve Duomo.", "Naples"),
            ("Quartieri Spagnoli & Toledo", "Via Toledo, Galleria Umberto I ve dik yamaçlı tarihi İspanyol Mahallesi.", "Naples"),
            ("Lungomare & Chiaia", "Castel dell'Ovo, Piazza del Plebiscito, Kraliyet Sarayı ve deniz kıyısı kordonu.", "Naples"),
            ("Vomero & Posillipo", "Castel Sant'Elmo ve Certosa di San Martino'dan tüm Napoli Körfezi ve Vezüv manzarası.", "Naples"),
        ],
        "events": [
            ("Museo Archeologico Nazionale (MANN)", "Pompeii ve Herculaneum'dan çıkarılan Büyük İskender Mozaiği ve Farnese heykelleri.", "Naples"),
            ("Cappella Sansevero", "Giuseppe Sanmartino'nun mermeri tül gibi işlediği Örtülü İsa (Cristo Velato) heykeli.", "Naples"),
            ("Pompeii & Herculaneum", "MS 79 Vezüv patlamasıyla küller altında donmuş antik Roma kentleri (Circumvesuviana ile 35 dk).", "Pompeii"),
            ("Napoli Sotterranea", "Şehrin 40 metre altındaki Yunan-Roma su sarnıçları, tüneller ve II. Dünya Savaşı sığınakları.", "Naples"),
        ],
        "thinkers": [
            ("Pizza Napoletana (Margherita & Marinara)", "San Marzano domatesi, fior di latte/bufala mozzarella ve odun fırınında 90 saniye.", "Naples"),
            ("Sfogliatella, Babà & Caffè Sospeso", "Kıvrımlı çıtır ricotta tatlısı, romlu babà ve 'askıda kahve' geleneği.", "Naples"),
            ("Metro Linea 1 (Toledo) & Funiküler", "Avrupa'nın en güzel metro istasyonu seçilen Toledo ve Vomero füniküler hatları.", "Naples"),
            ("Costiera Amalfitana & Capri", "Sorrento, Positano, Amalfi, Ravello ve vapurla Capri Adası rotası.", "Amalfi Coast"),
        ],
        "water_polys": [
            [(20, 155), (160, 150), (265, 130), (335, 165), (435, 225), (435, 236), (20, 236)], # Bay of Naples
        ],
        "avenues": [
            [(145, 95), (275, 85)],  # Spaccanapoli
            [(155, 85), (155, 145)], # Via Toledo
            [(275, 105), (385, 175)], # Coastal road to Pompeii
        ],
        "rails": [
            [(265, 95), (395, 175)], # Circumvesuviana
        ],
        "district_zones": [
            {"poly": [(140, 65), (275, 65), (275, 125), (140, 135)]},
        ],
        "district_boxes": [
            (95, 95, "VOMERO"),
            (205, 65, "SPACCANAPOLI"),
        ],
        "pois": [
            (205, 72, "MUSEO ARCHEOLOGICO"),
            (155, 145, "PLEBISCITO & OVO"),
            (355, 120, "MT. VESUVIUS"),
            (390, 175, "POMPEII"),
        ],
    },
    # 7. BOLOGNA
    {
        "year": "ITALY • EMILIA-ROMAGNA",
        "map_title": "BOLOGNA",
        "title": "BOLOGNA: LA DOTTA, LA GRASSA, LA ROSSA",
        "subtitle": "Dünyanın en eski üniversitesi (1088), 40 km portiko ve kızıl kuleler",
        "overview": (
            "'La Dotta' (Bilgin — 1088'de kurulan Batı dünyasının en eski üniversitesi), 'La Grassa' (Zengin Mutfaklı — "
            "İtalyan gastronomisinin başkenti) ve 'La Rossa' (Kızıl — pişmiş toprak çatıları ve sol politik mirası) "
            "lakaplarıyla anılan Bologna, UNESCO listesindeki 40 kilometrelik kemerli portikoları ve Ortaçağ'dan kalan "
            "eğik kuleleriyle Kuzey ve Orta İtalya'nın kavşak noktasıdır."
        ),
        "powers": [
            ("Piazza Maggiore & Quadrilatero", "San Petronio Bazilikası, Neptün Çeşmesi ve Ortaçağ gıda loncalarının dar pazarı.", "Bologna"),
            ("Zona Universitaria (Via Zamboni)", "Alma Mater Studiorum (1088) fakülteleri, öğrenci meydanları ve sanat galerileri.", "Bologna"),
            ("Santo Stefano & Sette Chiese", "Yedi Kilise kompleksi ve üçgen planlı büyüleyici Piazza Santo Stefano.", "Bologna"),
            ("Saragozza & Colle della Guardia", "666 kemerli dünyanın en uzun portikosuyla (3,8 km) San Luca tepesine çıkış.", "Bologna"),
        ],
        "events": [
            ("Le Due Torri (Asinelli & Garisenda)", "12. yüzyıldan kalan 97 metrelik Asinelli Kulesi ve Dante'nin andığı eğik Garisenda.", "Bologna"),
            ("Archiginnasio & Teatro Anatomico", "Üniversitenin 1563 tarihli ana binası ve sedir ağacından oyulmuş Anatomi Tiyatrosu.", "Bologna"),
            ("Basilica di San Petronio", "Dünyanın en büyük tuğla kiliselerinden biri ve Cassini'nin 67 metrelik güneş meridyeni.", "Bologna"),
            ("Santuario di San Luca", "Portico di San Luca altından yürüyerek ulaşılan tepe bazilikası.", "Bologna"),
        ],
        "thinkers": [
            ("Tagliatelle al Ragù, Tortellini in Brodo", "Gerçek Bolonez sosunun (asla spagettiyle değil, yumurtalı tagliatelle ile) anavatanı.", "Bologna"),
            ("Mortadella, Lasagne Verdi & Parmigiano", "Ispanaklı yeşil lazanya, Mortadella Bologna IGP ve 24 aylık Parmigiano Reggiano.", "Emilia-Romagna"),
            ("Bologna Centrale AV", "Milano (1 sa), Floransa (37 dk), Venedik (1,5 sa) ve Roma'yı bağlayan ana hızlı tren kavşağı.", "Bologna"),
            ("Modena, Parma & Ravenna", "Trenle 25–50 dakikada Ravenna Bizans mozaikleri, Parma ve Modena.", "Ravenna"),
        ],
        "avenues": [
            [(130, 55), (295, 55), (345, 120), (295, 190), (130, 190), (85, 120), (130, 55)], # Viali ring
            [(90, 120), (340, 120)],  # Via Emilia (Ugo Bassi / Rizzoli)
            [(235, 120), (305, 75)],  # Via Zamboni
            [(85, 165), (25, 215)],   # Portico di San Luca
        ],
        "rails": [
            [(60, 35), (215, 42), (370, 35)], # Bologna Centrale
        ],
        "district_zones": [
            {"poly": [(130, 55), (295, 55), (345, 120), (295, 190), (130, 190), (85, 120)]},
        ],
        "district_boxes": [
            (285, 78, "UNIVERSITA"),
            (165, 165, "SARAGOZZA"),
        ],
        "pois": [
            (205, 125, "P.MAGGIORE"),
            (240, 118, "DUE TORRI"),
            (255, 152, "SANTO STEFANO"),
            (215, 42, "CENTRALE"),
            (38, 208, "SAN LUCA"),
        ],
    },
    # 8. GENOVA & CINQUE TERRE
    {
        "year": "ITALY • LIGURIA",
        "map_title": "GENOVA & CINQUE TERRE",
        "title": "GENOVA & LIGURIAN RIVIERA (CINQUE TERRE)",
        "subtitle": "Deniz Cumhuriyeti, Caruggi sokakları, Palazzi dei Rolli ve 5 uçurum köyü",
        "overview": (
            "Ligurya Denizi ile Apenin dağları arasına sıkışmış amfitiyatro biçimli Cenova (La Superba), Ortaçağ'da "
            "Venedik'in en büyük deniz rakibiydi. Avrupa'nın en sık dokulu Ortaçağ dar sokak ağı (caruggi), UNESCO "
            "korumasındaki Rönesans sarayları (Palazzi dei Rolli) ve doğusunda sarp kayalıklara tutunmuş Cinque Terre "
            "(Monterosso, Vernazza, Corniglia, Manarola, Riomaggiore) köyleriyle kuzeybatı İtalya'nın kıyı kapısıdır."
        ),
        "powers": [
            ("Centro Storico & Caruggi", "San Lorenzo Katedrali, Palazzo Ducale ve daracık Ortaçağ geçitleri.", "Genoa"),
            ("Porto Antico", "Renzo Piano tarafından dönüştürülen tarihi liman, Akvaryum, Bigo ve Denizcilik Müzesi.", "Genoa"),
            ("Via Garibaldi (Strada Nuova)", "16. yüzyıl Ceneviz banker ailelerinin Palazzo Rosso, Palazzo Bianco ve Palazzo Tursi sarayları.", "Genoa"),
            ("Cinque Terre & Portofino", "Doğu Riviera'da (Riviera di Levante) teraslı bağlar ve yürüyüş patikalarıyla bağlı 5 balıkçı köyü.", "Cinque Terre"),
        ],
        "events": [
            ("Palazzi dei Rolli (Via Garibaldi)", "Ceneviz Cumhuriyeti'nin devlet konuklarını ağırladığı altın çağ sarayları.", "Genoa"),
            ("Acquario di Genova & Galata", "Avrupa'nın en büyük deniz akvaryumu ve gerçek boyutlu Ceneviz kadırgalı Galata Müzesi.", "Genoa"),
            ("Spianata Castelletto", "Art Nouveau asansörle çıkılan, tüm eski şehir çatılarını ve limanı gören panoramik teras.", "Genoa"),
            ("Sentiero Azzurro (Cinque Terre)", "Monterosso'dan Riomaggiore'ye deniz uçurumları boyunca uzanan tarihi kıyı patikası.", "Cinque Terre"),
        ],
        "thinkers": [
            ("Focaccia Genovese & Trofie al Pesto", "Zeytinyağlı sıcak focaccia (sabah cappuccinoya batırılır) ve fesleğen/çam fıstıklı pesto.", "Genoa"),
            ("Farinata di Ceci", "Bakır tepsilerde odun fırınında pişirilen çıtır nohut unu gözlemesi.", "Genoa"),
            ("Trenitalia Cinque Terre Express", "Genova Piazza Principe / Brignole'den Levanto ve 5 köye her 20 dakikada bir sahil treni.", "Cinque Terre"),
            ("Portofino & Camogli", "Cenova'nın hemen doğusunda pastel renkli balıkçı kasabası Camogli ve San Fruttuoso koyu.", "Liguria"),
        ],
        "water_polys": [
            [(3, 125), (125, 115), (245, 140), (355, 175), (436, 195), (436, 236), (3, 236)], # Ligurian Sea
        ],
        "avenues": [
            [(45, 95), (175, 95), (295, 135), (415, 175)], # Coastal Via Aurelia
        ],
        "rails": [
            [(65, 85), (175, 105), (315, 145), (420, 180)], # Genova -> Cinque Terre rail
        ],
        "district_zones": [
            {"poly": [(85, 65), (215, 65), (215, 125), (85, 115)]},
        ],
        "district_boxes": [
            (150, 58, "VIA GARIBALDI"),
            (355, 130, "CINQUE TERRE"),
        ],
        "pois": [
            (115, 108, "PORTO ANTICO"),
            (165, 95, "CARUGGI & DUOMO"),
            (255, 128, "CAMOGLI / PORTOFINO"),
            (345, 155, "VERNAZZA"),
            (395, 172, "RIOMAGGIORE"),
        ],
    },
    # 9. PARIS
    {
        "year": "FRANCE • ILE-DE-FRANCE",
        "map_title": "PARIS",
        "title": "PARIS: SEINE ISLANDS, LOUVRE & RIVE GAUCHE",
        "subtitle": "Seine nehri, Île de la Cité, Haussmann bulvarları, Louvre ve Quartier Latin",
        "overview": (
            "Seine nehrinin iki yakası (Rive Droite ve Rive Gauche) ile nehir ortasındaki Île de la Cité adası "
            "etrafında sarmal 20 bölgeye (arrondissement) ayrılan Paris, Gotik mimarinin, Aydınlanma düşüncesinin "
            "ve 19. yüzyıl Haussmann şehirciliğinin başkentidir. Louvre'dan Zafer Takı'na uzanan tarihi eksen, "
            "Sorbonne çevresindeki entelektüel Sol Yaka ve Montmartre tepesi yürüyerek ve metroyla birbirine bağlanır."
        ),
        "powers": [
            ("Île de la Cité & Le Marais (1–4e)", "Notre-Dame, Sainte-Chapelle, Louvre, Place des Vosges ve tarihi Marais konakları.", "Paris"),
            ("Quartier Latin & Saint-Germain (5–6e)", "Sorbonne Üniversitesi, Panthéon, Jardin du Luxembourg ve varoluşçu edebiyat kafeleri.", "Paris"),
            ("Montmartre & Pigalle (18e)", "Sacré-Cœur Bazilikası, Place du Tertre ressamlar tepesi ve dar taş merdivenler.", "Paris"),
            ("Champs-Élysées & Tour Eiffel (7–8e)", "Eyfel Kulesi, Musée d'Orsay, Invalides, Place de la Concorde ve Arc de Triomphe.", "Paris"),
        ],
        "events": [
            ("Musée du Louvre", "Eski kraliyet sarayında Mona Lisa, Semadirek Kanatlı Zaferi ve Mezopotamya/Mısır koleksiyonları.", "Paris"),
            ("Musée d'Orsay & Orangerie", "Eski tren garında Monet, Van Gogh, Degas, Cézanne ve Empresyonizm başyapıtları.", "Paris"),
            ("Cathédrale Notre-Dame & Sainte-Chapelle", "12. yüzyıl Gotik mimarisi ve Sainte-Chapelle'in 15 metrelik vitray pencereleri.", "Paris"),
            ("Tour Eiffel & Centre Pompidou", "Gustave Eiffel'in 1889 Dünya Fuarı demir kulesi ve modern sanat merkezi.", "Paris"),
        ],
        "thinkers": [
            ("Boulangerie, Bistro & Fromagerie", "Tereyağlı kruvasan, baget, soğan çorbası (soupe à l'oignon), steak frites ve peynir tabakları.", "Paris"),
            ("Café de Flore & Les Deux Magots", "Sartre, Simone de Beauvoir ve Camus'nün yazdığı tarihi Sol Yaka kafeleri.", "Paris"),
            ("RATP Métro & RER (Navigo)", "16 metro hattı ve Gare de Lyon'dan Torino/Milano'ya doğrudan hızlı tren (TGV/Frecciarossa).", "Paris"),
            ("Versailles & Giverny", "RER C treniyle 35 dakikada Versay Sarayı ve bahçeleri.", "Versailles"),
        ],
        "rivers": [
            ([(395, 195), (275, 145), (185, 125), (105, 145), (45, 195)], 11), # Seine arch
        ],
        "avenues": [
            [(95, 85), (165, 115), (215, 122)], # Axe Historique (Arc -> Concorde -> Louvre)
            [(225, 65), (225, 185)],            # Blvd Sébastopol / St-Michel
        ],
        "district_zones": [
            {"poly": [(165, 90), (285, 90), (285, 130), (165, 130)]},
            {"poly": [(165, 135), (275, 135), (275, 185), (165, 185)]},
        ],
        "district_boxes": [
            (285, 105, "LE MARAIS"),
            (235, 168, "QUARTIER LATIN"),
            (225, 42, "MONTMARTRE"),
        ],
        "pois": [
            (205, 118, "LOUVRE"),
            (238, 132, "NOTRE-DAME"),
            (175, 132, "MUSEE D'ORSAY"),
            (115, 145, "TOUR EIFFEL"),
            (95, 85, "ARC DE TRIOMPHE"),
        ],
    },
    # 10. LONDON
    {
        "year": "UK • ENGLAND",
        "map_title": "LONDON",
        "title": "LONDON: THAMES, WESTMINSTER & THE CITY",
        "subtitle": "Thames kıvrımları, Westminster, British Museum, South Bank ve City of London",
        "overview": (
            "Thames nehrinin gelgitli menderesleri etrafında kurulan Londra, antik Roma yerleşimi Londinium'dan "
            "miras kalan finans merkezi 'The City' ile kraliyet ve parlamento merkezi 'City of Westminster' ikili "
            "çekirdeği etrafında şekillenmiştir. Dünyanın en zengin ücretsiz ulusal müzeleri, Kraliyet Parkları "
            "ve South Bank nehir yürüyüş yoluyla benzersiz bir kültür metropolüdür."
        ),
        "powers": [
            ("Westminster & Whitehall", "Parlamento Binası (Big Ben), Westminster Abbey, Buckingham Sarayı ve Trafalgar Meydanı.", "London"),
            ("Bloomsbury & West End", "British Museum, Covent Garden, Soho, tiyatrolar bölgesi ve University College London.", "London"),
            ("The City of London", "St Paul Katedrali, Tower of London, Tower Bridge, Bank of England ve gökdelenler.", "London"),
            ("South Bank & Greenwich", "Tate Modern, Shakespeare's Globe, Borough Market ve Başlangıç Meridyeni (0°).", "London"),
        ],
        "events": [
            ("The British Museum", "Rosetta Taşı, Parthenon Mermerleri, Asur kabartmaları ve dünya uygarlıkları arşivi (Ücretsiz).", "London"),
            ("National Gallery & Tate Modern", "Trafalgar Meydanı'nda Van Eyck'tan Turner'a Avrupa resmi ve Bankside çağdaş sanat müzesi.", "London"),
            ("Tower of London & Tower Bridge", "1066 Norman Fethi'nden kalan kale, Kraliyet Mücevherleri ve Viktorya dönemi baskül köprüsü.", "London"),
            ("Westminster Abbey & Houses of Parliament", "1066'dan beri taç giyme törenlerinin yapıldığı, Newton ve Darwin'in gömülü olduğu Gotik kilise.", "London"),
        ],
        "thinkers": [
            ("Borough Market, Fish & Chips, Sunday Roast", "1000 yıllık Borough gıda pazarı, tarihi publarda Yorkshire puddingli pazar rostosu ve Hint körileri.", "London"),
            ("Historic Pubs & Afternoon Tea", "Fleet Street'teki 17. yüzyıl edebiyat pubları (Ye Olde Cheshire Cheese) ve çay geleneği.", "London"),
            ("London Underground (Tube) & Thames Clipper", "Temassız kartla (Contactless) çalışan dünyanın ilk metrosu (1863) ve nehir vapurları.", "London"),
            ("Oxford, Cambridge & Bath", "Trenle 50–80 dakikada tarihi üniversite şehirleri Oxford ve Cambridge veya Roma hamamlarıyla Bath.", "Oxford"),
        ],
        "rivers": [
            ([(25, 175), (155, 165), (185, 125), (275, 120), (355, 145), (425, 135)], 12), # Thames
        ],
        "avenues": [
            [(95, 125), (175, 125), (285, 105)], # Mall -> Strand -> Fleet St
            [(175, 65), (175, 155)],
        ],
        "district_zones": [
            {"poly": [(145, 60), (235, 60), (235, 118), (145, 118)]},
            {"poly": [(255, 85), (355, 85), (355, 125), (255, 125)]},
        ],
        "district_boxes": [
            (95, 105, "HYDE PARK"),
            (205, 68, "BLOOMSBURY"),
            (285, 152, "SOUTH BANK"),
        ],
        "pois": [
            (175, 148, "WESTMINSTER"),
            (205, 85, "BRITISH MUSEUM"),
            (285, 105, "ST PAUL'S"),
            (278, 132, "TATE MODERN"),
            (355, 125, "TOWER OF LONDON"),
        ],
    },
    # 11. BERLIN
    {
        "year": "GERMANY • BRANDENBURG",
        "map_title": "BERLIN",
        "title": "BERLIN: SPREE RIVER, MUSEUM ISLAND & THE WALL",
        "subtitle": "Brandenburg Kapısı, Müzeler Adası, Reichstag ve Doğu-Batı tarihi",
        "overview": (
            "Spree ve Havel nehirleri kıyısında kurulan Berlin, Prusya Aydınlanması'ndan Weimar Cumhuriyeti'ne, "
            "II. Dünya Savaşı'ndan Soğuk Savaş'ın bölünmüş başkentine ve 1989'da Duvar'ın yıkılışına uzanan 20. "
            "yüzyıl tarihinin en yoğun sahnesidir. UNESCO listesindeki Müzeler Adası (Museumsinsel), Tiergarten "
            "ve Kreuzberg/Friedrichshain kültür mahalleleriyle Avrupa'nın en dinamik metropollerinden biridir."
        ),
        "powers": [
            ("Mitte & Unter den Linden", "Brandenburg Kapısı, Reichstag, Humboldt Üniversitesi ve Tarihi Müzeler Adası.", "Berlin"),
            ("Kreuzberg & Friedrichshain", "East Side Gallery (Berlin Duvarı), Oberbaumbrücke ve alternatif kültür/sanat semtleri.", "Berlin"),
            ("Charlottenburg & Tiergarten", "Kurfürstendamm, Kaiser-Wilhelm Anıt Kilisesi, Charlottenburg Sarayı ve büyük merkez parkı.", "Berlin"),
            ("Prenzlauer Berg", "19. yüzyıl binaları, Mauerpark, Kollwitzplatz ve kahve/kitapçı kültürü.", "Berlin"),
        ],
        "events": [
            ("Museumsinsel (Museum Island)", "Neues Museum (Nefertiti Büstü), Altes Museum, Alte Nationalgalerie ve Pergamon.", "Berlin"),
            ("Brandenburger Tor & Reichstag", "1791 Neoklasik Zafer Kapısı ve Norman Foster'ın cam kubbeli Federal Meclis binası.", "Berlin"),
            ("East Side Gallery & Gedenkstätte", "Spree kıyısında 1,3 km'lik korunmuş Berlin Duvarı ve Bernauer Straße Duvar Anıtı.", "Berlin"),
            ("Checkpoint Charlie & Topographie", "Soğuk Savaş sınır geçiş noktası ve eski Gestapo merkezindeki açık hava belgesel sergisi.", "Berlin"),
        ],
        "thinkers": [
            ("Currywurst, Döner Kebap & Berliner Pfannkuchen", "1949'da icat edilen baharatlı sosis, Kreuzberg usulü döner ve reçelli Berliner çöreği.", "Berlin"),
            ("Biergarten & Üçüncü Nesil Kahve", "Tiergarten göl kıyısındaki Cafe am Neuen See ve Mitte/Neukölln kahve kavurmacıları.", "Berlin"),
            ("S-Bahn Ringbahn (S41/S42) & U-Bahn", "Şehri çember şeklinde dönen Ringbahn ve Hauptbahnhof merkezli hızlı ulaşım ağı.", "Berlin"),
            ("Potsdam & Sanssouci Sarayı", "S-Bahn (S7) ile 35 dakikada Büyük Friedrich'in Sanssouci Sarayı ve Cecilienhof.", "Potsdam"),
        ],
        "rivers": [
            ([(25, 115), (145, 95), (235, 105), (345, 155), (425, 175)], 9), # Spree
        ],
        "avenues": [
            [(75, 118), (185, 118), (245, 108)], # Straße des 17. Juni -> Unter den Linden
            [(215, 45), (215, 195)],             # Friedrichstraße
        ],
        "district_zones": [
            {"poly": [(175, 70), (285, 70), (285, 145), (175, 145)]},
            {"poly": [(215, 150), (365, 150), (365, 215), (215, 215)]},
        ],
        "district_boxes": [
            (115, 130, "TIERGARTEN"),
            (285, 52, "PRENZLAUER BERG"),
            (265, 195, "KREUZBERG"),
        ],
        "pois": [
            (178, 105, "REICHSTAG & TOR"),
            (242, 102, "MUSEUMSINSEL"),
            (215, 152, "CHECKPOINT CHARLIE"),
            (345, 152, "EAST SIDE GALLERY"),
        ],
    },
    # 12. VIENNA
    {
        "year": "AUSTRIA • DANUBE",
        "map_title": "WIEN (VIENNA)",
        "title": "WIEN: RINGSTRASSE, HABSBURG PALACES & DANUBE",
        "subtitle": "Ringstraße bulvarı, Hofburg, Schönbrunn, Viyana kahveleri ve klasik müzik",
        "overview": (
            "Tuna (Donau) nehri ve Viyana Ormanları arasında uzanan Viyana, yüzyıllar boyunca Habsburg İmparatorluğu'nun "
            "başkenti, Mozart, Beethoven, Schubert ve Mahler ile klasik müziğin kalbi, 1900'lerde ise Freud, Klimt, "
            "Wittgenstein ve Viyana Çevresi ile modern düşüncenin laboratuvarı olmuştur. Eski surların yerine yapılan "
            "at nalı biçimli Ringstraße bulvarı tarihi merkezi (Innere Stadt) çevreler."
        ),
        "powers": [
            ("Innere Stadt (1. Bezirk)", "Stephansdom Katedrali, Hofburg İmparatorluk Sarayı, Graben ve tarihi kahvehaneler.", "Vienna"),
            ("Ringstraße & MuseumsQuartier", "Sanat Tarihi Müzesi (KHM), Doğa Tarihi Müzesi, Parlamento, Devlet Operası ve MQ.", "Vienna"),
            ("Belvedere & Wieden (3–4. Bezirk)", "Klimt'in 'Öpücük' tablosunu barındıran Barok Belvedere Sarayı, Karlskirche ve Naschmarkt.", "Vienna"),
            ("Leopoldstadt & Prater (2. Bezirk)", "Tuna Kanalı ile Tuna Nehri arasındaki ada; tarihi dönme dolap (Riesenrad) ve Augarten.", "Vienna"),
        ],
        "events": [
            ("Kunsthistorisches Museum (KHM)", "Dünyanın en büyük Bruegel koleksiyonu, Velázquez, Vermeer ve Rönesans hazineleri.", "Vienna"),
            ("Schloss Schönbrunn & Hofburg", "Habsburg yazlık sarayı, Gloriette tepesi ve İmparatorluk Hazinesi (Schatzkammer).", "Vienna"),
            ("Oberes Belvedere & Secession", "Gustav Klimt, Egon Schiele ve Viyana Modernizmi (Wiener Moderne) başyapıtları.", "Vienna"),
            ("Wiener Staatsoper & Musikverein", "Dünyanın en prestijli opera evlerinden biri ve ayakta izleme biletleri (Stehplätze).", "Vienna"),
        ],
        "thinkers": [
            ("Wiener Kaffeehaus (Café Central, Sacher, Hawelka)", "UNESCO mirası Viyana kahve kültürü: Wiener Melange, Sachertorte ve Apfelstrudel.", "Vienna"),
            ("Wiener Schnitzel & Tafelspitz", "İnce dövülmüş dana şnitzel (patates salatasıyla) ve elmalı yaban turbu soslu haşlama et.", "Vienna"),
            ("Wiener Linien (U-Bahn & Ring Tram #1/#2)", "U1–U6 metro hatları ve Ringstraße üzerindeki tüm anıtları gezen 1 ve 2 numaralı tramvaylar.", "Vienna"),
            ("Wachau Vadisi & Bratislava", "Tuna teknesiyle veya trenle 1 saatte Melk Manastırı ya da Slovakya başkenti Bratislava.", "Bratislava"),
        ],
        "rivers": [
            ([(315, 15), (375, 95), (425, 175)], 11),  # Danube Main
            ([(245, 25), (275, 95), (335, 165)], 6),   # Donaukanal
        ],
        "avenues": [
            [(255, 85), (275, 115), (245, 155), (185, 155), (165, 115), (195, 80), (255, 85)], # Ringstraße
        ],
        "district_zones": [
            {"poly": [(195, 80), (255, 85), (275, 115), (245, 155), (185, 155), (165, 115)]},
        ],
        "district_boxes": [
            (315, 72, "PRATER"),
            (135, 158, "NASCHMARKT"),
        ],
        "pois": [
            (225, 112, "STEPHANSDOM"),
            (200, 128, "HOFBURG"),
            (172, 138, "KHM & MQ"),
            (248, 178, "BELVEDERE"),
            (75, 195, "SCHONBRUNN"),
        ],
    },
    # 13. BARCELONA
    {
        "year": "SPAIN • CATALONIA",
        "map_title": "BARCELONA",
        "title": "BARCELONA: EIXAMPLE GRID, GAUDI & MEDITERRANEAN",
        "subtitle": "Cerdà'nın sekizgen ızgara planı, Sagrada Família, Barri Gòtic ve Akdeniz",
        "overview": (
            "Akdeniz kıyısı ile Collserola tepeleri arasında uzanan Barselona, Roma ve Ortaçağ'dan kalan dar "
            "Barri Gòtic labirentini, Ildefons Cerdà'nın 1859'da tasarladığı devrimci sekizgen bloklu Eixample "
            "ızgara planıyla birleştirir. Antoni Gaudí'nin doğadan esinlenen organik Katalan Modernisme mimarisi "
            "şehrin her köşesine damgasını vurmuştur."
        ),
        "powers": [
            ("Ciutat Vella (Barri Gòtic & El Born)", "Katedral, Roma surları, Santa Maria del Mar, Picasso Müzesi ve La Rambla.", "Barcelona"),
            ("L'Eixample & Passeig de Gràcia", "Cerdà'nın pahlı köşeli ızgara blokları, Casa Batlló, La Pedrera ve Sagrada Família.", "Barcelona"),
            ("Gràcia & Park Güell", "Bohem meydanlarıyla eski köy dokusunu koruyan Gràcia ve tepedeki Park Güell.", "Barcelona"),
            ("Montjuïc & Barceloneta", "Akdeniz sahili, eski balıkçı mahallesi ve MNAC ile Miró Müzesi'nin bulunduğu Montjuïc tepesi.", "Barcelona"),
        ],
        "events": [
            ("Basílica de la Sagrada Família", "Gaudí'nin 1882'den beri yükselen, taş orman sütunlu ve ışık vitraylı başyapıtı.", "Barcelona"),
            ("Casa Batlló & Casa Milà (La Pedrera)", "Passeig de Gràcia üzerindeki dalgalı taş cepheli ve ejderha çatılı Modernisme konutları.", "Barcelona"),
            ("Park Güell & Palau de la Música", "Kırık seramik mozaikli (trencadís) teras ve Domènech i Montaner'in vitraylı konser sarayı.", "Barcelona"),
            ("Museu Picasso & Fundació Joan Miró", "El Born'daki 5 Ortaçağ sarayında Picasso'nun gençlik dönemi ve Montjuïc'te Miró.", "Barcelona"),
        ],
        "thinkers": [
            ("Mercat de la Boqueria & Santa Caterina", "İberico jambonu, taze deniz ürünleri, manchego peyniri ve Katalan pazar kültürü.", "Barcelona"),
            ("Pa amb Tomàquet, Bombas & Crema Catalana", "Domates ve zeytinyağı sürülmüş kızarmış ekmek, patates bombası ve karamelize muhallebi.", "Barcelona"),
            ("TMB Metro, FGC & Montjuïc Teleferiği", "Sants garından tüm Eixample ve sahile yayılan 12 hatlı entegre metro ağı.", "Barcelona"),
            ("Montserrat Manastırı & Girona", "Trenle 1 saatte testere dişli Montserrat Dağı veya Ortaçağ surlarıyla Girona.", "Girona"),
        ],
        "water_polys": [
            [(225, 236), (345, 165), (436, 95), (436, 236)], # Mediterranean Sea
        ],
        "avenues": [
            [(95, 165), (345, 65)],   # Avinguda Diagonal
            [(185, 85), (255, 155)],  # Passeig de Gràcia -> La Rambla
            [(135, 175), (325, 115)], # Gran Via
        ],
        "district_zones": [
            {"poly": [(225, 130), (315, 130), (315, 185), (225, 185)]}, # Ciutat Vella
            {"poly": [(145, 70), (305, 70), (305, 128), (145, 128)]},   # Eixample
        ],
        "district_boxes": [
            (195, 55, "GRACIA"),
            (135, 200, "MONTJUIC"),
            (325, 185, "BARCELONETA"),
        ],
        "pois": [
            (275, 78, "SAGRADA FAMILIA"),
            (215, 108, "CASA BATLLO"),
            (265, 155, "BARRI GOTIC"),
            (215, 38, "PARK GUELL"),
        ],
    },
    # 14. AMSTERDAM
    {
        "year": "NETHERLANDS • HOLLAND",
        "map_title": "AMSTERDAM",
        "title": "AMSTERDAM: GOLDEN AGE CANAL RING (GRACHTENGORDEL)",
        "subtitle": "At nalı biçimli 4 eşmerkezli kanal halkası, Rijksmuseum ve Jordaan",
        "overview": (
            "Amstel nehrinin IJ körfezine döküldüğü yerde inşa edilen Amsterdam, 17. yüzyıl Hollanda Altın Çağı'nda "
            "dünyanın en başarılı kentsel planlama projelerinden biri olan yarım daire biçimli Grachtengordel "
            "(Singel, Herengracht, Keizersgracht, Prinsengracht) kanal halkasıyla genişlemiştir. Dar alınlıklı "
            "tüccar evleri, 1.500 köprü, bisiklet yolları ve dünya çapındaki sanat müzeleriyle tanınır."
        ),
        "powers": [
            ("Centrum & Dam Meydanı", "Kraliyet Sarayı, Yeni Kilise (Nieuwe Kerk), Begijnhof avlusu ve Amstel kıyısı.", "Amsterdam"),
            ("Grachtengordel (Kanal Halkası)", "UNESCO korumasındaki Herengracht, Keizersgracht ve Prinsengracht ile 9 Straatjes butik sokakları.", "Amsterdam"),
            ("Jordaan", "Batı kanallarında Anne Frank Evi, Westerkerk, gizli iç avlular (hofjes) ve tarihi 'bruin café' pubları.", "Amsterdam"),
            ("Museumkwartier & Vondelpark", "Rijksmuseum, Van Gogh Müzesi, Stedelijk Müzesi, Concertgebouw ve Vondelpark.", "Amsterdam"),
        ],
        "events": [
            ("Rijksmuseum", "Rembrandt'ın Gece Devriyesi (Night Watch), Vermeer'in Sütçü Kız'ı ve 800 yıllık Hollanda tarihi.", "Amsterdam"),
            ("Van Gogh Museum", "Ayçiçekleri, Yatak Odası, Patates Yiyenler ve Van Gogh'un 200'den fazla tablosu ile mektupları.", "Amsterdam"),
            ("Anne Frank Huis", "Prinsengracht 263'teki gizli çatı katı (Achterhuis) ve II. Dünya Savaşı bellek müzesi.", "Amsterdam"),
            ("Grachtenfahrt & Begijnhof", "Tarihi kanallarda tekne/yürüyüş rotası ve 14. yüzyıldan kalma sessiz Begijnhof iç avlusu.", "Amsterdam"),
        ],
        "thinkers": [
            ("Stroopwafel, Haring & Bitterballen", "Albert Cuyp Pazarı'nda sıcak karamelli stroopwafel, salatalıklı ringa balığı ve hardallı kroket.", "Amsterdam"),
            ("Rijsttafel & Hollanda Peynirleri", "Çok çeşnili Endonezya 'pirinç sofrası' ve yıllandırılmış Gouda / Edam peynir tadımı.", "Amsterdam"),
            ("Fiets (Bisiklet), GVB Tramvay & Feribot", "Centraal Station arkasından NDSM kültür tersanesine ücretsiz IJ feribotları ve tramvaylar.", "Amsterdam"),
            ("Haarlem, Delft, Leiden & Lahey", "Trenle 15–45 dakikada Frans Hals'ın Haarlem'i, Vermeer'in Delft'i ve Mauritshuis (Lahey).", "Delft"),
        ],
        "water_polys": [
            [(3, 3), (436, 3), (436, 52), (3, 42)], # IJ waterfront
        ],
        "rivers": [
            ([(225, 235), (225, 115), (235, 50)], 8), # Amstel
            ([(145, 55), (125, 135), (175, 185), (275, 185), (325, 135), (305, 55)], 5), # Outer Canal Ring
            ([(165, 60), (150, 125), (185, 165), (265, 165), (295, 125), (280, 60)], 4), # Inner Canal Ring
        ],
        "district_zones": [
            {"poly": [(125, 55), (325, 55), (325, 185), (125, 185)]},
        ],
        "district_boxes": [
            (95, 115, "JORDAAN"),
            (135, 208, "VONDELPARK"),
        ],
        "pois": [
            (235, 52, "CENTRAAL"),
            (215, 102, "DAM SQUARE"),
            (150, 98, "ANNE FRANK HUIS"),
            (205, 198, "RIJKSMUSEUM & VAN GOGH"),
        ],
    },
    # 15. PRAGUE
    {
        "year": "CZECHIA • BOHEMIA",
        "map_title": "PRAHA (PRAGUE)",
        "title": "PRAHA: VLTAVA BRIDGES, OLD TOWN & CASTLE",
        "subtitle": "Vltava nehri, Karl Köprüsü, Astronomik Saat ve Prag Kalesi",
        "overview": (
            "'Yüz Kuleli Şehir' olarak anılan Prag, Vltava nehrinin iki yakasında II. Dünya Savaşı'nda yıkıma "
            "uğramadan günümüze ulaşmış Gotik, Rönesans, Barok ve Art Nouveau mimari bütünlüğüyle orta Avrupa'nın "
            "incisidir. XIV. yüzyılda İmparator IV. Karl'ın inşa ettirdiği taş Karl Köprüsü, Eski Şehir (Staré Město) "
            "ile karşı tepedeki devasa Prag Kalesi ve Malá Strana'yı birbirine bağlar."
        ),
        "powers": [
            ("Staré Město & Josefov", "Eski Şehir Meydanı, Astronomik Saat, Týn Kilisesi, Klementinum ve tarihi Yahudi Mahallesi.", "Prague"),
            ("Malá Strana (Küçük Mahalle)", "Karl Köprüsü'nün batı ucunda Barok saraylar, Aziz Nikolas Kilisesi ve Petřín Tepesi.", "Prague"),
            ("Hradčany & Pražský Hrad", "Dünyanın en büyük antik kale kompleksi, Aziz Vitus Katedrali, Altın Yol ve Strahov Manastırı.", "Prague"),
            ("Nové Město & Vyšehrad", "Wenceslas Meydanı, Ulusal Tiyatro, Dans Eden Ev ve Vltava kıyısındaki tarihi Vyšehrad kalesi.", "Prague"),
        ],
        "events": [
            ("Karlův Most (Charles Bridge)", "1357'de temeli atılan, 30 Barok aziz heykeliyle süslü 516 metrelik taş yaya köprüsü.", "Prague"),
            ("Staroměstské Náměstí & Orloj", "1410'dan beri çalışan dünyanın en eski aktif Astronomik Saati (Orloj) ve Jan Hus Anıtı.", "Prague"),
            ("Pražský Hrad & Katedrála Sv. Víta", "Gotik vitrayları (Alfons Mucha), Bohemya krallarının mezarları ve Eski Kraliyet Sarayı.", "Prague"),
            ("Strahovský Klášter & Klementinum", "Barok tavan freskli Teoloji/Felsefe salonlarıyla dünyanın en görkemli tarihi kütüphaneleri.", "Prague"),
        ],
        "thinkers": [
            ("Svíčková na Smetaně & Guláš", "Kremalı kök sebze sosunda marine sığır eti ve dilimlenmiş Çek ekmek mantısı (knedlíky).", "Prague"),
            ("Pilsner Urquell & Tarihi Pivnice", "1499'dan beri bira üreten U Fleků ve U Zlatého Tygra (Bohumil Hrabal'ın masası).", "Prague"),
            ("Tramvay #22 & Prag Metrosu (A/B/C)", "Yeni Şehir'den Malá Strana ve Prag Kalesi'ne tırmanan panoramik 22 numaralı tramvay.", "Prague"),
            ("Kutná Hora & Český Krumlov", "Trenle 1 saatte Sedlec Kemikli Kilise ve Azize Barbara Katedrali (Kutná Hora).", "Kutná Hora"),
        ],
        "rivers": [
            ([(215, 235), (210, 155), (215, 95), (275, 55), (385, 55)], 11), # Vltava curve
        ],
        "avenues": [
            [(125, 95), (210, 115), (265, 115)], # Castle -> Charles Bridge -> Old Town
            [(265, 115), (305, 175)],            # Wenceslas Square
        ],
        "district_zones": [
            {"poly": [(220, 75), (320, 75), (320, 145), (220, 145)]}, # Staré Město
            {"poly": [(85, 65), (205, 65), (205, 155), (85, 155)]},   # Hradčany & Malá Strana
        ],
        "district_boxes": [
            (270, 82, "JOSEFOV"),
            (155, 145, "MALA STRANA"),
            (315, 175, "NOVE MESTO"),
        ],
        "pois": [
            (135, 88, "PRAGUE CASTLE"),
            (212, 115, "CHARLES BRIDGE"),
            (265, 112, "OLD TOWN SQ"),
            (210, 215, "VYSEHRAD"),
        ],
    },
    # 16. ATHENS
    {
        "year": "GREECE • ATTICA",
        "map_title": "ATHINA (ATHENS)",
        "title": "ATHENS: ACROPOLIS, AGORA & AEGEAN CRADLE",
        "subtitle": "Akropolis, Parthenon, Antik Agora, Plaka ve Felsefe Akademileri",
        "overview": (
            "Attika havzasında Lycabettus tepesi ile Saronik Körfezi (Pire) arasında yükselen Atina, demokrasinin, "
            "batı tiyatrosunun, tarihyazımının ve Sokrates–Platon–Aristoteles felsefe geleneğinin doğduğu kenttir. "
            "Kutsal Kaya Akropolis'in etrafını saran trafiğe kapalı Arkeolojik Yürüyüş Yolu (Dionysiou Areopagitou), "
            "Antik Agora, Plaka ve Koukaki semtlerini tek bir kesintisiz antik peyzajda birleştirir."
        ),
        "powers": [
            ("Acropolis & Koukaki", "Parthenon, Erechtheion, Dionysos Tiyatrosu, Herodes Atticus Odeonu ve Yeni Akropolis Müzesi.", "Athens"),
            ("Plaka & Anafiotika", "Akropolis'in kuzey yamacında Bizans kiliseleri, Neoklasik evler ve Kiklad adası tarzı beyaz sokaklar.", "Athens"),
            ("Monastiraki, Thiseio & Agora", "Sokrates'in tartıştığı Antik Yunan Agorası, Hephaistos Tapınağı, Roma Agorası ve Rüzgarlar Kulesi.", "Athens"),
            ("Syntagma & Kolonaki", "Parlamento Binası, Ulusal Bahçe, Kiklad Sanat Müzesi ve panoramik Lycabettus Tepesi.", "Athens"),
        ],
        "events": [
            ("The Acropolis & Parthenon", "MÖ 5. yüzyıl Perikles çağında Iktinos, Kallikrates ve Pheidias tarafından inşa edilen dor tapınağı.", "Athens"),
            ("Acropolis Museum", "Bernard Tschumi'nin cam zeminli müzesinde Karyatidler ve Parthenon Frizleri.", "Athens"),
            ("Ancient Agora & Stoa of Attalos", "Demokrasinin kalbi, en iyi korunmuş Dor tapınağı Hephaisteion ve Agora Müzesi.", "Athens"),
            ("National Archaeological Museum", "Agamemnon'un Altın Maskesi, Antikythera Düzeneği ve Artemision Bronz Poseidon/Zeus heykeli.", "Athens"),
        ],
        "thinkers": [
            ("Souvlaki, Moussaka & Mezedopoleia", "Psyrri ve Plaka meyhane/tavernalarında ızgara deniz ürünleri, fava, horiatiki ve ouzo/tsipouro.", "Athens"),
            ("Koulouri, Bougatsa & Freddo Espresso", "Sabah susamlı simit (koulouri), kremalı börek ve Yunan buzlu kahve geleneği.", "Athens"),
            ("Atina Metrosu (Hat 1/2/3) & Pire Limanı", "İnşaatında çıkan antik eserlerin sergilendiği Syntagma/Acropolis istasyonları ve Ege adaları feribotları.", "Athens"),
            ("Sounion Burnu, Delphi & Mora", "Gün batımında Poseidon Tapınağı (Sounion) veya Apollon'un kehanet merkezi Delphi.", "Delphi"),
        ],
        "water_polys": [
            [(3, 195), (145, 205), (215, 236), (3, 236)], # Saronic Gulf / Piraeus corner
        ],
        "avenues": [
            [(75, 205), (195, 135), (285, 95)], # Piraeus -> Acropolis -> Syntagma
            [(165, 145), (235, 155)],           # Dionysiou Areopagitou promenade
        ],
        "district_zones": [
            {"poly": [(155, 95), (275, 95), (275, 165), (155, 165)]},
        ],
        "district_boxes": [
            (245, 132, "PLAKA"),
            (175, 95, "MONASTIRAKI"),
            (325, 72, "LYCABETTUS"),
        ],
        "pois": [
            (205, 142, "ACROPOLIS"),
            (172, 125, "ANCIENT AGORA"),
            (275, 108, "SYNTAGMA"),
            (235, 58, "ARCHAEOLOGICAL MUS."),
            (75, 202, "PIRAEUS PORT"),
        ],
    },
    # 17. ISTANBUL
    {
        "year": "TURKEY • BOSPHORUS",
        "map_title": "ISTANBUL",
        "title": "ISTANBUL: BOSPHORUS, GOLDEN HORN & TWO CONTINENTS",
        "subtitle": "Tarihi Yarımada, Haliç, Boğaziçi, Beyoğlu ve Kadıköy",
        "overview": (
            "Avrupa ile Asya'yı ayıran İstanbul Boğazı ve Haliç'in kesişiminde kurulan İstanbul (Byzantion, "
            "Konstantinopolis), Roma, Bizans ve Osmanlı imparatorluklarına 1.600 yıl başkentlik yapmıştır. "
            "Tarihi Yarımada'nın kubbeleri ve sarnıçları, Galata ve Beyoğlu'nun 19. yüzyıl pasajları ile vapurla "
            "20 dakikada geçilen Anadolu yakasındaki Kadıköy/Moda sahili kıtalararası bir kentsel doku oluşturur."
        ),
        "powers": [
            ("Sultanahmet & Tarihi Yarımada", "Ayasofya, Sultanahmet Camii, Topkapı Sarayı, Yerebatan Sarnıcı, Kapalıçarşı ve Süleymaniye.", "Istanbul"),
            ("Karaköy, Galata & Beyoğlu", "Galata Kulesi, İstiklal Caddesi, Pera Müzesi, tarihi pasajlar, Çukurcuma ve Cihangir.", "Istanbul"),
            ("Beşiktaş & Boğaziçi Kıyısı", "Dolmabahçe Sarayı, Ortaköy, Arnavutköy, Bebek ve Rumeli Hisarı.", "Istanbul"),
            ("Kadıköy, Moda & Üsküdar (Asya)", "Şehir Hatları vapuruyla geçilen Kadıköy Çarşısı, Moda sahili ve Kuzguncuk.", "Istanbul"),
        ],
        "events": [
            ("Ayasofya (Hagia Sophia) & Topkapı", "MS 537'de I. Justinianus'un inşa ettirdiği kubbeli bazilika ve 400 yıllık Osmanlı sarayı.", "Istanbul"),
            ("Süleymaniye Camii & Külliyesi", "Mimar Sinan'ın Haliç'e hakim üçüncü tepedeki kalfalık başyapıtı (1557).", "Istanbul"),
            ("Yerebatan Sarnıcı & Arkeoloji Müzesi", "Medusa başlı 336 mermer sütunlu Bizans sarnıcı ve İskender Lahdi.", "Istanbul"),
            ("Galata Kulesi & Boğaz Vapuru", "1348 Ceneviz kulesi ve Eminönü/Karaköy'den Kadıköy veya Boğaz'a vapur geçişi.", "Istanbul"),
        ],
        "thinkers": [
            ("Tarihi Esnaf Lokantaları & Meyhaneler", "Eminönü/Karaköy balık-ekmek, Kapalıçarşı esnaf lokantaları ve Beyoğlu/Kadıköy mezeleri.", "Istanbul"),
            ("Türk Kahvesi, Simit & Çay Bahçeleri", "Mısır Çarşısı kahvecileri, vapurda susamlı simit-çay ve Moda sahil yürüyüşü.", "Istanbul"),
            ("Şehir Hatları Vapurları, Marmaray & T1 Tramvay", "Tarihi Yarımada'yı Karaköy ve Kabataş'a bağlayan T1 tramvayı ve Boğaz altı Marmaray.", "Istanbul"),
            ("Prens Adaları (Büyükada & Heybeliada)", "Kabataş veya Kadıköy'den vapurla çam ormanlı ve ahşap köşklü Marmara adaları.", "Princes' Islands"),
        ],
        "water_polys": [
            [(235, 3), (295, 3), (265, 115), (345, 236), (175, 236), (215, 145), (105, 95), (115, 80), (220, 125)], # Bosphorus + Golden Horn + Marmara
        ],
        "avenues": [
            [(95, 155), (205, 155)],  # Divanyolu
            [(205, 115), (215, 65)],  # İstiklal Caddesi
        ],
        "district_zones": [
            {"poly": [(75, 125), (215, 135), (205, 195), (75, 195)]}, # Historic Peninsula
            {"poly": [(165, 55), (240, 55), (230, 120), (165, 110)]}, # Beyoğlu
            {"poly": [(295, 135), (415, 135), (415, 215), (295, 215)]}, # Kadıköy
        ],
        "district_boxes": [
            (195, 62, "BEYOGLU"),
            (355, 175, "KADIKOY (ASIA)"),
        ],
        "pois": [
            (192, 162, "HAGIA SOPHIA & TOPKAPI"),
            (145, 148, "SULEYMANIYE & BAZAAR"),
            (205, 112, "GALATA TOWER"),
            (242, 72, "DOLMABAHCE"),
        ],
    },
    # 18. LISBON
    {
        "year": "PORTUGAL • TAGUS",
        "map_title": "LISBOA (LISBON)",
        "title": "LISBOA: SEVEN HILLS, ALFAMA & BELÉM",
        "subtitle": "Tejo nehri ağzı, 28 numaralı tramvay, Alfama, Baixa ve Belém",
        "overview": (
            "Tejo (Tagus) nehrinin Atlantik Okyanusu ile buluştuğu geniş haliçte yedi dik tepe üzerine kurulan "
            "Lizbon, 15. ve 16. yüzyıl Coğrafi Keşifler Çağı'nın deniz üssüydü. 1755 depreminden sonra Marki de Pombal "
            "tarafından aydınlanma ızgarasıyla yeniden kurulan Baixa, depremden kurtulan Mağribi kökenli Alfama "
            "mahallesi ve azulejo çinili cepheleriyle Avrupa'nın en ışıklı Atlantik başkentidir."
        ),
        "powers": [
            ("Baixa, Rossio & Chiado", "Praça do Comércio, Augusta Caddesi, Santa Justa Asansörü ve edebiyatçıların Chiado terasları.", "Lisbon"),
            ("Alfama & Castelo", "São Jorge Kalesi, Lizbon Katedrali (Sé), fado evleri ve miradouro seyir terasları.", "Lisbon"),
            ("Bairro Alto & Príncipe Real", "Fünikülerle (Glória/Bica) çıkılan dik sokaklar, São Pedro de Alcântara terası ve gece hayatı.", "Lisbon"),
            ("Belém & Alcântara", "Jerónimos Manastırı, Belém Kulesi, Keşifler Anıtı ve LX Factory kültür merkezi.", "Lisbon"),
        ],
        "events": [
            ("Mosteiro dos Jerónimos & Torre de Belém", "Vasco da Gama'nın Hindistan seferi onuruna yapılan UNESCO Manuelin mimari başyapıtları.", "Lisbon"),
            ("Castelo de São Jorge & Miradouros", "Santa Luzia ve Senhora do Monte teraslarından kızıl çatılar ve Tejo manzarası.", "Lisbon"),
            ("Museu Calouste Gulbenkian & Azulejos", "Dünya çapında klasik/modern sanat koleksiyonu ve 500 yıllık Portekiz çini müzesi.", "Lisbon"),
            ("Elétrico 28 (Tramvay 28)", "Martim Moniz'den Graça, Alfama, Baixa ve Estrela'ya dar sokakları tırmanan sarı ahşap tramvay.", "Lisbon"),
        ],
        "thinkers": [
            ("Pastéis de Belém (Pastel de Nata)", "1837'den beri tarçın ve pudra şekeriyle sıcak servis edilen çıtır milföylü yumurtalı tart.", "Lisbon"),
            ("Bacalhau à Brás, Sardinha Assada & Ginjinha", "365 farklı tarifle pişirilen morina balığı, ızgara sardalya ve vişne likörü.", "Lisbon"),
            ("Asansörler (Elevadores) & CP Banliyö Trenleri", "Rossio garından Sintra'ya, Cais do Sodré garından Cascais okyanus kıyısına trenler.", "Lisbon"),
            ("Sintra, Cabo da Roca & Cascais", "40 dakikada Pena Sarayı, Quinta da Regaleira ve kıta Avrupası'nın en batı ucu Cabo da Roca.", "Sintra"),
        ],
        "water_polys": [
            [(3, 165), (185, 160), (315, 140), (436, 95), (436, 236), (3, 236)], # Tagus Estuary
        ],
        "avenues": [
            [(65, 155), (245, 145)],  # Riverfront Belém -> Baixa
            [(225, 75), (245, 145)],  # Av. da Liberdade -> Baixa
        ],
        "district_zones": [
            {"poly": [(195, 85), (325, 85), (325, 148), (195, 148)]},
        ],
        "district_boxes": [
            (195, 105, "BAIRRO ALTO"),
            (305, 105, "ALFAMA"),
        ],
        "pois": [
            (78, 148, "BELEM TOWER & JERONIMOS"),
            (245, 142, "BAIXA & COMERCIO"),
            (285, 108, "CASTELO S.JORGE"),
            (225, 55, "GULBENKIAN"),
        ],
    },
    # 19. ZURICH
    {
        "year": "SWITZERLAND • ALPS",
        "map_title": "ZURICH",
        "title": "ZURICH: LIMMAT RIVER, LAKE ZURICH & ETH",
        "subtitle": "Limmat nehri, Zürih Gölü, Niederdorf, Kunsthaus ve ETH Zürich",
        "overview": (
            "Zürih Gölü'nün kuzey ucundan doğan berrak Limmat nehrinin iki yakasında kurulan Zürih, Roma gümrük "
            "istasyonu Turicum'dan Reformasyon'a (Zwingli), 1916 Cabaret Voltaire'de doğan Dadaizm akımına ve "
            "Albert Einstein'ın okuduğu/ders verdiği ETH Zürich'e uzanan bir bilim ve kültür şehridir. Dakik tramvay "
            "ağı ve Alp zirvelerine açılan tren hatlarıyla İsviçre'nin kalbidir."
        ),
        "powers": [
            ("Altstadt (Lindenhof & Niederdorf)", "Roma kalesi tepesi Lindenhof, St. Peter, Fraumünster, Grossmünster ve yaya Niederdorf sokakları.", "Zurich"),
            ("Bahnhofstrasse & Paradeplatz", "Ana gardan göl kıyısına (Bürkliplatz) uzanan ağaçlı bulvar ve tarihi saat/finans merkezi.", "Zurich"),
            ("Hochschulquartier (ETH & UZH)", "Polybahn füniküleriyle çıkılan ETH Zürich terası, Semper Binası ve Kunsthaus sanat müzesi.", "Zurich"),
            ("Zürich-West & Seefeld", "Eski demiryolu kemerleri altındaki Viadukt ve göl kıyısında Le Corbusier Pavyonu.", "Zurich"),
        ],
        "events": [
            ("Grossmünster & Fraumünster", "Çift kuleli Romanesk katedral ve Fraumünster'de Marc Chagall ile Giacometti vitrayları.", "Zurich"),
            ("Kunsthaus Zürich", "Chipperfield ek binasıyla birlikte Giacometti, Monet, Munch, Cézanne ve Dadaizm koleksiyonu.", "Zurich"),
            ("Schweizerisches Nationalmuseum & ETH", "Hauptbahnhof yanındaki şato biçimli İsviçre Ulusal Müzesi ve ETH Polyterrasse manzarası.", "Zurich"),
            ("Uetliberg & Zürichsee", "S10 treniyle 20 dakikada çıkılan 870 m'lik Uetliberg zirvesi ve göl vapurları.", "Zurich"),
        ],
        "thinkers": [
            ("Zürcher Geschnetzeltes & Rösti", "Kremalı beyaz şarap ve mantar soslu dana dilimleri ile çıtır patates rösti (Zeughauskeller).", "Zurich"),
            ("Confiserie Sprüngli (Luxemburgerli) & Fondue", "Paradeplatz'da taze Luxemburgerli makaronları ve kış aylarında gravyer/vacherin peynir fondüsü.", "Zurich"),
            ("VBZ Tramvay Ağı, Polybahn & SBB", "Saniyesi saniyesine işleyen mavi-beyaz tramvaylar ve nehir/göl teknelerini kapsayan ZVV bileti.", "Zurich"),
            ("Luzern, Bern & Rheinfall", "Trenle 45–60 dakikada Luzern Kapellbrücke, Bern eski şehri veya Ren Şelalesi (Schaffhausen).", "Lucerne"),
        ],
        "water_polys": [
            [(185, 165), (275, 165), (325, 236), (175, 236)], # Lake Zurich
        ],
        "rivers": [
            ([(225, 165), (215, 95), (175, 25)], 9), # Limmat flowing north
            ([(165, 165), (175, 95), (205, 65)], 5), # Sihl joining Limmat
        ],
        "avenues": [
            [(195, 72), (195, 162)], # Bahnhofstrasse
        ],
        "district_zones": [
            {"poly": [(175, 65), (265, 65), (265, 162), (175, 162)]},
        ],
        "district_boxes": [
            (255, 88, "ETH ZURICH"),
            (115, 175, "UETLIBERG"),
        ],
        "pois": [
            (198, 65, "HAUPTBAHNHOF"),
            (202, 112, "LINDENHOF"),
            (232, 132, "GROSSMUNSTER"),
            (265, 138, "KUNSTHAUS"),
            (235, 185, "ZURICHSEE"),
        ],
    },
    # 20. TOKYO
    {
        "year": "JAPAN • KANTO",
        "map_title": "TOKYO",
        "title": "TOKYO: IMPERIAL MOAT, YAMANOTE LOOP & SUMIDA",
        "subtitle": "Edo Kalesi hendekleri, Yamanote demiryolu çemberi, Asakusa ve Shinjuku",
        "overview": (
            "1603'te Tokugawa Şogunluğu'nun merkezi Edo olarak yükselen ve 1868 Meiji Restorasyonu ile imparatorluk "
            "başkenti olan Tokyo, merkezdeki İmparatorluk Sarayı bahçeleri ve onu çember şeklinde saran yeşil "
            "JR Yamanote demiryolu hattı etrafında çok merkezli bir metropol olarak işler. Sumida nehri kıyısındaki "
            "tarihi Asakusa/Ueno tapınakları (Shitamachi) ile batıdaki Shinjuku ve Shibuya zıtlığı büyüleyicidir."
        ),
        "powers": [
            ("Chiyoda & Marunouchi", "İmparatorluk Sarayı (Kōkyo) hendekleri, tarihi kırmızı tuğlalı Tokyo İstasyonu ve Ginza.", "Tokyo"),
            ("Asakusa & Ueno (Shitamachi)", "645 tarihli Sensō-ji Tapınağı, Sumida Nehri, Ueno Parkı ve Tokyo Ulusal Müzesi.", "Tokyo"),
            ("Shinjuku & Shibuya", "Dünyanın en işlek garı Shinjuku, Meiji Jingu orman tapınağı, Harajuku ve Shibuya Kavşağı.", "Tokyo"),
            ("Akihabara, Yanaka & Odaiba", "Elektronik/anime mahallesi Akihabara, eski ahşap dokulu Yanaka ve Tokyo Körfezi.", "Tokyo"),
        ],
        "events": [
            ("Sensō-ji (Asakusa) & Meiji Jingū", "Kaminarimon (Yıldırım Kapısı) feneriyle Tokyo'nun en eski Budist tapınağı ve Şinto Meiji ormanı.", "Tokyo"),
            ("Tokyo National Museum (Ueno)", "Samuray zırhları, Hokusai/Hiroshige ukiyo-e ahşap baskıları ve Japon ulusal hazineleri.", "Tokyo"),
            ("Imperial Palace East Gardens", "Eski Edo Kalesi'nin devasa taş surları, hendekleri, Nijubashi köprüsü ve Japon bahçeleri.", "Tokyo"),
            ("Shibuya Crossing & Shinjuku Gyoen", "Yaya geçidi senfonisi ve geleneksel Japon, Fransız ve İngiliz peyzajlı Shinjuku Gyoen.", "Tokyo"),
        ],
        "thinkers": [
            ("Edomae Sushi, Ramen, Tempura & Soba", "Tsukiji Dış Pazarı'nda sabah suşisi, tonkotsu/shoyu ramen ve karabuğday eriştesi (soba).", "Tokyo"),
            ("Izakaya, Depachika & Matcha", "Tren köprüleri altındaki (Yurakucho/Omoide Yokocho) izakayalar ve mağaza alt katı gıda galerileri.", "Tokyo"),
            ("JR Yamanote Line & Suica/Pasmo", "Tokyo'nun tüm ana merkezlerini (Tokyo, Ueno, Shinjuku, Shibuya) birbirine bağlayan halka tren.", "Tokyo"),
            ("Kamakura, Nikko & Hakone (Fuji)", "Trenle 1–2 saatte Büyük Buda (Kamakura), Toshogu Tapınağı (Nikko) ve Fuji Dağı manzaralı Hakone.", "Kamakura"),
        ],
        "water_polys": [
            [(285, 175), (436, 155), (436, 236), (265, 236)], # Tokyo Bay
        ],
        "rivers": [
            ([(325, 15), (335, 85), (315, 175)], 9), # Sumida River
        ],
        "rails": [
            [(245, 55), (275, 115), (245, 175), (155, 185), (125, 125), (165, 65), (245, 55)], # JR Yamanote Loop
        ],
        "district_zones": [
            {"poly": [(195, 95), (255, 95), (255, 145), (195, 145)]}, # Imperial Palace & Marunouchi
            {"poly": [(105, 95), (165, 95), (165, 175), (105, 175)]}, # Shinjuku / Shibuya
        ],
        "district_boxes": [
            (265, 98, "AKIHABARA"),
            (265, 148, "GINZA"),
        ],
        "pois": [
            (225, 118, "IMPERIAL PALACE"),
            (265, 62, "UENO MUSEUM"),
            (325, 68, "ASAKUSA SENSO-JI"),
            (125, 115, "SHINJUKU"),
            (142, 168, "SHIBUYA & MEIJI"),
        ],
    },
]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    wv_titles = load_wv_titles()
    assert len(CITIES) == 20, f"Expected 20 cities, got {len(CITIES)}"

    out_bytes = bytearray()
    out_bytes += struct.pack("<8sHHHH", b"CNAT0001", len(CITIES), MAP_W, MAP_H, 0)
    assert len(out_bytes) == 16

    for idx, city in enumerate(CITIES):
        rec = bytearray()
        rec += pack_utf8(city["year"], 24)
        rec += pack_utf8(city["title"], 48)
        rec += pack_utf8(city["subtitle"], 64)
        rec += pack_utf8(city["overview"], 640)
        for group_key in ("powers", "events", "thinkers"):
            assert len(city[group_key]) == 4
            for name, detail, wtitle in city[group_key]:
                if wtitle not in wv_titles:
                    wtitle = city["powers"][0][2]
                assert wtitle in wv_titles, f"Missing Wikivoyage title '{wtitle}' in {city['title']}"
                rec += pack_utf8(name, 36)
                rec += pack_utf8(detail, 96)
                rec += pack_utf8(wtitle, 48)
        bmp_bytes, _ = render_city_map(city)
        assert len(bmp_bytes) == 13200
        rec += bmp_bytes
        assert len(rec) == 16136, f"Record {idx} size {len(rec)}"
        out_bytes += rec

    with open(OUT_PATH, "wb") as f:
        f.write(out_bytes)
    print(f"Wrote {OUT_PATH}: {len(out_bytes)} bytes ({len(CITIES)} cities)")

if __name__ == "__main__":
    main()
