#include <HalStorage.h>

#include <cstdio>
#include <cstring>

#include "InterceptCore.h"
namespace intercept {
namespace {
constexpr char defaultPath[] = "/.crosspoint/intercept.dat";
constexpr char storiesPath[] = "/apps/intercept/stories.bin";
void makeSavePath(char* out, size_t size, const char* slug) {
  if (!slug || !slug[0]) {
    std::snprintf(out, size, "%s", defaultPath);
  } else {
    std::snprintf(out, size, "/.crosspoint/int_%s.dat", slug);
  }
}
uint16_t le16(const uint8_t* p) { return uint16_t(p[0]) | (uint16_t(p[1]) << 8); }
uint32_t le32(const uint8_t* p) { return uint32_t(le16(p)) | (uint32_t(le16(p + 2)) << 16); }
}  // namespace
bool load(State& s, bool& writable, const char* slug, uint16_t maxNodes) {
  s = {};
  writable = true;
  char path[64];
  makeSavePath(path, sizeof(path), slug);
  if (!Storage.exists(path)) return true;
  HalFile f;
  if (!Storage.openFileForRead("INTERCEPT", path, f)) {
    writable = false;
    return false;
  }
  State candidate;
  uint8_t bytes[32];
  bool found = false;
  for (int n = 0; n < 2; ++n) {
    if (f.read(bytes, 32) != 32) break;
    if (!std::memcmp(bytes, "INT", 3) && bytes[3] != '1') {
      writable = false;
      return false;
    }
    if (decode(bytes, candidate, maxNodes) && (!found || int32_t(candidate.sequence - s.sequence) > 0)) {
      s = candidate;
      found = true;
    }
  }
  if (!found) writable = false;
  return found;
}
bool save(State& s, bool writable, const char* slug, uint16_t maxNodes) {
  if (!writable) return false;
  Storage.ensureDirectoryExists("/.crosspoint");
  char path[64];
  makeSavePath(path, sizeof(path), slug);
  HalFile f;
  if (!(f = Storage.open(path, O_RDWR | O_CREAT))) return false;
  auto next = s;
  ++next.sequence;
  uint8_t bytes[32];
  encode(next, bytes);
  const auto offset = (next.sequence - 1) % 2 * 32;
  if (!f.seekSet(offset) || f.write(bytes, 32) != 32) return false;
  f.flush();
  State check;
  if (!f.seekSet(offset) || f.read(bytes, 32) != 32 || !decode(bytes, check, maxNodes) ||
      check.sequence != next.sequence)
    return false;
  s.sequence = next.sequence;
  return true;
}
unsigned loadCatalog(StoryMeta* out, unsigned maxCount) {
  if (!out || !maxCount || !Storage.exists(storiesPath)) return 0;
  HalFile f;
  if (!Storage.openFileForRead("INTERCEPT", storiesPath, f)) return 0;
  uint8_t header[16];
  if (f.read(header, sizeof(header)) != int(sizeof(header))) return 0;
  if (std::memcmp(header, "CNST0001", 8) != 0) return 0;
  const unsigned count = std::min<unsigned>(le16(header + 8), maxCount);
  const uint32_t totalBytes = le32(header + 12);
  if (!count || f.fileSize64() != totalBytes) return 0;
  for (unsigned i = 0; i < count; ++i) {
    uint8_t raw[256];
    if (f.read(raw, sizeof(raw)) != int(sizeof(raw))) return i;
    StoryMeta& m = out[i];
    std::memcpy(m.slug, raw, 24);
    m.slug[23] = '\0';
    std::memcpy(m.title, raw + 24, 40);
    m.title[39] = '\0';
    std::memcpy(m.subtitle, raw + 64, 48);
    m.subtitle[47] = '\0';
    std::memcpy(m.tagline, raw + 112, 128);
    m.tagline[127] = '\0';
    m.nodeOffset = le32(raw + 240);
    m.nodeCount = le16(raw + 244);
    m.coverScene = le16(raw + 246);
  }
  return count;
}
bool loadDiskNode(const StoryMeta& meta, uint16_t nodeIndex, DiskNode& out) {
  out = {};
  if (nodeIndex >= meta.nodeCount || !Storage.exists(storiesPath)) return false;
  HalFile f;
  if (!Storage.openFileForRead("INTERCEPT", storiesPath, f)) return false;
  const uint32_t offset = meta.nodeOffset + uint32_t(nodeIndex) * 652u;
  if (!f.seekSet(offset)) return false;
  uint8_t raw[652];
  if (f.read(raw, sizeof(raw)) != int(sizeof(raw))) return false;
  std::memcpy(out.title, raw, 44);
  out.title[43] = '\0';
  std::memcpy(out.text, raw + 44, 380);
  out.text[379] = '\0';
  for (int k = 0; k < 3; ++k) {
    const uint8_t* c = raw + 424 + k * 74;
    std::memcpy(out.choices[k].label, c, 64);
    out.choices[k].label[63] = '\0';
    out.choices[k].next = le16(c + 64);
    out.choices[k].require = le16(c + 66);
    out.choices[k].forbid = le16(c + 68);
    out.choices[k].set = le16(c + 70);
    out.choices[k].clear = le16(c + 72);
  }
  out.count = std::min<uint8_t>(raw[646], 3);
  out.scene = raw[647];
  out.ending = raw[648];
  return true;
}
}  // namespace intercept
