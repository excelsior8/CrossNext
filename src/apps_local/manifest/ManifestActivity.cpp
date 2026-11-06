#include "ManifestActivity.h"

#include <HalStorage.h>
#include <Logging.h>
#include <Memory.h>

#include <algorithm>
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

constexpr const char* kTag = "MANIFEST";
constexpr const char* kPackPath = "/manifest/scenes.bin";
constexpr const char* kStatePath = "/manifest/state.bin";
constexpr int16_t kMargin = 16;

enum : fui::ActionId {
  ActionPrevScene = 1,
  ActionNextScene = 2,
  ActionSetTab = 3,
  ActionStepWho = 4,
  ActionStepFate = 5,
  ActionStepKiller = 6,
  ActionVerify = 7,
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

std::unique_ptr<Activity> ManifestActivity::create(GfxRenderer& renderer, MappedInputManager& mappedInput) {
  return makeUniqueNoThrow<ManifestActivity>(renderer, mappedInput);
}

void ManifestActivity::onEnter() {
  Activity::onEnter();
  toybox::ensureFonts(renderer);
  meta_ = makeUniqueNoThrow<manifest::ManifestMetadata>();
  scene_ = makeUniqueNoThrow<manifest::ManifestScene>();
  loadProgress();
  packReady_ = loadScene(sceneIdx_);
  interactionsReady_ = false;
  requestUpdate();
}

void ManifestActivity::onExit() {
  saveProgress();
  scene_.reset();
  meta_.reset();
  Activity::onExit();
}

void ManifestActivity::loadProgress() {
  HalFile f;
  if (!Storage.exists(kStatePath) || !Storage.openFileForRead(kTag, kStatePath, f)) return;
  uint8_t buf[34] = {};
  if (f.read(buf, sizeof(buf)) == sizeof(buf)) {
    sceneIdx_ = buf[0] < 10 ? buf[0] : 0;
    tab_ = buf[1] < 2 ? buf[1] : 0;
    solvedMask_ = static_cast<uint16_t>(buf[2] | (buf[3] << 8));
    memcpy(guessWho_, buf + 4, 10);
    memcpy(guessFate_, buf + 14, 10);
    memcpy(guessKiller_, buf + 24, 10);
  }
}

void ManifestActivity::saveProgress() const {
  if (!packReady_) return;
  HalFile f;
  if (!Storage.openFileForWrite(kTag, kStatePath, f)) return;
  uint8_t buf[34] = {};
  buf[0] = static_cast<uint8_t>(sceneIdx_);
  buf[1] = static_cast<uint8_t>(tab_);
  buf[2] = static_cast<uint8_t>(solvedMask_ & 0xFF);
  buf[3] = static_cast<uint8_t>((solvedMask_ >> 8) & 0xFF);
  memcpy(buf + 4, guessWho_, 10);
  memcpy(buf + 14, guessFate_, 10);
  memcpy(buf + 24, guessKiller_, 10);
  f.write(buf, sizeof(buf));
}

bool ManifestActivity::loadScene(int idx) {
  if (!meta_ || !scene_) return false;
  HalFile f;
  if (!Storage.exists(kPackPath) || !Storage.openFileForRead(kTag, kPackPath, f)) return false;
  manifest::ManifestHeader hdr{};
  if (f.read(reinterpret_cast<uint8_t*>(&hdr), sizeof(hdr)) != static_cast<int>(sizeof(hdr)) ||
      memcmp(hdr.magic, "CNMF0001", 8) != 0 || hdr.sceneCount == 0) {
    return false;
  }
  sceneCount_ = std::min<int>(hdr.sceneCount, 10);
  if (f.read(reinterpret_cast<uint8_t*>(meta_.get()), sizeof(manifest::ManifestMetadata)) !=
      static_cast<int>(sizeof(manifest::ManifestMetadata))) {
    return false;
  }
  if (idx < 0) idx = sceneCount_ - 1;
  if (idx >= sceneCount_) idx = 0;
  sceneIdx_ = idx;
  const size_t offset = sizeof(manifest::ManifestHeader) + sizeof(manifest::ManifestMetadata) +
                        static_cast<size_t>(sceneIdx_) * sizeof(manifest::ManifestScene);
  if (!f.seek(offset)) return false;
  const size_t want = sizeof(manifest::ManifestScene);
  uint8_t* dst = reinterpret_cast<uint8_t*>(scene_.get());
  size_t got = 0;
  while (got < want) {
    const int n = f.read(dst + got, std::min<size_t>(4096, want - got));
    if (n <= 0) return false;
    got += static_cast<size_t>(n);
  }
  lastCheckHits_ = (solvedMask_ & (1u << sceneIdx_)) ? 3 : -1;
  return true;
}

void ManifestActivity::drawSceneBitmap(const int x0, const int y0) const {
  if (!scene_) return;
  renderer.fillRect(x0 - 2, y0 - 2, 444, 204, false);
  renderer.drawRect(x0 - 2, y0 - 2, 444, 204, 2, true);
  const uint8_t* bmp = scene_->sceneBitmap;
  for (int r = 0; r < 200; ++r) {
    const uint8_t* row = bmp + r * 55;
    for (int b = 0; b < 55; ++b) {
      const uint8_t byte = row[b];
      if (!byte) continue;
      const int baseCol = b * 8;
      for (int bit = 0; bit < 8; ++bit) {
        if (byte & (0x80 >> bit)) {
          renderer.drawPixel(x0 + baseCol + bit, y0 + r, true);
        }
      }
    }
  }
}

void ManifestActivity::routeAction(const int action, const int value) {
  switch (action) {
    case ActionPrevScene:
      if (packReady_) {
        loadScene(sceneIdx_ - 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionNextScene:
      if (packReady_) {
        loadScene(sceneIdx_ + 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionSetTab:
      if (value >= 0 && value < 2 && value != tab_) {
        tab_ = value;
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionStepWho:
      guessWho_[sceneIdx_] = static_cast<uint8_t>((guessWho_[sceneIdx_] + 10 + value) % 10);
      lastCheckHits_ = -1;
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionStepFate:
      guessFate_[sceneIdx_] = static_cast<uint8_t>((guessFate_[sceneIdx_] + 8 + value) % 8);
      lastCheckHits_ = -1;
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionStepKiller:
      guessKiller_[sceneIdx_] = static_cast<uint8_t>((guessKiller_[sceneIdx_] + 12 + value) % 12);
      lastCheckHits_ = -1;
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionVerify: {
      if (!scene_) return;
      int hits = 0;
      if (guessWho_[sceneIdx_] == scene_->correctWho) ++hits;
      if (guessFate_[sceneIdx_] == scene_->correctFate) ++hits;
      if (guessKiller_[sceneIdx_] == scene_->correctKiller) ++hits;
      lastCheckHits_ = static_cast<int8_t>(hits);
      if (hits == 3) {
        solvedMask_ |= static_cast<uint16_t>(1u << sceneIdx_);
      }
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    }
    default:
      return;
  }
}

void ManifestActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    shelf::leave(renderer, mappedInput);
    return;
  }
  if (packReady_) {
    if (mappedInput.wasPressed(MappedInputManager::Button::PageBack) ||
        mappedInput.wasPressed(MappedInputManager::Button::Up)) {
      routeAction(ActionPrevScene, 0);
      return;
    }
    if (mappedInput.wasPressed(MappedInputManager::Button::PageForward) ||
        mappedInput.wasPressed(MappedInputManager::Button::Down)) {
      routeAction(ActionNextScene, 0);
      return;
    }
  }
  fui::InputSnapshot input;
  int tapX = 0, tapY = 0;
  if (!sidebuttons::poll(interactions_, mappedInput, tapX, tapY) || !interactionsReady_) return;
  input.touchReleased = true;
  input.touchX = static_cast<int16_t>(tapX);
  input.touchY = static_cast<int16_t>(tapY);
  const fui::ActionEvent ev = sidebuttons::route(interactions_, input, mappedInput, *this);
  routeAction(static_cast<int>(ev.action), static_cast<int>(ev.value));
}

void ManifestActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const int readerFont = SETTINGS.getReaderFontId();
  const toybox::Faces faces{toybox::kButtonFontId, readerFont, toybox::kDisplayFontId};
  fui::GfxRendererTarget target = toybox::makeTarget(renderer, faces);
  const fui::InputSnapshot noInput{};
  toybox::Frame frame(target, target.deviceContext(), noInput, interactions_);
  toybox::Screen screen(frame);

  int solvedCount = 0;
  for (int i = 0; i < 10; ++i) {
    if (solvedMask_ & (1u << i)) ++solvedCount;
  }
  char badge[24];
  snprintf(badge, sizeof(badge), "SOLVED %d/%d", solvedCount, std::max(1, sceneCount_));

  fui::HeaderProps header;
  header.title = "S.S. ESPERIA • 1887";
  header.trailingLabel = badge;
  header.borderEdges = fui::EdgesNone;
  header.sidePadding = screen.theme().headerSidePadding;
  toybox::headerBand(screen, header);

  const fui::Rect body = screen.body();
  const int16_t inner = static_cast<int16_t>(body.width - kMargin * 2);

  if (!packReady_ || !meta_ || !scene_) {
    target.text(fui::Rect{kMargin, static_cast<int16_t>(body.y + 120), inner, 120},
                "Put /manifest/scenes.bin on the SD card to investigate the S.S. Esperia.",
                makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 4));
    interactionsReady_ = true;
    renderer.displayBuffer();
    return;
  }

  int16_t y = static_cast<int16_t>(body.y + 8);
  drawButton(screen, fui::Rect{kMargin, y, 48, 38}, "<", ActionPrevScene, 0, false);
  drawButton(screen, fui::Rect{static_cast<int16_t>(body.width - kMargin - 48), y, 48, 38}, ">", ActionNextScene, 0,
             false);

  const fui::Rect titleBox{static_cast<int16_t>(kMargin + 54), y, static_cast<int16_t>(inner - 108), 38};
  target.text(toybox::inkCentred(target, titleBox, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)),
              scene_->chapterTitle, makeStyle(toybox::kSmallFont, fui::TextAlign::Center));
  y = static_cast<int16_t>(y + 44);

  // 440x200 1-bit scene engraving
  drawSceneBitmap(20, y);
  y = static_cast<int16_t>(y + 206);

  // Two-tab bar: CLUES & MEMORY | DEDUCE FATE
  const int16_t halfW = static_cast<int16_t>((inner - 8) / 2);
  drawButton(screen, fui::Rect{kMargin, y, halfW, 34}, "1. CLUES & MEMORY", ActionSetTab, 0, tab_ == 0);
  drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + halfW + 8), y, halfW, 34},
             (solvedMask_ & (1u << sceneIdx_)) ? "2. FATE [VERIFIED]" : "2. DEDUCE FATE", ActionSetTab, 1, tab_ == 1);
  y = static_cast<int16_t>(y + 42);

  if (tab_ == 0) {
    char locLine[64];
    snprintf(locLine, sizeof(locLine), "LOCATION: %s", scene_->location);
    target.text(fui::Rect{kMargin, y, inner, 22}, locLine, makeStyle(toybox::kSmallFont));
    y = static_cast<int16_t>(y + 24);

    target.text(fui::Rect{kMargin, y, inner, 130}, scene_->clueSummary,
                makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 5));
    y = static_cast<int16_t>(y + 134);
    target.fill(fui::Rect{kMargin, y, inner, 1}, fui::Paint::solid(fui::Color::Black));
    y = static_cast<int16_t>(y + 8);

    target.text(fui::Rect{kMargin, y, inner, 22}, "POCKET-WATCH AUDIO TRANSCRIPT:", makeStyle(toybox::kSmallFont));
    y = static_cast<int16_t>(y + 24);
    target.text(fui::Rect{kMargin, y, inner, static_cast<int16_t>(body.bottom() - y - 8)}, scene_->transcript,
                makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 7));
  } else {
    // 3-Part Deduction Matrix
    const auto drawSelector = [&](const char* label, const char* valueText, const fui::ActionId act) {
      target.text(fui::Rect{kMargin, y, inner, 20}, label, makeStyle(toybox::kSmallFont));
      y = static_cast<int16_t>(y + 22);
      drawButton(screen, fui::Rect{kMargin, y, 52, 40}, "<", act, -1, false);
      drawButton(screen, fui::Rect{static_cast<int16_t>(body.width - kMargin - 52), y, 52, 40}, ">", act, 1, false);
      const fui::Rect valBox{static_cast<int16_t>(kMargin + 58), y, static_cast<int16_t>(inner - 116), 40};
      target.stroke(valBox, fui::Paint::solid(fui::Color::Black), 1);
      target.text(toybox::inkCentred(target, valBox, makeStyle(toybox::kBodyFont, fui::TextAlign::Center)), valueText,
                  makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 1, true));
      y = static_cast<int16_t>(y + 48);
    };

    drawSelector("1. THIS SOUL WAS (IDENTITY):", meta_->crewNames[guessWho_[sceneIdx_] % 10], ActionStepWho);
    drawSelector("2. THEIR FATE WAS (CAUSE):", meta_->fateNames[guessFate_[sceneIdx_] % 8], ActionStepFate);
    drawSelector("3. CAUSED BY (PERPETRATOR / FORCE):", meta_->killerNames[guessKiller_[sceneIdx_] % 12],
                 ActionStepKiller);

    y = static_cast<int16_t>(y + 4);
    if (lastCheckHits_ >= 0) {
      char msg[80];
      if (lastCheckHits_ == 3) {
        snprintf(msg, sizeof(msg), "FATE VALIDATED! ALL 3 ENTRIES MATCH THE LOG.");
      } else {
        snprintf(msg, sizeof(msg), "INSPECTOR NOTE: %d OF 3 ENTRIES ARE ACCURATE.", static_cast<int>(lastCheckHits_));
      }
      target.text(fui::Rect{kMargin, y, inner, 32}, msg,
                  makeStyle(toybox::kSmallFont, fui::TextAlign::Center, fui::Color::Black, 1));
    }

    const int16_t btnY = static_cast<int16_t>(body.bottom() - 54);
    drawButton(screen, fui::Rect{kMargin, btnY, inner, 46},
               (solvedMask_ & (1u << sceneIdx_)) ? "FATE LOCKED IN MANIFEST" : "VERIFY FATE IN MANIFEST", ActionVerify,
               0, true);
  }

  interactionsReady_ = true;
  renderer.displayBuffer();
}
