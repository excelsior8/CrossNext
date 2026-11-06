#include "BilingualActivity.h"

#include <HalStorage.h>
#include <Logging.h>
#include <Memory.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <string>

#include "../../CrossPointSettings.h"
#include "../../activities/RenderLock.h"
#include "../../fontIds.h"
#include "../Shelf.h"
#include "../ui/ToyboxIcons.h"
#include "../ui/ToyboxTheme.h"
#include "components/SideButtonNavigation.h"

namespace fui = freeink::ui;

namespace {

constexpr const char* kTag = "BILING";
constexpr const char* kPackPath = "/bilingual/texts.bin";
constexpr const char* kStatePath = "/bilingual/state.bin";
constexpr const char* kFlashcardDir1 = "/FLASHCARDS";
constexpr const char* kFlashcardDir2 = "/FLASHCARDS/Italiano";
constexpr const char* kFlashcardCsv = "/FLASHCARDS/Italiano/05 - Bilingual Kaydedilenler.csv";
constexpr int16_t kMargin = 16;
constexpr int kStoriesPerPage = 6;

enum : fui::ActionId {
  ActionSelectStory = 1,
  ActionListPrev = 2,
  ActionListNext = 3,
  ActionPrevSeg = 4,
  ActionNextSeg = 5,
  ActionCycleMode = 6,
  ActionSaveCard = 7,
  ActionBackToList = 8,
  ActionRevealQuiz = 9,
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

std::string csvEscape(const char* s) {
  std::string out = "\"";
  for (size_t i = 0; s[i] != '\0'; ++i) {
    if (s[i] == '"') {
      out += "\"\"";
    } else {
      out += s[i];
    }
  }
  out += "\"";
  return out;
}

}  // namespace

std::unique_ptr<Activity> BilingualActivity::create(GfxRenderer& renderer, MappedInputManager& mappedInput) {
  return makeUniqueNoThrow<BilingualActivity>(renderer, mappedInput);
}

void BilingualActivity::onEnter() {
  Activity::onEnter();
  toybox::ensureFonts(renderer);
  seg_ = makeUniqueNoThrow<bilingual::Segment>();
  packReady_ = loadCatalog();
  loadProgress();
  if (inStory_ && packReady_) {
    if (!loadSegment(storyIdx_, segIdx_)) inStory_ = false;
  }
  interactionsReady_ = false;
  requestUpdate();
}

void BilingualActivity::onExit() {
  saveProgress();
  seg_.reset();
  stories_.clear();
  Activity::onExit();
}

bool BilingualActivity::loadCatalog() {
  stories_.clear();
  HalFile f;
  if (!Storage.exists(kPackPath) || !Storage.openFileForRead(kTag, kPackPath, f)) return false;
  bilingual::BilingualHeader hdr{};
  if (f.read(reinterpret_cast<uint8_t*>(&hdr), sizeof(hdr)) != static_cast<int>(sizeof(hdr)) ||
      memcmp(hdr.magic, "CNBL0001", 8) != 0) {
    return false;
  }
  if (hdr.textCount == 0 || hdr.textCount > 32) return false;
  stories_.resize(hdr.textCount);
  const size_t bytes = static_cast<size_t>(hdr.textCount) * sizeof(bilingual::StoryMeta);
  if (f.read(reinterpret_cast<uint8_t*>(stories_.data()), bytes) != static_cast<int>(bytes)) {
    stories_.clear();
    return false;
  }
  return true;
}

bool BilingualActivity::loadSegment(int storyIdx, int segIdx) {
  if (!seg_ || stories_.empty()) return false;
  if (storyIdx < 0 || storyIdx >= static_cast<int>(stories_.size())) return false;
  const auto& meta = stories_[storyIdx];
  if (meta.segmentCount == 0) return false;
  if (segIdx < 0) segIdx = 0;
  if (segIdx >= meta.segmentCount) segIdx = meta.segmentCount - 1;

  HalFile f;
  if (!Storage.openFileForRead(kTag, kPackPath, f)) return false;
  const size_t segIndex = static_cast<size_t>(meta.firstSegment) + static_cast<size_t>(segIdx);
  const size_t offset = sizeof(bilingual::BilingualHeader) + stories_.size() * sizeof(bilingual::StoryMeta) +
                        segIndex * sizeof(bilingual::Segment);
  if (!f.seek(offset)) return false;
  if (f.read(reinterpret_cast<uint8_t*>(seg_.get()), sizeof(bilingual::Segment)) !=
      static_cast<int>(sizeof(bilingual::Segment))) {
    return false;
  }
  storyIdx_ = storyIdx;
  segIdx_ = segIdx;
  if (storyIdx_ < 16) savedSegByStory_[storyIdx_] = static_cast<uint8_t>(segIdx_);
  cardSaved_ = false;
  return true;
}

void BilingualActivity::loadProgress() {
  HalFile f;
  if (!Storage.exists(kStatePath) || !Storage.openFileForRead(kTag, kStatePath, f)) return;
  uint8_t buf[20] = {};
  if (f.read(buf, sizeof(buf)) == sizeof(buf)) {
    inStory_ = buf[0] != 0;
    storyIdx_ = buf[1];
    segIdx_ = buf[2];
    mode_ = buf[3] < 3 ? buf[3] : 0;
    memcpy(savedSegByStory_, buf + 4, 16);
  }
}

void BilingualActivity::saveProgress() const {
  if (!packReady_) return;
  HalFile f;
  if (!Storage.openFileForWrite(kTag, kStatePath, f)) return;
  uint8_t buf[20] = {};
  buf[0] = inStory_ ? 1 : 0;
  buf[1] = static_cast<uint8_t>(storyIdx_);
  buf[2] = static_cast<uint8_t>(segIdx_);
  buf[3] = static_cast<uint8_t>(mode_);
  memcpy(buf + 4, savedSegByStory_, 16);
  f.write(buf, sizeof(buf));
}

bool BilingualActivity::exportFlashcard() {
  if (!seg_ || seg_->cardFront[0] == '\0') return false;
  if (!Storage.exists(kFlashcardDir1)) Storage.mkdir(kFlashcardDir1);
  if (!Storage.exists(kFlashcardDir2)) Storage.mkdir(kFlashcardDir2);

  std::string existing;
  if (Storage.exists(kFlashcardCsv)) {
    HalFile rf;
    if (Storage.openFileForRead(kTag, kFlashcardCsv, rf)) {
      const size_t sz = rf.size();
      if (sz > 0 && sz < 65536) {
        existing.resize(sz);
        rf.read(existing.data(), sz);
      }
    }
  } else {
    existing = "question,answer\n";
  }

  const std::string line = csvEscape(seg_->cardFront) + "," + csvEscape(seg_->cardBack) + "\n";
  if (existing.find(seg_->cardFront) == std::string::npos) {
    existing += line;
    HalFile wf;
    if (!Storage.openFileForWrite(kTag, kFlashcardCsv, wf)) return false;
    wf.write(reinterpret_cast<const uint8_t*>(existing.data()), existing.size());
  }
  cardSaved_ = true;
  return true;
}

void BilingualActivity::routeAction(const int action, const int value) {
  switch (action) {
    case ActionSelectStory:
      if (value >= 0 && value < static_cast<int>(stories_.size())) {
        const int resumeSeg = value < 16 ? savedSegByStory_[value] : 0;
        if (loadSegment(value, resumeSeg)) {
          inStory_ = true;
          saveProgress();
          interactionsReady_ = false;
          requestUpdate();
        }
      }
      return;
    case ActionListPrev:
      if (listPage_ > 0) {
        --listPage_;
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionListNext:
      if ((listPage_ + 1) * kStoriesPerPage < static_cast<int>(stories_.size())) {
        ++listPage_;
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionPrevSeg:
      if (inStory_ && segIdx_ > 0) {
        loadSegment(storyIdx_, segIdx_ - 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionNextSeg:
      if (inStory_ && storyIdx_ < static_cast<int>(stories_.size()) &&
          segIdx_ + 1 < stories_[storyIdx_].segmentCount) {
        loadSegment(storyIdx_, segIdx_ + 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionCycleMode:
      mode_ = (mode_ + 1) % 3;
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionRevealQuiz:
      mode_ = 0;
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionSaveCard:
      exportFlashcard();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionBackToList:
      inStory_ = false;
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    default:
      return;
  }
}

void BilingualActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    if (inStory_) {
      routeAction(ActionBackToList, 0);
    } else {
      shelf::leave(renderer, mappedInput);
    }
    return;
  }

  if (packReady_) {
    const auto swipe = mappedInput.wasSwipe();
    if (mappedInput.wasPressed(MappedInputManager::Button::PageBack) ||
        mappedInput.wasPressed(MappedInputManager::Button::Up) || swipe == MappedInputManager::SwipeDir::Down ||
        swipe == MappedInputManager::SwipeDir::Right) {
      routeAction(inStory_ ? ActionPrevSeg : ActionListPrev, 0);
      return;
    }
    if (mappedInput.wasPressed(MappedInputManager::Button::PageForward) ||
        mappedInput.wasPressed(MappedInputManager::Button::Down) || swipe == MappedInputManager::SwipeDir::Up ||
        swipe == MappedInputManager::SwipeDir::Left) {
      routeAction(inStory_ ? ActionNextSeg : ActionListNext, 0);
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

void BilingualActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const int readerFont = SETTINGS.getReaderFontId();
  const toybox::Faces faces{toybox::kButtonFontId, readerFont, toybox::kDisplayFontId};
  fui::GfxRendererTarget target = toybox::makeTarget(renderer, faces);
  const fui::InputSnapshot noInput{};
  toybox::Frame frame(target, target.deviceContext(), noInput, interactions_);
  toybox::Screen screen(frame);

  const fui::Rect body = screen.body();
  const int16_t inner = static_cast<int16_t>(body.width - kMargin * 2);

  if (!packReady_ || stories_.empty()) {
    fui::HeaderProps header;
    header.title = "BILINGUAL";
    header.borderEdges = fui::EdgesNone;
    header.sidePadding = screen.theme().headerSidePadding;
    toybox::headerBand(screen, header);
    target.text(fui::Rect{kMargin, static_cast<int16_t>(body.y + 120), inner, 120},
                "Put /bilingual/texts.bin on the SD card to read graded Italian-Turkish-English stories.",
                makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 4));
    interactionsReady_ = true;
    renderer.displayBuffer();
    return;
  }

  if (!inStory_) {
    const int totalPages = (static_cast<int>(stories_.size()) + kStoriesPerPage - 1) / kStoriesPerPage;
    char badge[24];
    snprintf(badge, sizeof(badge), "PAGE %d/%d", listPage_ + 1, std::max(1, totalPages));
    fui::HeaderProps header;
    header.title = "BILINGUAL IT-TR";
    header.trailingLabel = badge;
    header.borderEdges = fui::EdgesNone;
    header.sidePadding = screen.theme().headerSidePadding;
    toybox::headerBand(screen, header);

    int16_t y = static_cast<int16_t>(body.y + 10);
    const int start = listPage_ * kStoriesPerPage;
    const int end = std::min<int>(start + kStoriesPerPage, stories_.size());
    const int16_t rowH = 102;

    for (int i = start; i < end; ++i) {
      const auto& st = stories_[i];
      const fui::Rect row{kMargin, y, inner, static_cast<int16_t>(rowH - 6)};
      // Level pill
      const fui::Rect pill{kMargin, static_cast<int16_t>(y + 8), 48, 28};
      target.fill(pill, fui::Paint::solid(fui::Color::Black));
      target.text(toybox::inkCentred(target, pill, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)), st.level,
                  makeStyle(toybox::kSmallFont, fui::TextAlign::Center, fui::Color::White));

      // Title
      target.text(fui::Rect{static_cast<int16_t>(kMargin + 58), static_cast<int16_t>(y + 6),
                            static_cast<int16_t>(inner - 58), 32},
                  st.title, makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 1, true));

      // Subtitle + progress
      char sub[96];
      const int saved = (i < 16) ? savedSegByStory_[i] : 0;
      snprintf(sub, sizeof(sub), "%s  (%d/%u)", st.subtitle, saved + 1, static_cast<unsigned>(st.segmentCount));
      target.text(fui::Rect{static_cast<int16_t>(kMargin + 58), static_cast<int16_t>(y + 42),
                            static_cast<int16_t>(inner - 58), 44},
                  sub, makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 2, false));

      target.fill(fui::Rect{kMargin, static_cast<int16_t>(row.bottom() + 2), inner, 1},
                  fui::Paint::solid(fui::Color::Black));
      frame.hit(row, ActionSelectStory, static_cast<int16_t>(i));
      y = static_cast<int16_t>(y + rowH);
    }

    const int16_t footY = static_cast<int16_t>(body.bottom() - 50);
    if (listPage_ > 0) {
      drawButton(screen, fui::Rect{kMargin, footY, 140, 40}, "< PREV", ActionListPrev, 0, false);
    }
    if (end < static_cast<int>(stories_.size())) {
      drawButton(screen, fui::Rect{static_cast<int16_t>(body.width - kMargin - 140), footY, 140, 40}, "NEXT >",
                 ActionListNext, 0, false);
    }

    interactionsReady_ = true;
    renderer.displayBuffer();
    return;
  }

  // Reader View
  const auto& meta = stories_[storyIdx_];
  char segBadge[24];
  snprintf(segBadge, sizeof(segBadge), "%s %d/%u", meta.level, segIdx_ + 1, static_cast<unsigned>(meta.segmentCount));

  fui::HeaderProps header;
  header.title = meta.title;
  header.trailingLabel = segBadge;
  header.leadingIcon = fui::bitmapFromIcon(icon_wiki_back_32);
  header.leadingAction = ActionBackToList;
  header.borderEdges = fui::EdgesNone;
  header.sidePadding = screen.theme().headerSidePadding;
  toybox::headerBand(screen, header);

  int16_t y = static_cast<int16_t>(body.y + 8);
  // Top Half: Italian Original
  target.text(fui::Rect{kMargin, y, inner, 22}, "ITALIANO",
              makeStyle(toybox::kSmallFont, fui::TextAlign::Left, fui::Color::Black, 1));
  y = static_cast<int16_t>(y + 24);
  target.text(fui::Rect{kMargin, y, inner, 250}, seg_->itText,
              makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 8, false));
  y = static_cast<int16_t>(y + 254);

  // Middle Action Bar
  static const char* const kModeLabels[3] = {"LANG: TR", "LANG: EN", "MODE: QUIZ"};
  drawButton(screen, fui::Rect{kMargin, y, 124, 38}, kModeLabels[mode_], ActionCycleMode, 0, false);
  drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + 132), y, 168, 38},
             cardSaved_ ? "SAVED TO CSV!" : "+ FLASHCARD", ActionSaveCard, 0, cardSaved_);
  drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + 308), y, 64, 38}, "<", ActionPrevSeg, 0, false);
  drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + 380), y, 68, 38}, ">", ActionNextSeg, 0, false);
  y = static_cast<int16_t>(y + 46);

  if (mode_ == 2) {
    // Quiz Mode: Translation hidden until tapped
    const fui::Rect quizBox{kMargin, y, inner, static_cast<int16_t>(body.bottom() - y - 12)};
    target.stroke(quizBox, fui::Paint::solid(fui::Color::Black), 2);
    target.text(fui::Rect{static_cast<int16_t>(kMargin + 20), static_cast<int16_t>(y + 90),
                          static_cast<int16_t>(inner - 40), 120},
                "QUIZ MODE: Read the Italian passage above, then tap here to reveal translation & grammar notes.",
                makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 4));
    frame.hit(quizBox, ActionRevealQuiz, 0);
  } else {
    target.text(fui::Rect{kMargin, y, inner, 22}, mode_ == 0 ? "TURKCE CEVIRI" : "ENGLISH TRANSLATION",
                makeStyle(toybox::kSmallFont, fui::TextAlign::Left, fui::Color::Black, 1));
    y = static_cast<int16_t>(y + 24);
    target.text(fui::Rect{kMargin, y, inner, 180}, mode_ == 0 ? seg_->trText : seg_->enText,
                makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 6, false));
    y = static_cast<int16_t>(y + 184);

    target.fill(fui::Rect{kMargin, y, inner, 1}, fui::Paint::solid(fui::Color::Black));
    y = static_cast<int16_t>(y + 6);
    target.text(fui::Rect{kMargin, y, inner, 22}, "GRAMMAR & VOCABULARY",
                makeStyle(toybox::kSmallFont, fui::TextAlign::Left, fui::Color::Black, 1));
    y = static_cast<int16_t>(y + 22);
    target.text(fui::Rect{kMargin, y, inner, 96}, seg_->vocabNote,
                makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 3, false));
    y = static_cast<int16_t>(y + 100);

    // Target flashcard preview at the bottom
    if (y + 32 <= body.bottom()) {
      char cardPreview[240];
      snprintf(cardPreview, sizeof(cardPreview), "CARD: %s -> %s", seg_->cardFront, seg_->cardBack);
      target.text(fui::Rect{kMargin, y, inner, static_cast<int16_t>(body.bottom() - y - 4)}, cardPreview,
                  makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 2, true));
    }
  }

  interactionsReady_ = true;
  renderer.displayBuffer();
}
