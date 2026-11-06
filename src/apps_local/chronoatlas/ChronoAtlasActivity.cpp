#include "ChronoAtlasActivity.h"

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

constexpr const char* kTag = "ATLAS";
constexpr const char* kAtlasPath = "/chronoatlas/atlas.bin";
constexpr const char* kCitiesPath = "/chronoatlas/cities.bin";
constexpr const char* kStatePath = "/chronoatlas/state.bin";
constexpr int16_t kMargin = 16;

enum : fui::ActionId {
  ActionPrevEra = 1,
  ActionNextEra = 2,
  ActionTab = 3,
  ActionOpenWiki = 4,
  ActionToggleMode = 5,
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

fui::StyleSet headerPillStyles() {
  fui::StyleSet styles;
  styles.explicitlySet = true;
  styles.normal.background = fui::Paint::solid(fui::Color::Black);
  styles.normal.foreground = fui::Paint::solid(fui::Color::White);
  styles.normal.border = fui::Paint::solid(fui::Color::White);
  styles.normal.borderWidth = toybox::kFrame;
  styles.selected = styles.normal;
  styles.focused = styles.normal;
  styles.active = styles.normal;
  return styles;
}

}  // namespace

std::unique_ptr<Activity> ChronoAtlasActivity::create(GfxRenderer& renderer, MappedInputManager& mappedInput) {
  return makeUniqueNoThrow<ChronoAtlasActivity>(renderer, mappedInput);
}

void ChronoAtlasActivity::onEnter() {
  Activity::onEnter();
  toybox::ensureFonts(renderer);
  era_ = makeUniqueNoThrow<chronoatlas::AtlasEra>();
  loadProgress();
  packReady_ = loadEra(eraIdx_);
  if (!packReady_ && mode_ != 0) {
    mode_ = 0;
    packReady_ = loadEra(0);
  }
  interactionsReady_ = false;
  requestUpdate();
}

void ChronoAtlasActivity::onExit() {
  saveProgress();
  era_.reset();
  Activity::onExit();
}

void ChronoAtlasActivity::loadProgress() {
  HalFile f;
  if (!Storage.exists(kStatePath) || !Storage.openFileForRead(kTag, kStatePath, f)) return;
  uint8_t buf[3] = {};
  if (f.read(buf, 3) >= 2) {
    eraIdx_ = buf[0];
    tab_ = buf[1] < 4 ? buf[1] : 0;
    mode_ = buf[2] < 2 ? buf[2] : 0;
  }
}

void ChronoAtlasActivity::saveProgress() const {
  if (!packReady_) return;
  HalFile f;
  if (!Storage.openFileForWrite(kTag, kStatePath, f)) return;
  const uint8_t buf[3] = {static_cast<uint8_t>(eraIdx_), static_cast<uint8_t>(tab_), static_cast<uint8_t>(mode_)};
  f.write(buf, 3);
}

bool ChronoAtlasActivity::loadEra(int idx) {
  if (!era_) return false;
  const char* path = (mode_ == 1) ? kCitiesPath : kAtlasPath;
  HalFile f;
  if (!Storage.exists(path) || !Storage.openFileForRead(kTag, path, f)) return false;
  chronoatlas::AtlasHeader hdr{};
  if (f.read(reinterpret_cast<uint8_t*>(&hdr), sizeof(hdr)) != static_cast<int>(sizeof(hdr)) ||
      memcmp(hdr.magic, "CNAT0001", 8) != 0) {
    return false;
  }
  if (hdr.eraCount == 0) return false;
  eraCount_ = hdr.eraCount;
  if (idx < 0) idx = eraCount_ - 1;
  if (idx >= eraCount_) idx = 0;
  eraIdx_ = idx;
  const size_t offset = sizeof(chronoatlas::AtlasHeader) + static_cast<size_t>(eraIdx_) * sizeof(chronoatlas::AtlasEra);
  if (!f.seek(offset)) return false;
  const size_t want = sizeof(chronoatlas::AtlasEra);
  uint8_t* dst = reinterpret_cast<uint8_t*>(era_.get());
  size_t got = 0;
  while (got < want) {
    const int n = f.read(dst + got, std::min<size_t>(4096, want - got));
    if (n <= 0) return false;
    got += static_cast<size_t>(n);
  }
  return true;
}

void ChronoAtlasActivity::drawMap(const int x0, const int y0) const {
  if (!era_) return;
  renderer.fillRect(x0 - 2, y0 - 2, 444, 244, false);
  renderer.drawRect(x0 - 2, y0 - 2, 444, 244, 2, true);
  const uint8_t* bmp = era_->mapBitmap;
  for (int r = 0; r < 240; ++r) {
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

void ChronoAtlasActivity::routeAction(const int action, const int value) {
  switch (action) {
    case ActionPrevEra:
      if (packReady_) {
        loadEra(eraIdx_ - 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionNextEra:
      if (packReady_) {
        loadEra(eraIdx_ + 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionTab:
      if (value >= 0 && value < 4 && value != tab_) {
        tab_ = value;
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionToggleMode: {
      const int nextMode = 1 - mode_;
      const char* nextPath = (nextMode == 1) ? kCitiesPath : kAtlasPath;
      if (Storage.exists(nextPath)) {
        mode_ = nextMode;
        eraIdx_ = 0;
        packReady_ = loadEra(0);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    }
    case ActionOpenWiki: {
      if (!era_ || value < 0 || value >= 4) return;
      const chronoatlas::AtlasItem* items = era_->powers;
      int vault = (mode_ == 1) ? 2 : 0;  // City Atlas jumps to Wikivoyage (vault 2)
      if (tab_ == 1) {
        items = era_->events;
      } else if (tab_ == 2) {
        items = era_->thinkers;
        if (mode_ == 0) vault = 1;  // Philosophy/History vault for thinkers
      }
      if (items[value].wikiTitle[0] != '\0') {
        saveProgress();
        WikipediaActivity::requestJump(vault, items[value].wikiTitle);
        activityManager.replaceActivity(WikipediaActivity::create(renderer, mappedInput));
      }
      return;
    }
    default:
      return;
  }
}

void ChronoAtlasActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    shelf::leave(renderer, mappedInput);
    return;
  }
  if (packReady_) {
    const auto swipe = mappedInput.wasSwipe();
    if (mappedInput.wasPressed(MappedInputManager::Button::PageBack) ||
        mappedInput.wasPressed(MappedInputManager::Button::Up) || swipe == MappedInputManager::SwipeDir::Right) {
      routeAction(ActionPrevEra, 0);
      return;
    }
    if (mappedInput.wasPressed(MappedInputManager::Button::PageForward) ||
        mappedInput.wasPressed(MappedInputManager::Button::Down) || swipe == MappedInputManager::SwipeDir::Left) {
      routeAction(ActionNextEra, 0);
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

void ChronoAtlasActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const int readerFont = SETTINGS.getReaderFontId();
  const toybox::Faces faces{toybox::kButtonFontId, readerFont, toybox::kDisplayFontId};
  fui::GfxRendererTarget target = toybox::makeTarget(renderer, faces);
  const fui::InputSnapshot noInput{};
  toybox::Frame frame(target, target.deviceContext(), noInput, interactions_);
  toybox::Screen screen(frame);

  fui::HeaderProps header;
  header.title = (mode_ == 1) ? "CITY & POI ATLAS" : "CHRONOATLAS";
  header.trailingLabel = (mode_ == 1) ? "MODE: CITIES" : "MODE: HISTORY";
  header.trailingAction = ActionToggleMode;
  header.trailingStyles = headerPillStyles();
  header.trailingText = screen.theme().smallText;
  header.trailingText.font = toybox::kSmallFont;
  header.trailingText.color = fui::Color::White;
  header.trailingRadius = toybox::kPillRadius / 2;
  header.borderEdges = fui::EdgesNone;
  header.sidePadding = screen.theme().headerSidePadding;
  toybox::headerBand(screen, header);

  const fui::Rect body = screen.body();
  const int16_t inner = static_cast<int16_t>(body.width - kMargin * 2);

  if (!packReady_ || !era_) {
    target.text(fui::Rect{kMargin, static_cast<int16_t>(body.y + 120), inner, 120},
                "Put /chronoatlas/atlas.bin & cities.bin on the SD card.",
                makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 4));
    interactionsReady_ = true;
    renderer.displayBuffer();
    return;
  }

  int16_t y = static_cast<int16_t>(body.y + 8);
  drawButton(screen, fui::Rect{kMargin, y, 54, 42}, "<", ActionPrevEra, 0, false);
  drawButton(screen, fui::Rect{static_cast<int16_t>(body.width - kMargin - 54), y, 54, 42}, ">", ActionNextEra, 0,
             false);

  char headline[96];
  snprintf(headline, sizeof(headline), "%d/%d • %s : %s", eraIdx_ + 1, eraCount_, era_->yearLabel, era_->eraTitle);
  const fui::Rect titleBox{static_cast<int16_t>(kMargin + 60), y, static_cast<int16_t>(inner - 120), 42};
  target.text(toybox::inkCentred(target, titleBox, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)), headline,
              makeStyle(toybox::kSmallFont, fui::TextAlign::Center, fui::Color::Black, 1));
  y = static_cast<int16_t>(y + 48);

  static const char* const kHistTabs[4] = {"MAP & POWERS", "EVENTS", "THINKERS", "OVERVIEW"};
  static const char* const kCityTabs[4] = {"MAP & ZONES", "TOP POIS", "TIPS & FOOD", "OVERVIEW"};
  const char* const* tabs = (mode_ == 1) ? kCityTabs : kHistTabs;
  const int16_t tabW = static_cast<int16_t>((inner - 12) / 4);
  for (int t = 0; t < 4; ++t) {
    const int16_t tx = static_cast<int16_t>(kMargin + t * (tabW + 4));
    drawButton(screen, fui::Rect{tx, y, tabW, 34}, tabs[t], ActionTab, static_cast<int16_t>(t), tab_ == t);
  }
  y = static_cast<int16_t>(y + 42);

  if (tab_ == 0 || tab_ == 3) {
    drawMap(20, y);
    y = static_cast<int16_t>(y + 246);
  }

  if (tab_ == 3) {
    target.text(fui::Rect{kMargin, y, inner, static_cast<int16_t>(body.bottom() - y - 8)}, era_->summary,
                makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 12));
  } else {
    const chronoatlas::AtlasItem* items = era_->powers;
    if (tab_ == 1) {
      items = era_->events;
    } else if (tab_ == 2) {
      items = era_->thinkers;
    }

    const int16_t availH = static_cast<int16_t>(body.bottom() - y - 4);
    const int maxRows = 4;
    const int16_t rowH = static_cast<int16_t>(availH / maxRows);
    const uint8_t subLines = (tab_ == 0) ? 2 : 3;

    for (int i = 0; i < maxRows; ++i) {
      if (items[i].title[0] == '\0') continue;
      const int16_t ry = static_cast<int16_t>(y + i * rowH);
      const fui::Rect row{kMargin, ry, inner, static_cast<int16_t>(rowH - 2)};
      target.text(fui::Rect{kMargin, static_cast<int16_t>(ry + 2), static_cast<int16_t>(inner - 74), 26},
                  items[i].title, makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 1, true));
      if (items[i].wikiTitle[0] != '\0') {
        const fui::Rect pill{static_cast<int16_t>(body.width - kMargin - 68), static_cast<int16_t>(ry + 3), 68, 24};
        target.stroke(pill, fui::Paint::solid(fui::Color::Black), 1);
        target.text(toybox::inkCentred(target, pill, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)),
                    (mode_ == 1) ? "GUIDE >" : "WIKI >", makeStyle(toybox::kSmallFont, fui::TextAlign::Center));
      }
      target.text(
          fui::Rect{kMargin, static_cast<int16_t>(ry + 28), inner, static_cast<int16_t>(row.height - 30)},
          items[i].subtitle, makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, subLines, false));
      target.fill(fui::Rect{kMargin, static_cast<int16_t>(row.bottom() - 1), inner, 1},
                  fui::Paint::solid(fui::Color::Black));
      frame.hit(row, ActionOpenWiki, static_cast<int16_t>(i));
    }
  }

  interactionsReady_ = true;
  renderer.displayBuffer();
}
