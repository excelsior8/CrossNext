#include "LogosActivity.h"

#include <HalStorage.h>
#include <Logging.h>
#include <Memory.h>

#include <algorithm>
#include <cstdio>
#include <cstring>

#include "../../CrossPointSettings.h"
#include "../../activities/ActivityManager.h"
#include "../../activities/RenderLock.h"
#include "../../fontIds.h"
#include "../Shelf.h"
#include "../ui/ToyboxTheme.h"
#include "../wikipedia/WikipediaActivity.h"
#include "components/SideButtonNavigation.h"

namespace fui = freeink::ui;

namespace {

constexpr const char* kTag = "LOGOS";
constexpr const char* kPackPath = "/logos/arguments.bin";
constexpr const char* kStatePath = "/logos/state.bin";
constexpr int16_t kMargin = 16;

enum : fui::ActionId {
  ActionPrevArg = 1,
  ActionNextArg = 2,
  ActionSetTab = 3,
  ActionPickObjection = 4,
  ActionOpenWiki = 5,
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

std::unique_ptr<Activity> LogosActivity::create(GfxRenderer& renderer, MappedInputManager& mappedInput) {
  return makeUniqueNoThrow<LogosActivity>(renderer, mappedInput);
}

void LogosActivity::onEnter() {
  Activity::onEnter();
  toybox::ensureFonts(renderer);
  arg_ = makeUniqueNoThrow<logos::LogosArgument>();
  loadProgress();
  packReady_ = loadArgument(argIdx_);
  interactionsReady_ = false;
  requestUpdate();
}

void LogosActivity::onExit() {
  saveProgress();
  arg_.reset();
  Activity::onExit();
}

void LogosActivity::loadProgress() {
  HalFile f;
  if (!Storage.exists(kStatePath) || !Storage.openFileForRead(kTag, kStatePath, f)) return;
  uint8_t buf[2] = {};
  if (f.read(buf, 2) == 2) {
    argIdx_ = buf[0];
    tab_ = buf[1] < 2 ? buf[1] : 0;
  }
}

void LogosActivity::saveProgress() const {
  if (!packReady_) return;
  HalFile f;
  if (!Storage.openFileForWrite(kTag, kStatePath, f)) return;
  const uint8_t buf[2] = {static_cast<uint8_t>(argIdx_), static_cast<uint8_t>(tab_)};
  f.write(buf, 2);
}

bool LogosActivity::loadArgument(int idx) {
  if (!arg_) return false;
  HalFile f;
  if (!Storage.exists(kPackPath) || !Storage.openFileForRead(kTag, kPackPath, f)) return false;
  logos::LogosHeader hdr{};
  if (f.read(reinterpret_cast<uint8_t*>(&hdr), sizeof(hdr)) != static_cast<int>(sizeof(hdr)) ||
      memcmp(hdr.magic, "CNLG0001", 8) != 0 || hdr.argCount == 0) {
    return false;
  }
  argCount_ = hdr.argCount;
  if (idx < 0) idx = argCount_ - 1;
  if (idx >= argCount_) idx = 0;
  argIdx_ = idx;
  const size_t offset =
      sizeof(logos::LogosHeader) + static_cast<size_t>(argIdx_) * sizeof(logos::LogosArgument);
  if (!f.seek(offset)) return false;
  if (f.read(reinterpret_cast<uint8_t*>(arg_.get()), sizeof(logos::LogosArgument)) !=
      static_cast<int>(sizeof(logos::LogosArgument))) {
    return false;
  }
  selectedObj_ = -1;
  return true;
}

void LogosActivity::routeAction(const int action, const int value) {
  switch (action) {
    case ActionPrevArg:
      if (packReady_) {
        loadArgument(argIdx_ - 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionNextArg:
      if (packReady_) {
        loadArgument(argIdx_ + 1);
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
    case ActionPickObjection:
      if (value >= 0 && value < 3) {
        selectedObj_ = value;
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionOpenWiki:
      if (arg_ && arg_->wikiTitle[0] != '\0') {
        saveProgress();
        WikipediaActivity::requestJump(1, arg_->wikiTitle);
        activityManager.replaceActivity(WikipediaActivity::create(renderer, mappedInput));
      }
      return;
    default:
      return;
  }
}

void LogosActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    shelf::leave(renderer, mappedInput);
    return;
  }
  if (packReady_) {
    if (mappedInput.wasPressed(MappedInputManager::Button::PageBack) ||
        mappedInput.wasPressed(MappedInputManager::Button::Up)) {
      routeAction(ActionPrevArg, 0);
      return;
    }
    if (mappedInput.wasPressed(MappedInputManager::Button::PageForward) ||
        mappedInput.wasPressed(MappedInputManager::Button::Down)) {
      routeAction(ActionNextArg, 0);
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

void LogosActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const int readerFont = SETTINGS.getReaderFontId();
  const toybox::Faces faces{toybox::kButtonFontId, readerFont, toybox::kDisplayFontId};
  fui::GfxRendererTarget target = toybox::makeTarget(renderer, faces);
  const fui::InputSnapshot noInput{};
  toybox::Frame frame(target, target.deviceContext(), noInput, interactions_);
  toybox::Screen screen(frame);

  char badge[24];
  snprintf(badge, sizeof(badge), "ARG %d/%d", argIdx_ + 1, std::max(1, argCount_));
  fui::HeaderProps header;
  header.title = "LOGOS • DIALECTICS";
  header.trailingLabel = badge;
  header.borderEdges = fui::EdgesNone;
  header.sidePadding = screen.theme().headerSidePadding;
  toybox::headerBand(screen, header);

  const fui::Rect body = screen.body();
  const int16_t inner = static_cast<int16_t>(body.width - kMargin * 2);

  if (!packReady_ || !arg_) {
    target.text(fui::Rect{kMargin, static_cast<int16_t>(body.y + 120), inner, 120},
                "Put /logos/arguments.bin on the SD card to explore philosophical argument trees.",
                makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 4));
    interactionsReady_ = true;
    renderer.displayBuffer();
    return;
  }

  int16_t y = static_cast<int16_t>(body.y + 8);
  drawButton(screen, fui::Rect{kMargin, y, 48, 40}, "<", ActionPrevArg, 0, false);
  drawButton(screen, fui::Rect{static_cast<int16_t>(body.width - kMargin - 48), y, 48, 40}, ">", ActionNextArg, 0,
             false);

  target.text(fui::Rect{static_cast<int16_t>(kMargin + 54), y, static_cast<int16_t>(inner - 108), 18},
              arg_->eraAndSchool, makeStyle(toybox::kSmallFont, fui::TextAlign::Center));
  target.text(
      fui::Rect{static_cast<int16_t>(kMargin + 54), static_cast<int16_t>(y + 18), static_cast<int16_t>(inner - 108),
                24},
      arg_->title, makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 1, true));
  y = static_cast<int16_t>(y + 46);

  const int16_t halfW = static_cast<int16_t>((inner - 8) / 2);
  drawButton(screen, fui::Rect{kMargin, y, halfW, 34}, "1. PREMISE TREE", ActionSetTab, 0, tab_ == 0);
  drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + halfW + 8), y, halfW, 34}, "2. RED-TEAM CRITIQUE",
             ActionSetTab, 1, tab_ == 1);
  y = static_cast<int16_t>(y + 42);

  if (tab_ == 0) {
    const char* const nodes[4] = {arg_->premise1, arg_->premise2, arg_->premise3, arg_->conclusion};
    for (int i = 0; i < 4; ++i) {
      const bool isConc = (i == 3);
      const fui::Rect box{kMargin, y, inner, 118};
      if (isConc) {
        target.stroke(box, fui::Paint::solid(fui::Color::Black), 2);
      } else {
        target.stroke(box, fui::Paint::solid(fui::Color::Black), 1);
      }
      target.text(fui::Rect{static_cast<int16_t>(kMargin + 8), static_cast<int16_t>(y + 6),
                            static_cast<int16_t>(inner - 16), 106},
                  nodes[i], makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 4, isConc));
      y = static_cast<int16_t>(y + 126);
    }

    const int16_t btnY = static_cast<int16_t>(body.bottom() - 52);
    drawButton(screen, fui::Rect{kMargin, btnY, halfW, 44}, "RED-TEAM IT >", ActionSetTab, 1, true);
    drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + halfW + 8), btnY, halfW, 44}, "READ IN VAULT >",
               ActionOpenWiki, 0, false);
  } else {
    target.text(fui::Rect{kMargin, y, inner, 20}, "SELECT THE STRONGEST PHILOSOPHICAL OBJECTION:",
                makeStyle(toybox::kSmallFont));
    y = static_cast<int16_t>(y + 24);

    for (int i = 0; i < 3; ++i) {
      const bool chosen = (selectedObj_ == i);
      const fui::Rect box{kMargin, y, inner, 88};
      if (chosen) {
        target.stroke(box, fui::Paint::solid(fui::Color::Black), 3);
      } else {
        target.stroke(box, fui::Paint::solid(fui::Color::Black), 1);
      }
      target.text(fui::Rect{static_cast<int16_t>(kMargin + 8), static_cast<int16_t>(y + 6),
                            static_cast<int16_t>(inner - 16), 76},
                  arg_->objections[i],
                  makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 3, chosen));
      frame.hit(box, ActionPickObjection, static_cast<int16_t>(i));
      y = static_cast<int16_t>(y + 96);
    }

    if (selectedObj_ >= 0) {
      const bool hit = (selectedObj_ == static_cast<int>(arg_->bestObjection));
      const fui::Rect banner{kMargin, y, inner, 26};
      target.fill(banner, fui::Paint::solid(fui::Color::Black));
      target.text(toybox::inkCentred(target, banner, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)),
                  hit ? "EXACT HIT! CLASSIC PHILOSOPHICAL CRITIQUE:" : "WEAK OBJECTION — SEE STRONGEST CRITIQUE:",
                  makeStyle(toybox::kSmallFont, fui::TextAlign::Center, fui::Color::White));
      y = static_cast<int16_t>(y + 30);
      target.text(fui::Rect{kMargin, y, inner, static_cast<int16_t>(body.bottom() - y - 6)}, arg_->analysis,
                  makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 8));
    } else {
      target.text(fui::Rect{kMargin, static_cast<int16_t>(y + 30), inner, 80},
                  "Tap Objection A, B, or C above to test which critique breaks a premise of this argument.",
                  makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 3));
    }
  }

  interactionsReady_ = true;
  renderer.displayBuffer();
}
