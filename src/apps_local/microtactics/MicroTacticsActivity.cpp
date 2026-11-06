#include "MicroTacticsActivity.h"

#include <HalStorage.h>
#include <Logging.h>
#include <Memory.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

#include "../../CrossPointSettings.h"
#include "../../activities/RenderLock.h"
#include "../../fontIds.h"
#include "../Shelf.h"
#include "../ui/ToyboxTheme.h"
#include "components/SideButtonNavigation.h"

namespace fui = freeink::ui;

namespace {

constexpr const char* kTag = "TACTICS";
constexpr const char* kStatePath = "/.crosspoint/microtactics.bin";
constexpr int16_t kMargin = 16;
constexpr int kSectorCount = 12;
constexpr int16_t kGridX = 24;
constexpr int16_t kGridY = 126;
constexpr int16_t kCell = 72;  // 6 * 72 = 432px

enum : fui::ActionId {
  ActionPrevSector = 1,
  ActionNextSector = 2,
  ActionToggleAttack = 3,
  ActionEndTurn = 4,
  ActionResetSector = 5,
};

fui::TextStyle makeStyle(const fui::FontId font, const fui::TextAlign align = fui::TextAlign::Left,
                         const fui::Color color = fui::Color::Black, const uint8_t maxLines = 1,
                         const bool bold = false) {
  fui::TextStyle s;
  s.font = font;
  s.align = align;
  s.color = color;
  s.maxLines = maxLines;
  s.bold = bold;
  return s;
}

void drawButton(toybox::Screen& screen, const fui::Rect& box, const char* label, const fui::ActionId action,
                const int16_t value, const bool filled) {
  if (filled) {
    screen.target().fill(box, fui::Paint::solid(fui::Color::Black));
  } else {
    screen.target().stroke(box, fui::Paint::solid(fui::Color::Black), 2);
  }
  const fui::TextStyle style =
      makeStyle(toybox::kSmallFont, fui::TextAlign::Center, filled ? fui::Color::White : fui::Color::Black, 1);
  screen.target().text(toybox::inkCentred(screen.target(), box, style), label, style);
  screen.frame().hit(box, action, value);
}

}  // namespace

std::unique_ptr<Activity> MicroTacticsActivity::create(GfxRenderer& renderer, MappedInputManager& mappedInput) {
  return makeUniqueNoThrow<MicroTacticsActivity>(renderer, mappedInput);
}

void MicroTacticsActivity::onEnter() {
  Activity::onEnter();
  toybox::ensureFonts(renderer);
  loadProgress();
  startSector(sector_);
  interactionsReady_ = false;
  requestUpdate();
}

void MicroTacticsActivity::onExit() {
  saveProgress();
  Activity::onExit();
}

void MicroTacticsActivity::loadProgress() {
  HalFile f;
  if (!Storage.exists(kStatePath) || !Storage.openFileForRead(kTag, kStatePath, f)) return;
  uint8_t buf[3] = {};
  if (f.read(buf, 3) == 3) {
    sector_ = buf[0] < kSectorCount ? buf[0] : 0;
    clearedMask_ = static_cast<uint16_t>(buf[1] | (buf[2] << 8));
  }
}

void MicroTacticsActivity::saveProgress() const {
  HalFile f;
  if (!Storage.openFileForWrite(kTag, kStatePath, f)) return;
  const uint8_t buf[3] = {
      static_cast<uint8_t>(sector_),
      static_cast<uint8_t>(clearedMask_ & 0xFF),
      static_cast<uint8_t>((clearedMask_ >> 8) & 0xFF),
  };
  f.write(buf, 3);
}

void MicroTacticsActivity::startSector(int sector) {
  if (sector < 0) sector = kSectorCount - 1;
  if (sector >= kSectorCount) sector = 0;
  sector_ = sector;
  turn_ = 1;
  gridHp_ = 4;
  selectedUnit_ = 0;
  attackMode_ = false;
  state_ = 0;

  for (int r = 0; r < 6; ++r)
    for (int c = 0; c < 6; ++c) board_[r][c] = Plain;
  for (auto& u : units_) u = Unit{};

  // Deterministic sector terrain layout from sector index
  const uint32_t seed = static_cast<uint32_t>(sector_ + 1) * 2654435761u;
  board_[1][(seed >> 2) % 3 + 1] = City;
  board_[2][(seed >> 5) % 2 + 1] = City;
  board_[3][(seed >> 7) % 2 + 2] = City;
  board_[4][(seed >> 11) % 3 + 1] = City;
  board_[0][(seed >> 13) % 4 + 1] = Mountain;
  board_[5][(seed >> 17) % 4 + 1] = Mountain;
  board_[(seed >> 19) % 2 + 2][0] = Chasm;
  board_[(seed >> 23) % 2 + 1][5] = Chasm;

  // Place Player Squad (3 Mechs) on bottom/left rows
  const int8_t startCoords[3][2] = {{4, 1}, {4, 3}, {3, 1}};
  const UnitKind kinds[3] = {MechTitan, MechArtillery, MechAegis};
  for (int i = 0; i < 3; ++i) {
    int r = startCoords[i][0];
    int c = startCoords[i][1];
    if (board_[r][c] != Plain) board_[r][c] = Plain;
    units_[i] = {kinds[i], static_cast<int8_t>(r), static_cast<int8_t>(c), 3, 3, false, false, 0, 0};
  }

  // Place 3..4 Enemies on top/right rows
  const int enemyCount = (sector_ >= 4) ? 4 : 3;
  const int8_t eCoords[4][2] = {{1, 4}, {2, 4}, {0, 3}, {3, 4}};
  for (int e = 0; e < enemyCount; ++e) {
    int r = eCoords[e][0];
    int c = (eCoords[e][1] + (sector_ % 2)) % 5 + 1;
    if (board_[r][c] != Plain) board_[r][c] = Plain;
    const int8_t hp = static_cast<int8_t>((sector_ >= 6 && e == 0) ? 3 : 2);
    units_[3 + e] = {EnemyVek, static_cast<int8_t>(r), static_cast<int8_t>(c), hp, hp, false, false, 0, 0};
  }

  planEnemyIntents();
  snprintf(statusMsg_, sizeof(statusMsg_), "Tap a Mech (T/A/S), move, then push Vek off their targets!");
}

void MicroTacticsActivity::planEnemyIntents() {
  static const int8_t kDirs[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
  for (int i = 3; i < 8; ++i) {
    auto& e = units_[i];
    if (e.kind != EnemyVek || e.hp <= 0) continue;
    e.aimDr = 0;
    e.aimDc = -1;  // default aim left
    // Look for an adjacent City or Mech to threaten; if none, step 1 tile closer to nearest City/Mech first
    bool foundAdj = false;
    for (int pass = 0; pass < 2 && !foundAdj; ++pass) {
      for (const auto& d : kDirs) {
        const int nr = e.r + d[0];
        const int nc = e.c + d[1];
        if (nr < 0 || nr >= 6 || nc < 0 || nc >= 6) continue;
        if (board_[nr][nc] == City) {
          e.aimDr = d[0];
          e.aimDc = d[1];
          foundAdj = true;
          break;
        }
        for (int m = 0; m < 3; ++m) {
          if (units_[m].kind != None && units_[m].hp > 0 && units_[m].r == nr && units_[m].c == nc) {
            e.aimDr = d[0];
            e.aimDc = d[1];
            foundAdj = true;
            break;
          }
        }
      }
      if (!foundAdj && pass == 0) {
        // Move 1 step toward center
        for (const auto& d : kDirs) {
          const int nr = e.r + d[0];
          const int nc = e.c + d[1];
          if (nr < 0 || nr >= 6 || nc < 0 || nc >= 6 || board_[nr][nc] != Plain) continue;
          bool occ = false;
          for (const auto& u : units_)
            if (u.kind != None && u.hp > 0 && u.r == nr && u.c == nc) occ = true;
          if (!occ && (std::abs(nr - 2) + std::abs(nc - 2) < std::abs(e.r - 2) + std::abs(e.c - 2))) {
            e.r = static_cast<int8_t>(nr);
            e.c = static_cast<int8_t>(nc);
            break;
          }
        }
      }
    }
  }
}

void MicroTacticsActivity::damageAt(const int r, const int c, const int dmg) {
  if (r < 0 || r >= 6 || c < 0 || c >= 6) return;
  if (board_[r][c] == City && dmg > 0) {
    gridHp_ = std::max(0, gridHp_ - dmg);
  }
  for (auto& u : units_) {
    if (u.kind != None && u.hp > 0 && u.r == r && u.c == c) {
      u.hp = static_cast<int8_t>(std::max(0, static_cast<int>(u.hp) - dmg));
      if (u.hp == 0) u.kind = None;
    }
  }
}

void MicroTacticsActivity::pushTile(const int r, const int c, const int dr, const int dc) {
  int uIdx = -1;
  for (int i = 0; i < 8; ++i) {
    if (units_[i].kind != None && units_[i].hp > 0 && units_[i].r == r && units_[i].c == c) {
      uIdx = i;
      break;
    }
  }
  if (uIdx < 0) return;

  const int nr = r + dr;
  const int nc = c + dc;
  if (nr < 0 || nr >= 6 || nc < 0 || nc >= 6 || board_[nr][nc] == Mountain || board_[nr][nc] == City) {
    // Collision with wall/mountain/city: 1 bump damage to pushed unit!
    damageAt(r, c, 1);
    return;
  }
  for (int i = 0; i < 8; ++i) {
    if (units_[i].kind != None && units_[i].hp > 0 && units_[i].r == nr && units_[i].c == nc) {
      // Collision between two units: 1 damage to both!
      damageAt(r, c, 1);
      damageAt(nr, nc, 1);
      return;
    }
  }
  units_[uIdx].r = static_cast<int8_t>(nr);
  units_[uIdx].c = static_cast<int8_t>(nc);
  if (board_[nr][nc] == Chasm) {
    units_[uIdx].hp = 0;
    units_[uIdx].kind = None;
  }
}

void MicroTacticsActivity::checkVictory() {
  if (gridHp_ <= 0) {
    state_ = 2;
    snprintf(statusMsg_, sizeof(statusMsg_), "GRID DESTROYED! Tap RESET to try again.");
    return;
  }
  bool anyEnemy = false;
  for (int i = 3; i < 8; ++i) {
    if (units_[i].kind == EnemyVek && units_[i].hp > 0) anyEnemy = true;
  }
  if (!anyEnemy || turn_ > 4) {
    state_ = 1;
    clearedMask_ |= static_cast<uint16_t>(1u << sector_);
    saveProgress();
    snprintf(statusMsg_, sizeof(statusMsg_), "SECTOR CLEARED! Tap > for the next sector.");
  }
}

void MicroTacticsActivity::endPlayerTurn() {
  if (state_ != 0) return;
  // Execute telegraphed Enemy attacks from their CURRENT positions
  for (int i = 3; i < 8; ++i) {
    const auto& e = units_[i];
    if (e.kind != EnemyVek || e.hp <= 0) continue;
    const int tr = e.r + e.aimDr;
    const int tc = e.c + e.aimDc;
    damageAt(tr, tc, 1);
  }
  ++turn_;
  for (int i = 0; i < 3; ++i) {
    units_[i].moved = false;
    units_[i].acted = false;
  }
  attackMode_ = false;
  checkVictory();
  if (state_ == 0) {
    planEnemyIntents();
    snprintf(statusMsg_, sizeof(statusMsg_), "Turn %d/4: Reposition Mechs & push Vek off targets!", turn_);
  }
}

void MicroTacticsActivity::handleGridTap(const int r, const int c) {
  if (state_ != 0) return;
  // Tapping one of our Mechs selects it
  for (int i = 0; i < 3; ++i) {
    if (units_[i].kind != None && units_[i].hp > 0 && units_[i].r == r && units_[i].c == c) {
      selectedUnit_ = i;
      attackMode_ = units_[i].moved && !units_[i].acted;
      const char* names[4] = {"", "TITAN (Punch+Push)", "ARTILLERY (Lob+Push 4)", "AEGIS (Push All 4)"};
      snprintf(statusMsg_, sizeof(statusMsg_), "%s selected. %s", names[units_[i].kind],
               attackMode_ ? "Tap target direction!" : "Tap tile to move (range 3) or ACT.");
      interactionsReady_ = false;
      requestUpdate();
      return;
    }
  }

  if (selectedUnit_ < 0 || selectedUnit_ >= 3) return;
  auto& m = units_[selectedUnit_];
  if (m.kind == None || m.hp <= 0) return;

  const int dist = std::abs(r - m.r) + std::abs(c - m.c);
  if (!attackMode_ && !m.moved) {
    bool occ = (board_[r][c] != Plain);
    for (const auto& u : units_)
      if (u.kind != None && u.hp > 0 && u.r == r && u.c == c) occ = true;
    if (!occ && dist >= 1 && dist <= 3) {
      m.r = static_cast<int8_t>(r);
      m.c = static_cast<int8_t>(c);
      m.moved = true;
      attackMode_ = !m.acted;
      snprintf(statusMsg_, sizeof(statusMsg_), "Moved! Now tap a target tile to fire/push.");
      interactionsReady_ = false;
      requestUpdate();
      return;
    }
  }

  if (!m.acted && (r == m.r || c == m.c) && dist >= 1) {
    const int dr = (r > m.r) ? 1 : (r < m.r ? -1 : 0);
    const int dc = (c > m.c) ? 1 : (c < m.c ? -1 : 0);
    if (m.kind == MechTitan && dist == 1) {
      damageAt(r, c, 1);
      pushTile(r, c, dr, dc);
      m.acted = true;
      attackMode_ = false;
      snprintf(statusMsg_, sizeof(statusMsg_), "TITAN kinetic punch executed!");
    } else if (m.kind == MechArtillery && dist >= 2 && dist <= 4) {
      damageAt(r, c, 1);
      static const int8_t kAdj[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
      for (const auto& d : kAdj) pushTile(r + d[0], c + d[1], d[0], d[1]);
      m.acted = true;
      attackMode_ = false;
      snprintf(statusMsg_, sizeof(statusMsg_), "ARTILLERY shock mortar landed!");
    } else if (m.kind == MechAegis && dist == 1) {
      static const int8_t kAdj[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
      for (const auto& d : kAdj) pushTile(m.r + d[0], m.c + d[1], d[0], d[1]);
      m.acted = true;
      attackMode_ = false;
      snprintf(statusMsg_, sizeof(statusMsg_), "AEGIS repulse wave pushed all adjacent tiles!");
    }
    checkVictory();
    interactionsReady_ = false;
    requestUpdate();
  }
}

void MicroTacticsActivity::routeAction(const int action, const int) {
  switch (action) {
    case ActionPrevSector:
      startSector(sector_ - 1);
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionNextSector:
      startSector(sector_ + 1);
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionToggleAttack:
      if (selectedUnit_ >= 0 && selectedUnit_ < 3 && !units_[selectedUnit_].acted) {
        attackMode_ = !attackMode_;
        snprintf(statusMsg_, sizeof(statusMsg_),
                 attackMode_ ? "WEAPON ARMED: Tap target tile in line!" : "MOVE MODE: Tap empty tile (range 3).");
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionEndTurn:
      endPlayerTurn();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionResetSector:
      startSector(sector_);
      interactionsReady_ = false;
      requestUpdate();
      return;
    default:
      return;
  }
}

void MicroTacticsActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    shelf::leave(renderer, mappedInput);
    return;
  }
  if (mappedInput.wasPressed(MappedInputManager::Button::PageBack) ||
      mappedInput.wasPressed(MappedInputManager::Button::Up)) {
    routeAction(ActionPrevSector, 0);
    return;
  }
  if (mappedInput.wasPressed(MappedInputManager::Button::PageForward) ||
      mappedInput.wasPressed(MappedInputManager::Button::Down)) {
    routeAction(ActionNextSector, 0);
    return;
  }

  fui::InputSnapshot input;
  int tapX = 0, tapY = 0;
  if (!sidebuttons::poll(interactions_, mappedInput, tapX, tapY) || !interactionsReady_) return;

  if (tapX >= kGridX && tapX < kGridX + 6 * kCell && tapY >= kGridY && tapY < kGridY + 6 * kCell) {
    const int c = (tapX - kGridX) / kCell;
    const int r = (tapY - kGridY) / kCell;
    handleGridTap(r, c);
    return;
  }

  input.touchReleased = true;
  input.touchX = static_cast<int16_t>(tapX);
  input.touchY = static_cast<int16_t>(tapY);
  const fui::ActionEvent ev = sidebuttons::route(interactions_, input, mappedInput, *this);
  routeAction(static_cast<int>(ev.action), static_cast<int>(ev.value));
}

void MicroTacticsActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const int readerFont = SETTINGS.getReaderFontId();
  const toybox::Faces faces{toybox::kButtonFontId, readerFont, toybox::kDisplayFontId};
  fui::GfxRendererTarget target = toybox::makeTarget(renderer, faces);
  const fui::InputSnapshot noInput{};
  toybox::Frame frame(target, target.deviceContext(), noInput, interactions_);
  toybox::Screen screen(frame);

  char badge[24];
  snprintf(badge, sizeof(badge), "TURN %d/4 • GRID %d", std::min(4, turn_), gridHp_);
  fui::HeaderProps header;
  header.title = "MICRO-TACTICS";
  header.trailingLabel = badge;
  header.borderEdges = fui::EdgesNone;
  header.sidePadding = screen.theme().headerSidePadding;
  toybox::headerBand(screen, header);

  const fui::Rect body = screen.body();
  const int16_t inner = static_cast<int16_t>(body.width - kMargin * 2);

  int16_t y = static_cast<int16_t>(body.y + 8);
  drawButton(screen, fui::Rect{kMargin, y, 48, 38}, "<", ActionPrevSector, 0, false);
  drawButton(screen, fui::Rect{static_cast<int16_t>(body.width - kMargin - 48), y, 48, 38}, ">", ActionNextSector, 0,
             false);

  char secTitle[64];
  snprintf(secTitle, sizeof(secTitle), "SECTOR %d/%d %s", sector_ + 1, kSectorCount,
           (clearedMask_ & (1u << sector_)) ? "[CLEARED]" : "");
  const fui::Rect titleBox{static_cast<int16_t>(kMargin + 54), y, static_cast<int16_t>(inner - 108), 38};
  target.text(toybox::inkCentred(target, titleBox, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)), secTitle,
              makeStyle(toybox::kSmallFont, fui::TextAlign::Center));

  // Draw 6x6 Tactical Grid (kGridX = 24, kGridY = 126, 432x432)
  renderer.drawRect(kGridX - 2, kGridY - 2, 6 * kCell + 4, 6 * kCell + 4, 2, true);
  for (int r = 0; r < 6; ++r) {
    for (int c = 0; c < 6; ++c) {
      const int16_t cx = static_cast<int16_t>(kGridX + c * kCell);
      const int16_t cy = static_cast<int16_t>(kGridY + r * kCell);
      renderer.drawRect(cx, cy, kCell, kCell, 1, true);

      const Terrain t = board_[r][c];
      if (t == City) {
        target.text(fui::Rect{static_cast<int16_t>(cx + 4), static_cast<int16_t>(cy + 4),
                              static_cast<int16_t>(kCell - 8), 20},
                    "[CITY]", makeStyle(toybox::kSmallFont, fui::TextAlign::Center));
        renderer.drawRect(cx + 18, cy + 28, 14, 34, 2, true);
        renderer.drawRect(cx + 36, cy + 20, 18, 42, 2, true);
      } else if (t == Mountain) {
        target.text(fui::Rect{static_cast<int16_t>(cx + 4), static_cast<int16_t>(cy + 24),
                              static_cast<int16_t>(kCell - 8), 24},
                    "/\\ MTN", makeStyle(toybox::kSmallFont, fui::TextAlign::Center));
      } else if (t == Chasm) {
        renderer.fillRectDither(cx + 4, cy + 4, kCell - 8, kCell - 8, Color::DarkGray);
        target.text(fui::Rect{static_cast<int16_t>(cx + 4), static_cast<int16_t>(cy + 24),
                              static_cast<int16_t>(kCell - 8), 24},
                    "~PIT~", makeStyle(toybox::kSmallFont, fui::TextAlign::Center, fui::Color::White));
      }
    }
  }

  // Draw Enemy Attack Telegraphs (!)
  for (int i = 3; i < 8; ++i) {
    const auto& e = units_[i];
    if (e.kind != EnemyVek || e.hp <= 0) continue;
    const int tr = e.r + e.aimDr;
    const int tc = e.c + e.aimDc;
    if (tr >= 0 && tr < 6 && tc >= 0 && tc < 6) {
      const int16_t tx = static_cast<int16_t>(kGridX + tc * kCell);
      const int16_t ty = static_cast<int16_t>(kGridY + tr * kCell);
      renderer.drawRect(tx + 3, ty + 3, kCell - 6, kCell - 6, 2, true);
      target.text(fui::Rect{static_cast<int16_t>(tx + 4), static_cast<int16_t>(ty + 48),
                            static_cast<int16_t>(kCell - 8), 20},
                  "!HIT!", makeStyle(toybox::kSmallFont, fui::TextAlign::Center));
    }
  }

  // Draw Units (Mechs & Vek)
  for (int i = 0; i < 8; ++i) {
    const auto& u = units_[i];
    if (u.kind == None || u.hp <= 0) continue;
    const int16_t cx = static_cast<int16_t>(kGridX + u.c * kCell);
    const int16_t cy = static_cast<int16_t>(kGridY + u.r * kCell);
    const bool isMech = (i < 3);
    const bool isSel = (i == selectedUnit_);

    const fui::Rect token{static_cast<int16_t>(cx + 8), static_cast<int16_t>(cy + 8),
                          static_cast<int16_t>(kCell - 16), static_cast<int16_t>(kCell - 24)};
    if (isMech) {
      target.fill(token, fui::Paint::solid(fui::Color::Black));
      if (isSel) renderer.drawRect(cx + 3, cy + 3, kCell - 6, kCell - 6, 3, true);
    } else {
      target.fill(token, fui::Paint::solid(fui::Color::White));
      target.stroke(token, fui::Paint::solid(fui::Color::Black), 2);
    }

    char label[20];
    if (u.kind == MechTitan) {
      snprintf(label, sizeof(label), "T:%d", u.hp);
    } else if (u.kind == MechArtillery) {
      snprintf(label, sizeof(label), "A:%d", u.hp);
    } else if (u.kind == MechAegis) {
      snprintf(label, sizeof(label), "S:%d", u.hp);
    } else {
      const char dirCh = (u.aimDr < 0) ? '^' : (u.aimDr > 0 ? 'v' : (u.aimDc < 0 ? '<' : '>'));
      snprintf(label, sizeof(label), "V%d%c", u.hp, dirCh);
    }
    target.text(toybox::inkCentred(target, token, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)), label,
                makeStyle(toybox::kSmallFont, fui::TextAlign::Center,
                          isMech ? fui::Color::White : fui::Color::Black));
  }

  y = static_cast<int16_t>(kGridY + 6 * kCell + 10);
  target.text(fui::Rect{kMargin, y, inner, 48}, statusMsg_,
              makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 2));
  y = static_cast<int16_t>(y + 54);

  const int16_t btnW = static_cast<int16_t>((inner - 16) / 3);
  drawButton(screen, fui::Rect{kMargin, y, btnW, 44}, attackMode_ ? "MODE: ACT" : "MODE: MOVE", ActionToggleAttack, 0,
             attackMode_);
  drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + btnW + 8), y, btnW, 44}, "END TURN", ActionEndTurn, 0,
             true);
  drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + (btnW + 8) * 2), y, btnW, 44}, "RESET",
             ActionResetSector, 0, false);

  interactionsReady_ = true;
  renderer.displayBuffer();
}
