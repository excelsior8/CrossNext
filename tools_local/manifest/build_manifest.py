#!/usr/bin/env python3
import os
import struct
import math
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = "./sd_out"
OUT_PATH = os.path.join(OUT_DIR, "scenes.bin")

W, H = 440, 200

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
    except Exception:
        font_sm = ImageFont.load_default()
        font_md = font_sm
    return font_sm, font_md

FONT_SM, FONT_MD = load_fonts()

CREW = [
    "01. Capt. Lorenzo Conti",
    "02. 1st Mate Marco Valli",
    "03. Dr. Enrico Fermi-Lombardi",
    "04. Chief Eng. Bruno Sarti",
    "05. Purser Giancarlo Neri",
    "06. Signora Elena Grimani",
    "07. Helmsman Pietro Corso",
    "08. Bosun Matteo Rizzo",
    "09. Telegraphist Luca Bini",
    "10. Stowaway Sofia Vane",
]

FATES = [
    "Shot with revolver",
    "Poisoned (cyanide)",
    "Crushed by cargo/gear",
    "Stabbed with blade",
    "Drowned Overboard",
    "Struck by lightning",
    "Electrocuted by dynamo",
    "Escaped in lifeboat",
]

KILLERS = [
    "None / Accident / Force of Nature",
    "Suicide (Self-Inflicted)",
    "Capt. Lorenzo Conti",
    "1st Mate Marco Valli",
    "Dr. Enrico Fermi-Lombardi",
    "Chief Eng. Bruno Sarti",
    "Purser Giancarlo Neri",
    "Signora Elena Grimani",
    "Helmsman Pietro Corso",
    "Bosun Matteo Rizzo",
    "Telegraphist Luca Bini",
    "Stowaway Sofia Vane",
]

def draw_figure(draw, x, y, pose="standing", prop=""):
    # Head
    draw.ellipse([x - 7, y - 34, x + 7, y - 20], fill=0, outline=1)
    draw.ellipse([x - 6, y - 33, x + 6, y - 21], outline=1)
    if pose == "standing":
        draw.polygon([(x - 10, y - 19), (x + 10, y - 19), (x + 12, y + 8), (x - 12, y + 8)], fill=1)
        draw.line([(x - 6, y + 8), (x - 8, y + 28)], fill=1, width=3)
        draw.line([(x + 6, y + 8), (x + 8, y + 28)], fill=1, width=3)
    elif pose == "fallen":
        draw.polygon([(x - 18, y + 10), (x + 18, y + 6), (x + 22, y + 20), (x - 14, y + 22)], fill=1)
        draw.ellipse([x - 28, y + 8, x - 14, y + 22], fill=0, outline=1)
    elif pose == "slumped":
        draw.polygon([(x - 12, y - 12), (x + 10, y - 8), (x + 14, y + 18), (x - 10, y + 18)], fill=1)

    if prop == "revolver":
        draw.line([(x + 10, y - 12), (x + 26, y - 14)], fill=1, width=2)
        draw.line([(x + 28, y - 14), (x + 38, y - 18)], fill=1, width=1)
    elif prop == "blade":
        draw.polygon([(x + 10, y - 10), (x + 26, y - 16), (x + 14, y - 6)], fill=1)
    elif prop == "goblet":
        draw.polygon([(x + 14, y - 4), (x + 22, y - 4), (x + 18, y + 4)], fill=1)
        draw.line([(x + 18, y + 4), (x + 18, y + 10)], fill=1, width=1)

def render_scene(idx: int, sc: dict) -> bytes:
    img = Image.new("1", (W, H), 0)
    pix = img.load()
    draw = ImageDraw.Draw(img)

    # Woodcut sky / ceiling hatching
    for y in range(4, 130, 3):
        for x in range(4, W - 4):
            if (x + y * 2) % 7 == 0:
                pix[x, y] = 1

    # Deck planking perspective lines
    draw.line([(4, 130), (W - 5, 130)], fill=1, width=2)
    for y in range(136, H - 4, 8):
        draw.line([(4, y), (W - 5, y)], fill=1, width=1)
    for x in range(-80, W + 80, 45):
        draw.line([(W // 2 + (x - W // 2) // 2, 130), (x, H - 4)], fill=1, width=1)

    # Portholes or ship rails
    if sc["interior"]:
        for px in (95, 220, 345):
            draw.ellipse([px - 18, 42, px + 18, 78], fill=0, outline=1)
            draw.ellipse([px - 15, 45, px + 15, 75], outline=1)
            draw.line([(px - 15, 60), (px + 15, 60)], fill=1, width=1)
            draw.line([(px, 45), (px, 75)], fill=1, width=1)
    else:
        # Stormy sea waves & ship rail
        for x in range(10, W - 10, 16):
            draw.arc([x, 96, x + 16, 112], 0, 180, fill=1)
            draw.arc([x + 6, 108, x + 22, 124], 0, 180, fill=1)
        draw.line([(4, 115), (W - 5, 115)], fill=1, width=2)
        for rx in range(20, W - 20, 28):
            draw.line([(rx, 115), (rx, 130)], fill=1, width=2)

    # Scene-specific engraving elements
    for fig in sc["figs"]:
        draw_figure(draw, fig[0], fig[1], fig[2], fig[3])

    if sc.get("lightning", False):
        pts = [(260, 18), (235, 55), (255, 60), (220, 105), (240, 108), (205, 145)]
        draw.line(pts, fill=1, width=3)

    if sc.get("crate", False):
        draw.rectangle([195, 118, 255, 162], fill=0, outline=1)
        draw.line([(195, 118), (255, 162)], fill=1, width=2)
        draw.line([(195, 162), (255, 118)], fill=1, width=2)
        draw.line([(225, 20), (225, 118)], fill=1, width=1) # snapped chain

    if sc.get("lifeboat", False):
        draw.polygon([(260, 135), (380, 135), (360, 162), (280, 162)], fill=0, outline=1)
        draw.line([(260, 135), (380, 135)], fill=1, width=2)

    # Callout Evidence Labels (3 boxed forensic markers)
    for cx, cy, label in sc["callouts"]:
        bbox = draw.textbbox((0, 0), label, font=FONT_SM)
        tw = bbox[2] - bbox[0] + 6
        th = bbox[3] - bbox[1] + 4
        draw.rectangle([cx, cy, cx + tw, cy + th], fill=0, outline=1)
        draw.text((cx + 3, cy + 1), label, fill=1, font=FONT_SM)

    # Top-left Memento Mortem Cartouche
    hdr = f" SCENE {idx + 1:02d}/10 | {sc['loc']} "
    bbox = draw.textbbox((0, 0), hdr, font=FONT_MD)
    cw = bbox[2] - bbox[0] + 6
    ch = bbox[3] - bbox[1] + 4
    draw.rectangle([4, 4, 4 + cw, 4 + ch], fill=0, outline=1)
    draw.text((7, 5), hdr, fill=1, font=FONT_MD)

    # Double border
    draw.rectangle([0, 0, W - 1, H - 1], outline=1)
    draw.rectangle([2, 2, W - 3, H - 3], outline=1)

    buf = bytearray(W * H // 8)
    for y in range(H):
        row_off = y * (W // 8)
        for x in range(W):
            if pix[x, y]:
                buf[row_off + (x >> 3)] |= (0x80 >> (x & 7))
    return bytes(buf)

SCENES = [
    # Scene 1: Purser Giancarlo Neri (4) -> Poisoned (1) by Dr. Enrico Fermi-Lombardi (4)
    {
        "title": "I. THE BITTER APERITIVO (21:15)",
        "loc": "OFFICERS' SALOON",
        "clues": "Victim wears the Purser's double-breasted ledger coat and clutches a spilled goblet smelling of bitter almonds. Only the ship's physician had the key to the cyanide cabinet.",
        "audio": "[POCKET WATCH 21:15] \"Drink up, Giancarlo! Once you audit my medical opium manifests in Brindisi, we are both ruined...\" — \"Enrico, this Marsala tastes of bitter almonds—my throat—!\"",
        "who": 4, "fate": 1, "killer": 4,
        "interior": True,
        "figs": [(160, 132, "standing", ""), (250, 140, "slumped", "goblet")],
        "callouts": [(255, 95, "BITTER ALMOND GOBLET"), (85, 85, "MEDICAL BAG"), (275, 168, "PURSER'S LEDGER KEY")],
    },
    # Scene 2: Telegraphist Luca Bini (8) -> Electrocuted by dynamo (6) by Chief Eng. Bruno Sarti (5)
    {
        "title": "II. SILENCING THE SPARK (21:40)",
        "loc": "MARCONI WIRELESS CABIN",
        "clues": "Victim wears telegraph headphones fused to his temples. The high-voltage auxiliary dynamo cable was deliberately cross-wired into the Morse key from the engine bulkhead.",
        "audio": "[POCKET WATCH 21:40] \"Sarti, stop! I'm wiring the Coast Guard about the stolen gold bullion!\" — \"Touch that brass Morse key, boy, and my 600-volt turbine dynamo will fry your ears!\"",
        "who": 8, "fate": 6, "killer": 5,
        "interior": True,
        "figs": [(145, 130, "standing", ""), (265, 138, "slumped", "")],
        "lightning": True,
        "callouts": [(255, 82, "600V DYNAMO WIRE"), (280, 162, "MORSE HEADSET"), (75, 90, "ENGINEER WRENCH")],
    },
    # Scene 3: Bosun Matteo Rizzo (7) -> Crushed by cargo/gear (2) by None / Accident (0)
    {
        "title": "III. THE SNAP OF THE WINCH (22:05)",
        "loc": "FORWARD CARGO HOLD",
        "clues": "Victim with the Bosun's pipe and whistle lies beneath a fallen two-ton marble crate. The rusted iron hoist chain snapped cleanly during the violent Adriatic roll; no one else was on the catwalk.",
        "audio": "[POCKET WATCH 22:05] \"All hands clear the lower hatch! This gale is pitching the marble crates—watch that rusty hoist chain above my head—CRACK!\"",
        "who": 7, "fate": 2, "killer": 0,
        "interior": True,
        "crate": True,
        "figs": [(225, 148, "fallen", "")],
        "callouts": [(235, 52, "SNAPPED HOIST CHAIN"), (265, 135, "2-TON MARBLE CRATE"), (105, 155, "BOSUN'S WHISTLE")],
    },
    # Scene 4: Dr. Enrico Fermi-Lombardi (2) -> Stabbed with blade (3) by Signora Elena Grimani (7)
    {
        "title": "IV. VENGEANCE IN SILK (22:30)",
        "loc": "INFIRMARY CORRIDOR",
        "clues": "The ship's doctor lies beside his scattered surgical kit, pierced by an ornate Venetian stiletto. A black lace fan embroidered 'E.G.' is caught in his fingers.",
        "audio": "[POCKET WATCH 22:30] \"Signora Grimani! Why are you in the infirmary?\" — \"Giancarlo was my brother, Doctor. You poisoned his wine—now taste Venetian steel!\"",
        "who": 2, "fate": 3, "killer": 7,
        "interior": True,
        "figs": [(170, 132, "standing", "blade"), (260, 145, "fallen", "")],
        "callouts": [(185, 88, "VENETIAN STILETTO"), (270, 118, "SURGEON'S COAT"), (115, 165, "FAN MONOGRAM 'E.G.'")],
    },
    # Scene 5: Helmsman Pietro Corso (6) -> Struck by lightning (5) by None / Accident (0)
    {
        "title": "V. WRATH OF OTRANTO (23:00)",
        "loc": "WHEELHOUSE & BRIDGE",
        "clues": "The helmsman is fused to the brass binnacle and ship's wheel, his oilskins charred by a direct atmospheric bolt that split the mainmast lightning rod.",
        "audio": "[POCKET WATCH 23:00] \"Hold the wheel steady, Pietro! St. Elmo's fire is dancing on the mainmast—get your hands off the brass spokes—BOOM!\"",
        "who": 6, "fate": 5, "killer": 0,
        "interior": False,
        "lightning": True,
        "figs": [(205, 135, "standing", "")],
        "callouts": [(225, 32, "LIGHTNING BOLT"), (225, 145, "BRASS SHIP WHEEL"), (95, 82, "COMPASS BINNACLE")],
    },
    # Scene 6: Chief Eng. Bruno Sarti (3) -> Shot with revolver (0) by 1st Mate Marco Valli (3)
    {
        "title": "VI. MUTINY AT THE BOILERS (23:20)",
        "loc": "BOILER ROOM CATWALK",
        "clues": "The soot-stained Chief Engineer clutches a bullet wound in his chest beside the coal bunker. First Mate Valli stands over him holding a smoking service Webley revolver.",
        "audio": "[POCKET WATCH 23:20] \"We split the gold fifty-fifty, Valli! Why draw your pistol?\" — \"One share is simpler than two, Engineer. Give my regards to the furnace.\"",
        "who": 3, "fate": 0, "killer": 3,
        "interior": True,
        "figs": [(155, 130, "standing", "revolver"), (265, 145, "fallen", "")],
        "callouts": [(175, 85, "1ST MATE'S REVOLVER"), (270, 115, "CHIEF ENG. OVERALLS"), (295, 168, "STOLEN GOLD CRATE")],
    },
    # Scene 7: Signora Elena Grimani (5) -> Drowned Overboard (4) by 1st Mate Marco Valli (3)
    {
        "title": "VII. OVER THE STARBOARD RAIL (23:45)",
        "loc": "STARBOARD PROMENADE",
        "clues": "A woman in an evening gown is hurled over the broken starboard railing into the boiling sea by the First Mate after witnessing him haul the bullion chest.",
        "audio": "[POCKET WATCH 23:45] \"I saw you shoot the engineer, Mr. Valli! The Captain will hang you!\" — \"The Adriatic keeps its secrets, Signora. Over the rail you go!\"",
        "who": 5, "fate": 4, "killer": 3,
        "interior": False,
        "figs": [(185, 128, "standing", ""), (285, 138, "fallen", "")],
        "callouts": [(145, 78, "1ST MATE INSIGNIA"), (285, 88, "BROKEN RAILING"), (305, 168, "VELVET EVENING GOWN")],
    },
    # Scene 8: 1st Mate Marco Valli (1) -> Shot with revolver (0) by Capt. Lorenzo Conti (2)
    {
        "title": "VIII. CAPTAIN'S JUDGMENT (00:10)",
        "loc": "QUARTERDECK STAIRS",
        "clues": "First Mate Valli lies on the quarterdeck steps with a single naval carbine round through his collarbone. Captain Conti stands on the upper bridge rail with his rifle leveled.",
        "audio": "[POCKET WATCH 00:10] \"Drop the bullion chest, Valli! You murdered my officers and disgraced this flag!\" — \"Never, Captain—!\" [RIFLE SHOT]",
        "who": 1, "fate": 0, "killer": 2,
        "interior": False,
        "figs": [(145, 122, "standing", "revolver"), (265, 145, "fallen", "")],
        "callouts": [(85, 72, "CAPTAIN'S CARBINE"), (265, 105, "1ST MATE EPAULETTES"), (245, 168, "DROPPED PISTOL")],
    },
    # Scene 9: Stowaway Sofia Vane (9) -> Escaped in lifeboat (7) by None / Accident (0)
    {
        "title": "IX. THE LAST LIFEBOAT (00:30)",
        "loc": "AFT DAVITS & STERN",
        "clues": "A young stowaway wearing an oversized oilskin jacket lowers the stern jolly-boat into the calm eye of the squall and rows toward the Otranto lighthouse unharmed.",
        "audio": "[POCKET WATCH 00:30] \"Take the stern cutter, girl! Keep the Otranto lighthouse on your port bow and tell the harbor master what happened aboard the Esperia!\"",
        "who": 9, "fate": 7, "killer": 0,
        "interior": False,
        "lifeboat": True,
        "figs": [(315, 132, "standing", "")],
        "callouts": [(285, 82, "LOWERED JOLLY-BOAT"), (75, 78, "OTRANTO LIGHTHOUSE"), (165, 155, "STOWAWAY TICKET STUB")],
    },
    # Scene 10: Capt. Lorenzo Conti (0) -> Shot with revolver (0) by Suicide (Self-Inflicted) (1)
    {
        "title": "X. THE LOGBOOK IS CLOSED (00:55)",
        "loc": "CAPTAIN'S CHARTROOM",
        "clues": "Captain Lorenzo Conti sits alone behind his bolted oak desk, the signed ship's manifest before him and his own service revolver in his right hand.",
        "audio": "[POCKET WATCH 00:55] \"Nine souls accounted for in the log. The girl is safe in the cutter. A captain does not return to Venice without his crew. Forgive me.\"",
        "who": 0, "fate": 0, "killer": 1,
        "interior": True,
        "figs": [(220, 138, "slumped", "revolver")],
        "callouts": [(185, 78, "CAPTAIN'S CAP & COAT"), (275, 115, "OWN SERVICE REVOLVER"), (95, 158, "SIGNED SHIP MANIFEST")],
    },
]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = bytearray()
    # Header: 16 bytes
    out += struct.pack("<8sHHI", b"CNMF0001", 10, 10, 0)
    assert len(out) == 16

    # Metadata: 10*36 + 8*28 + 12*36 = 360 + 224 + 432 = 1016 bytes
    meta = bytearray()
    for name in CREW:
        meta += pack_utf8(name, 36)
    for fate in FATES:
        meta += pack_utf8(fate, 28)
    for killer in KILLERS:
        meta += pack_utf8(killer, 36)
    assert len(meta) == 1016
    out += meta

    for idx, sc in enumerate(SCENES):
        rec = bytearray()
        rec += pack_utf8(sc["title"], 48)
        rec += pack_utf8(sc["loc"], 36)
        rec += pack_utf8(sc["clues"], 220)
        rec += pack_utf8(sc["audio"], 280)
        rec += struct.pack("<BBBB", sc["who"], sc["fate"], sc["killer"], 0)
        bmp = render_scene(idx, sc)
        assert len(bmp) == 11000
        rec += bmp
        assert len(rec) == 11588, f"Scene {idx} size {len(rec)}"
        out += rec

    assert len(out) == 116912
    with open(OUT_PATH, "wb") as f:
        f.write(out)
    print(f"Wrote {OUT_PATH}: {len(out)} bytes ({len(SCENES)} scenes)")

if __name__ == "__main__":
    main()
