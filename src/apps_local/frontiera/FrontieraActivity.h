#pragma once

#include <FreeInkUIGfxRenderer.h>

#include <cstdint>
#include <memory>

#include "../../activities/Activity.h"
#include "../ui/ToyboxScreen.h"

namespace frontiera {

#pragma pack(push, 1)
struct FrontieraHeader {
  char magic[8];       // "CNFR0001"
  uint16_t caseCount;  // 20
  uint16_t reserved1;  // 0
  uint32_t reserved2;  // 0
};

struct FrontieraCase {
  char dayDate[16];
  char applicantName[36];
  char nationality[24];
  char issuingCity[24];
  char passportNo[16];
  char expiryDate[16];
  uint8_t shouldApprove;   // 1 = APPROVE, 0 = DENY
  uint8_t hasPermitStamp;  // 1 = OFFICIAL SEAL, 0 = FORGED/MISSING SEAL
  uint16_t weightKg;
  char rulesEn[220];
  char rulesIt[220];
  char docPermitEn[160];
  char docPermitIt[160];
  char dialogueEn[180];
  char dialogueIt[180];
  char auditEn[180];
  char auditIt[180];
  uint8_t portrait[1800];  // 120x120 1-bit MSB-first, 15 bytes/row
};
#pragma pack(pop)

}  // namespace frontiera

class FrontieraActivity final : public Activity {
 public:
  FrontieraActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("Frontiera", renderer, mappedInput) {}
  ~FrontieraActivity() override = default;

  static std::unique_ptr<Activity> create(GfxRenderer& renderer, MappedInputManager& mappedInput);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  bool loadCase(int idx);
  void saveProgress() const;
  void loadProgress();
  void routeAction(int action, int value);
  void drawPortrait(int x0, int y0) const;

  int caseCount_ = 0;
  int caseIdx_ = 0;
  bool italian_ = false;  // false = English (primary), true = Italian
  bool stamped_ = false;
  bool lastStampApprove_ = false;
  bool lastCorrect_ = false;
  uint16_t correctMask_ = 0;
  uint16_t attemptedMask_ = 0;
  bool packReady_ = false;
  std::unique_ptr<frontiera::FrontieraCase> cur_;
  toybox::Interactions interactions_;
  bool interactionsReady_ = false;
};
