#pragma once

#include <FreeInkUIGfxRenderer.h>

#include <cstdint>
#include <memory>

#include "../../activities/Activity.h"
#include "../ui/ToyboxScreen.h"

namespace logos {

#pragma pack(push, 1)
struct LogosHeader {
  char magic[8];      // "CNLG0001"
  uint16_t argCount;  // 24
  uint16_t reserved1;
  uint32_t reserved2;
};

struct LogosArgument {
  char eraAndSchool[36];
  char title[48];
  char wikiTitle[48];
  char premise1[160];
  char premise2[160];
  char premise3[160];
  char conclusion[160];
  char objections[3][120];
  uint8_t bestObjection;  // 0, 1, or 2
  uint8_t reserved[3];
  char analysis[340];
};
#pragma pack(pop)

}  // namespace logos

class LogosActivity final : public Activity {
 public:
  LogosActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("Logos", renderer, mappedInput) {}
  ~LogosActivity() override = default;

  static std::unique_ptr<Activity> create(GfxRenderer& renderer, MappedInputManager& mappedInput);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  bool loadArgument(int idx);
  void saveProgress() const;
  void loadProgress();
  void routeAction(int action, int value);

  int argCount_ = 0;
  int argIdx_ = 0;
  int tab_ = 0;           // 0: Premise Tree, 1: Red-Team Objections
  int selectedObj_ = -1;  // -1: none selected yet, 0..2: chosen objection
  bool packReady_ = false;
  std::unique_ptr<logos::LogosArgument> arg_;
  toybox::Interactions interactions_;
  bool interactionsReady_ = false;
};
