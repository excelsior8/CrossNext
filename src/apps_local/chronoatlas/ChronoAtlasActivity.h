#pragma once

#include <FreeInkUIGfxRenderer.h>

#include <cstdint>
#include <memory>

#include "../../activities/Activity.h"
#include "../ui/ToyboxScreen.h"

namespace chronoatlas {

#pragma pack(push, 1)
struct AtlasHeader {
  char magic[8];      // "CNAT0001"
  uint16_t eraCount;  // 20
  uint16_t mapW;      // 440
  uint16_t mapH;      // 240
  uint16_t reserved;  // 0
};

struct AtlasItem {
  char title[36];
  char subtitle[96];
  char wikiTitle[48];
};

struct AtlasEra {
  char yearLabel[24];
  char eraTitle[48];
  char subtitle[64];
  char summary[640];
  AtlasItem powers[4];
  AtlasItem events[4];
  AtlasItem thinkers[4];
  uint8_t mapBitmap[13200];  // 440x240 1-bit MSB-first, 55 bytes/row, 1=black
};
#pragma pack(pop)

}  // namespace chronoatlas

class ChronoAtlasActivity final : public Activity {
 public:
  ChronoAtlasActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("ChronoAtlas", renderer, mappedInput) {}
  ~ChronoAtlasActivity() override = default;

  static std::unique_ptr<Activity> create(GfxRenderer& renderer, MappedInputManager& mappedInput);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  bool loadEra(int idx);
  void saveProgress() const;
  void loadProgress();
  void routeAction(int action, int value);
  void drawMap(int x0, int y0) const;

  int mode_ = 0;  // 0: Historical Atlas (/chronoatlas/atlas.bin), 1: World City & POI Atlas (/chronoatlas/cities.bin)
  int eraCount_ = 0;
  int eraIdx_ = 0;
  int tab_ = 0;
  bool packReady_ = false;
  std::unique_ptr<chronoatlas::AtlasEra> era_;
  toybox::Interactions interactions_;
  bool interactionsReady_ = false;
};
