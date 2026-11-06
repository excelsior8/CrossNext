#pragma once

#include <FreeInkUIGfxRenderer.h>

#include <cstdint>
#include <memory>

#include "../../activities/Activity.h"
#include "../ui/ToyboxScreen.h"

class MicroTacticsActivity final : public Activity {
 public:
  MicroTacticsActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("MicroTactics", renderer, mappedInput) {}
  ~MicroTacticsActivity() override = default;

  static std::unique_ptr<Activity> create(GfxRenderer& renderer, MappedInputManager& mappedInput);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  enum Terrain : uint8_t { Plain = 0, City = 1, Mountain = 2, Chasm = 3 };
  enum UnitKind : uint8_t { None = 0, MechTitan = 1, MechArtillery = 2, MechAegis = 3, EnemyVek = 4 };

  struct Unit {
    UnitKind kind = None;
    int8_t r = 0;
    int8_t c = 0;
    int8_t hp = 0;
    int8_t maxHp = 0;
    bool moved = false;
    bool acted = false;
    int8_t aimDr = 0;  // Enemy telegraphed attack direction
    int8_t aimDc = 0;
  };

  void startSector(int sector);
  void planEnemyIntents();
  void endPlayerTurn();
  void pushTile(int r, int c, int dr, int dc);
  void damageAt(int r, int c, int dmg);
  void handleGridTap(int r, int c);
  void routeAction(int action, int value);
  void checkVictory();
  void saveProgress() const;
  void loadProgress();

  int sector_ = 0;
  int turn_ = 1;
  int gridHp_ = 4;
  int selectedUnit_ = -1;
  bool attackMode_ = false;
  uint8_t state_ = 0;  // 0: Playing, 1: Sector Cleared, 2: Grid Destroyed
  uint16_t clearedMask_ = 0;
  Terrain board_[6][6] = {};
  Unit units_[8] = {};
  char statusMsg_[80] = {};

  toybox::Interactions interactions_;
  bool interactionsReady_ = false;
};
