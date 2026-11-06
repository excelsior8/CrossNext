#pragma once

#include <FreeInkUIGfxRenderer.h>

#include <cstdint>
#include <memory>
#include <vector>

#include "../../activities/Activity.h"
#include "../ui/ToyboxScreen.h"

namespace bilingual {

#pragma pack(push, 1)
struct BilingualHeader {
  char magic[8];          // "CNBL0001"
  uint16_t textCount;     // 12
  uint16_t totalSegments; // 168
  uint32_t reserved;      // 0
};

struct StoryMeta {
  char title[48];
  char subtitle[48];
  char level[8];
  uint16_t firstSegment;
  uint16_t segmentCount;
  uint8_t reserved[20];
};

struct Segment {
  char itText[220];
  char trText[220];
  char enText[160];
  char vocabNote[104];
  char cardFront[32];
  char cardBack[32];
};
#pragma pack(pop)

}  // namespace bilingual

class BilingualActivity final : public Activity {
 public:
  BilingualActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("Bilingual", renderer, mappedInput) {}
  ~BilingualActivity() override = default;

  static std::unique_ptr<Activity> create(GfxRenderer& renderer, MappedInputManager& mappedInput);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  bool loadCatalog();
  bool loadSegment(int storyIdx, int segIdx);
  void saveProgress() const;
  void loadProgress();
  bool exportFlashcard();
  void routeAction(int action, int value);

  std::vector<bilingual::StoryMeta> stories_;
  std::unique_ptr<bilingual::Segment> seg_;
  bool packReady_ = false;
  bool inStory_ = false;
  int listPage_ = 0;
  int storyIdx_ = 0;
  int segIdx_ = 0;
  int mode_ = 0;  // 0: TR + Vocab, 1: EN + Vocab, 2: Quiz (Hidden)
  bool cardSaved_ = false;
  uint8_t savedSegByStory_[16] = {};

  toybox::Interactions interactions_;
  bool interactionsReady_ = false;
};
