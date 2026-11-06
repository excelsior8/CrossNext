#pragma once

#include <FreeInkUIGfxRenderer.h>

#include <cstdint>
#include <memory>

#include "../../activities/Activity.h"
#include "../ui/ToyboxScreen.h"

namespace manifest {

#pragma pack(push, 1)
struct ManifestHeader {
  char magic[8];        // "CNMF0001"
  uint16_t sceneCount;  // 10
  uint16_t crewCount;   // 10
  uint32_t reserved;    // 0
};

struct ManifestMetadata {
  char crewNames[10][36];
  char fateNames[8][28];
  char killerNames[12][36];
};

struct ManifestScene {
  char chapterTitle[48];
  char location[36];
  char clueSummary[220];
  char transcript[280];
  uint8_t correctWho;
  uint8_t correctFate;
  uint8_t correctKiller;
  uint8_t reserved;
  uint8_t sceneBitmap[11000];  // 440x200 1-bit MSB-first, 55 bytes/row
};
#pragma pack(pop)

}  // namespace manifest

class ManifestActivity final : public Activity {
 public:
  ManifestActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("Manifest", renderer, mappedInput) {}
  ~ManifestActivity() override = default;

  static std::unique_ptr<Activity> create(GfxRenderer& renderer, MappedInputManager& mappedInput);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  bool loadScene(int idx);
  void saveProgress() const;
  void loadProgress();
  void routeAction(int action, int value);
  void drawSceneBitmap(int x0, int y0) const;

  int sceneCount_ = 0;
  int sceneIdx_ = 0;
  int tab_ = 0;  // 0: Clues & Memory, 1: Deduce Fate
  uint8_t guessWho_[10] = {};
  uint8_t guessFate_[10] = {};
  uint8_t guessKiller_[10] = {};
  uint16_t solvedMask_ = 0;
  int8_t lastCheckHits_ = -1;  // -1 = not checked yet on this view, 0..3 = number of matching fields
  bool packReady_ = false;
  std::unique_ptr<manifest::ManifestMetadata> meta_;
  std::unique_ptr<manifest::ManifestScene> scene_;
  toybox::Interactions interactions_;
  bool interactionsReady_ = false;
};
