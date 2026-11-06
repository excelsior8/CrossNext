#pragma once
#include <I18n.h>

#include <cstdint>
namespace intercept {
enum Flag : uint16_t { Component = 1, Cooperative = 2, Lied = 4, BrokenWindow = 8, Proof = 16, Returned = 32 };
enum class Ending : uint8_t { None, Free, Suspicion, Captured, Escape, Betrayed };
struct Choice {
  StrId label;
  uint16_t next, require, forbid, set, clear;
};
struct Node {
  StrId title, text;
  Choice choices[3];
  uint8_t count, scene;
  Ending ending;
};
extern const Node nodes[];
extern const uint16_t nodeCount;

inline constexpr unsigned MAX_EXTRA_STORIES = 15;
struct StoryMeta {
  char slug[24]{};
  char title[40]{};
  char subtitle[48]{};
  char tagline[128]{};
  uint32_t nodeOffset = 0;
  uint16_t nodeCount = 0;
  uint16_t coverScene = 0;
  uint8_t reserved[8]{};
};
struct DiskChoice {
  char label[64]{};
  uint16_t next = 0, require = 0, forbid = 0, set = 0, clear = 0;
};
struct DiskNode {
  char title[44]{};
  char text[380]{};
  DiskChoice choices[3]{};
  uint8_t count = 0, scene = 0, ending = 0;
  uint8_t pad[3]{};
};

struct State {
  uint32_t sequence = 0;
  uint16_t node = 0, flags = 0;
  uint32_t choices = 0;
};
bool allowed(const State&, unsigned choice);
bool choose(State&, unsigned choice);
bool allowedDisk(const State&, const DiskNode&, uint16_t totalNodes, unsigned choice);
bool chooseDisk(State&, const DiskNode&, uint16_t totalNodes, unsigned choice);
void encode(const State&, uint8_t*);
bool decode(const uint8_t*, State&, uint16_t maxNodes = nodeCount);
bool load(State&, bool& writable, const char* slug = nullptr, uint16_t maxNodes = nodeCount);
bool save(State&, bool writable, const char* slug = nullptr, uint16_t maxNodes = nodeCount);
unsigned loadCatalog(StoryMeta* out, unsigned maxCount);
bool loadDiskNode(const StoryMeta& meta, uint16_t nodeIndex, DiskNode& out);
}  // namespace intercept
