#!/usr/bin/env python3
"""
Compile JSON interactive fiction stories from scratch/stories_json/*.json
into /apps/intercept/stories.bin (CNST0001 binary archive) for CrossNext X4 Pro.
"""
import glob
import json
import os
import struct

STORIES_DIR = "./sd_out"
OUT_PATHS = [
    "./sd_out",
    "./sd_out",
]

ENDINGS = {
    "none": 0,
    "free": 1,
    "suspicion": 2,
    "captured": 3,
    "escape": 4,
    "betrayed": 5,
}

# Normalize Turkish chars outside Latin-1 (0x00..0xFF) so ui_prose_14 renders 100% cleanly
TR_MAP = str.maketrans({
    "ğ": "g", "Ğ": "G",
    "ı": "i", "İ": "I",
    "ş": "s", "Ş": "S",
    "—": "-", "–": "-",
    "“": '"', "”": '"',
    "‘": "'", "’": "'",
    "…": "...", "•": "-",
})

def clean_str(s: str, max_bytes: int) -> bytes:
    s = (s or "").translate(TR_MAP).strip()
    # Keep only codepoints <= 0xFF (ASCII + Latin-1, which covers Italian àèéìòù & çöü)
    cleaned = "".join(ch if ord(ch) <= 0xFF else "?" for ch in s)
    b = cleaned.encode("utf-8")
    if len(b) >= max_bytes:
        # Truncate safely on UTF-8 boundary
        b = b[: max_bytes - 1]
        while b and (b[-1] & 0xC0) == 0x80:
            b = b[:-1]
        if b and (b[-1] & 0xE0) == 0xC0:
            b = b[:-1]
    return b.ljust(max_bytes, b"\x00")


def pack_node(node: dict, total_nodes: int) -> bytes:
    title_b = clean_str(node.get("title", "SCENE"), 44)
    text_b = clean_str(node.get("text", ""), 380)
    choices = node.get("choices", [])[:3]
    choices_b = bytearray()
    for k in range(3):
        if k < len(choices):
            c = choices[k]
            lbl = clean_str(c.get("label", "Continue"), 64)
            nxt = max(0, min(total_nodes - 1, int(c.get("next", 0))))
            req = int(c.get("require", 0)) & 0xFFFF
            frb = int(c.get("forbid", 0)) & 0xFFFF
            st = int(c.get("set", 0)) & 0xFFFF
            clr = int(c.get("clear", 0)) & 0xFFFF
            choices_b += lbl + struct.pack("<HHHHH", nxt, req, frb, st, clr)
        else:
            choices_b += b"\x00" * 74
    assert len(choices_b) == 222
    count = len(choices)
    scene = max(0, min(45, int(node.get("scene", 0))))
    ending_str = str(node.get("ending", "none")).lower()
    ending = ENDINGS.get(ending_str, 0)
    if count == 0 and ending == 0:
        ending = 1
    tail = struct.pack("<BBBBBB", count, scene, ending, 0, 0, 0)
    record = title_b + text_b + bytes(choices_b) + tail
    assert len(record) == 652, f"Expected 652 bytes, got {len(record)}"
    return record


def main():
    json_files = sorted(glob.glob(os.path.join(STORIES_DIR, "*.json")))
    if not json_files:
        print("No JSON files found in", STORIES_DIR)
        return

    stories = []
    for jf in json_files[:15]:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
        nodes = data.get("nodes", [])
        if not nodes:
            continue
        stories.append((jf, data))

    count = len(stories)
    header_size = 16
    meta_table_size = count * 256
    current_offset = header_size + meta_table_size

    meta_bytes = bytearray()
    nodes_bytes = bytearray()

    for jf, data in stories:
        nodes = data["nodes"]
        n_count = len(nodes)
        slug = clean_str(data.get("slug", os.path.splitext(os.path.basename(jf))[0]), 24)
        title = clean_str(data.get("title", "STORY"), 40)
        subtitle = clean_str(data.get("subtitle", "Interactive Fiction"), 48)
        tagline = clean_str(data.get("tagline", ""), 128)
        cover_scene = max(0, min(45, int(data.get("cover_scene", nodes[0].get("scene", 0)))))

        meta_rec = (
            slug
            + title
            + subtitle
            + tagline
            + struct.pack("<IHH8s", current_offset, n_count, cover_scene, b"\x00" * 8)
        )
        assert len(meta_rec) == 256
        meta_bytes += meta_rec

        for nd in nodes:
            nodes_bytes += pack_node(nd, n_count)

        print(
            f"Packed {os.path.basename(jf)}: '{data.get('title')}' "
            f"({n_count} nodes, offset {current_offset})"
        )
        current_offset += n_count * 652

    total_bytes = header_size + len(meta_bytes) + len(nodes_bytes)
    header = struct.pack("<8sHHI", b"CNST0001", count, 0, total_bytes)
    archive = header + meta_bytes + nodes_bytes
    assert len(archive) == total_bytes

    for out_p in OUT_PATHS:
        os.makedirs(os.path.dirname(out_p), exist_ok=True)
        with open(out_p, "wb") as f:
            f.write(archive)
        print(f"Wrote {out_p} ({total_bytes:,} bytes, {count} stories)")


if __name__ == "__main__":
    main()
