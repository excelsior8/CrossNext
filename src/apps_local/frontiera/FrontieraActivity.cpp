#include "FrontieraActivity.h"

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

constexpr const char* kTag = "FRONT";
constexpr const char* kPackPath = "/frontiera/cases.bin";
constexpr const char* kStatePath = "/frontiera/state.bin";
constexpr int16_t kMargin = 16;

enum : fui::ActionId {
  ActionToggleLang = 1,
  ActionPrevCase = 2,
  ActionNextCase = 3,
  ActionApprove = 4,
  ActionDeny = 5,
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

std::unique_ptr<Activity> FrontieraActivity::create(GfxRenderer& renderer, MappedInputManager& mappedInput) {
  return makeUniqueNoThrow<FrontieraActivity>(renderer, mappedInput);
}

void FrontieraActivity::onEnter() {
  Activity::onEnter();
  toybox::ensureFonts(renderer);
  cur_ = makeUniqueNoThrow<frontiera::FrontieraCase>();
  loadProgress();
  packReady_ = loadCase(caseIdx_);
  interactionsReady_ = false;
  requestUpdate();
}

void FrontieraActivity::onExit() {
  saveProgress();
  cur_.reset();
  Activity::onExit();
}

void FrontieraActivity::loadProgress() {
  HalFile f;
  if (!Storage.exists(kStatePath) || !Storage.openFileForRead(kTag, kStatePath, f)) return;
  uint8_t buf[6] = {};
  if (f.read(buf, 6) == 6) {
    caseIdx_ = buf[0];
    italian_ = buf[1] != 0;
    correctMask_ = static_cast<uint16_t>(buf[2] | (buf[3] << 8));
    attemptedMask_ = static_cast<uint16_t>(buf[4] | (buf[5] << 8));
  }
}

void FrontieraActivity::saveProgress() const {
  if (!packReady_) return;
  HalFile f;
  if (!Storage.openFileForWrite(kTag, kStatePath, f)) return;
  const uint8_t buf[6] = {
      static_cast<uint8_t>(caseIdx_),
      static_cast<uint8_t>(italian_ ? 1 : 0),
      static_cast<uint8_t>(correctMask_ & 0xFF),
      static_cast<uint8_t>((correctMask_ >> 8) & 0xFF),
      static_cast<uint8_t>(attemptedMask_ & 0xFF),
      static_cast<uint8_t>((attemptedMask_ >> 8) & 0xFF),
  };
  f.write(buf, 6);
}

bool FrontieraActivity::loadCase(int idx) {
  if (!cur_) return false;
  HalFile f;
  if (!Storage.exists(kPackPath) || !Storage.openFileForRead(kTag, kPackPath, f)) return false;
  frontiera::FrontieraHeader hdr{};
  if (f.read(reinterpret_cast<uint8_t*>(&hdr), sizeof(hdr)) != static_cast<int>(sizeof(hdr)) ||
      memcmp(hdr.magic, "CNFR0001", 8) != 0 || hdr.caseCount == 0) {
    return false;
  }
  caseCount_ = hdr.caseCount;
  if (idx < 0) idx = caseCount_ - 1;
  if (idx >= caseCount_) idx = 0;
  caseIdx_ = idx;
  const size_t offset =
      sizeof(frontiera::FrontieraHeader) + static_cast<size_t>(caseIdx_) * sizeof(frontiera::FrontieraCase);
  if (!f.seek(offset)) return false;
  if (f.read(reinterpret_cast<uint8_t*>(cur_.get()), sizeof(frontiera::FrontieraCase)) !=
      static_cast<int>(sizeof(frontiera::FrontieraCase))) {
    return false;
  }
  stamped_ = false;
  return true;
}

void FrontieraActivity::drawPortrait(const int x0, const int y0) const {
  if (!cur_) return;
  renderer.fillRect(x0 - 2, y0 - 2, 124, 124, false);
  renderer.drawRect(x0 - 2, y0 - 2, 124, 124, 2, true);
  const uint8_t* bmp = cur_->portrait;
  for (int r = 0; r < 120; ++r) {
    const uint8_t* row = bmp + r * 15;
    for (int b = 0; b < 15; ++b) {
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

void FrontieraActivity::routeAction(const int action, const int) {
  switch (action) {
    case ActionToggleLang:
      italian_ = !italian_;
      saveProgress();
      interactionsReady_ = false;
      requestUpdate();
      return;
    case ActionPrevCase:
      if (packReady_) {
        loadCase(caseIdx_ - 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionNextCase:
      if (packReady_) {
        loadCase(caseIdx_ + 1);
        saveProgress();
        interactionsReady_ = false;
        requestUpdate();
      }
      return;
    case ActionApprove:
    case ActionDeny: {
      if (!cur_ || stamped_) return;
      const bool approve = (action == ActionApprove);
      stamped_ = true;
      lastStampApprove_ = approve;
      lastCorrect_ = (approve == (cur_->shouldApprove != 0));
      if (caseIdx_ < 16) {
        attemptedMask_ |= static_cast<uint16_t>(1u << caseIdx_);
        if (lastCorrect_) {
          correctMask_ |= static_cast<uint16_t>(1u << caseIdx_);
        } else {
          correctMask_ &= static_cast<uint16_t>(~(1u << caseIdx_));
        }
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

void FrontieraActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    shelf::leave(renderer, mappedInput);
    return;
  }
  if (packReady_) {
    if (mappedInput.wasPressed(MappedInputManager::Button::PageBack) ||
        mappedInput.wasPressed(MappedInputManager::Button::Up)) {
      routeAction(ActionPrevCase, 0);
      return;
    }
    if (mappedInput.wasPressed(MappedInputManager::Button::PageForward) ||
        mappedInput.wasPressed(MappedInputManager::Button::Down)) {
      routeAction(ActionNextCase, 0);
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

void FrontieraActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const int readerFont = SETTINGS.getReaderFontId();
  const toybox::Faces faces{toybox::kButtonFontId, readerFont, toybox::kDisplayFontId};
  fui::GfxRendererTarget target = toybox::makeTarget(renderer, faces);
  const fui::InputSnapshot noInput{};
  toybox::Frame frame(target, target.deviceContext(), noInput, interactions_);
  toybox::Screen screen(frame);

  fui::HeaderProps header;
  header.title = italian_ ? "FRONTIERA • ISPEZIONE" : "FRONTIERA • INSPECTOR";
  header.trailingLabel = italian_ ? "LANG: IT" : "LANG: EN";
  header.trailingAction = ActionToggleLang;
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

  if (!packReady_ || !cur_) {
    target.text(fui::Rect{kMargin, static_cast<int16_t>(body.y + 120), inner, 120},
                "Put /frontiera/cases.bin on the SD card to play Frontiera (Papers, Please 1-Bit).",
                makeStyle(toybox::kBodyFont, fui::TextAlign::Center, fui::Color::Black, 4));
    interactionsReady_ = true;
    renderer.displayBuffer();
    return;
  }

  int solved = 0;
  for (int b = 0; b < 16; ++b) {
    if (correctMask_ & (1u << b)) ++solved;
  }

  int16_t y = static_cast<int16_t>(body.y + 8);
  drawButton(screen, fui::Rect{kMargin, y, 48, 38}, "<", ActionPrevCase, 0, false);
  drawButton(screen, fui::Rect{static_cast<int16_t>(body.width - kMargin - 48), y, 48, 38}, ">", ActionNextCase, 0,
             false);

  char statusLine[80];
  snprintf(statusLine, sizeof(statusLine), "%s #%d/%d • %s: %s • OK:%d", italian_ ? "CASO" : "CASE", caseIdx_ + 1,
           caseCount_, italian_ ? "OGGI" : "TODAY", cur_->dayDate, solved);
  const fui::Rect statusBox{static_cast<int16_t>(kMargin + 54), y, static_cast<int16_t>(inner - 108), 38};
  target.text(toybox::inkCentred(target, statusBox, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)), statusLine,
              makeStyle(toybox::kSmallFont, fui::TextAlign::Center));
  y = static_cast<int16_t>(y + 46);

  // Applicant Portrait + Passport Box
  drawPortrait(20, y + 2);
  const int16_t px = 150;
  const int16_t pw = static_cast<int16_t>(body.width - kMargin - px);
  target.stroke(fui::Rect{px, y, pw, 124}, fui::Paint::solid(fui::Color::Black), 2);

  char line1[64], line2[64], line3[64], line4[64];
  snprintf(line1, sizeof(line1), "%s", cur_->applicantName);
  snprintf(line2, sizeof(line2), "%s • %s", cur_->nationality, cur_->issuingCity);
  snprintf(line3, sizeof(line3), "ID: %s  EXP: %s", cur_->passportNo, cur_->expiryDate);
  snprintf(line4, sizeof(line4), "%u kg • %s: %s", static_cast<unsigned>(cur_->weightKg),
           italian_ ? "TIMBRO" : "SEAL",
           cur_->hasPermitStamp ? (italian_ ? "VALIDO" : "VALID") : (italian_ ? "SOSPETTO/ASSENTE" : "SUSPECT/NONE"));

  target.text(fui::Rect{static_cast<int16_t>(px + 8), static_cast<int16_t>(y + 6), static_cast<int16_t>(pw - 16), 28},
              line1, makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 1, true));
  target.text(fui::Rect{static_cast<int16_t>(px + 8), static_cast<int16_t>(y + 34), static_cast<int16_t>(pw - 16), 26},
              line2, makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 1));
  target.text(fui::Rect{static_cast<int16_t>(px + 8), static_cast<int16_t>(y + 62), static_cast<int16_t>(pw - 16), 26},
              line3, makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 1));
  target.text(fui::Rect{static_cast<int16_t>(px + 8), static_cast<int16_t>(y + 90), static_cast<int16_t>(pw - 16), 26},
              line4, makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 1));
  y = static_cast<int16_t>(y + 132);

  // Daily Bulletin Box
  target.text(fui::Rect{kMargin, y, inner, 20},
              italian_ ? "ORDINI DEL MINISTERO (REGOLE):" : "MINISTRY BULLETIN (CHECKPOINT RULES):",
              makeStyle(toybox::kSmallFont));
  y = static_cast<int16_t>(y + 22);
  target.text(fui::Rect{kMargin, y, inner, 118}, italian_ ? cur_->rulesIt : cur_->rulesEn,
              makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 4));
  y = static_cast<int16_t>(y + 122);
  target.fill(fui::Rect{kMargin, y, inner, 1}, fui::Paint::solid(fui::Color::Black));
  y = static_cast<int16_t>(y + 6);

  // Entry Permit Box
  target.text(fui::Rect{kMargin, y, inner, 20},
              italian_ ? "PERMESSO D'INGRESSO E DOGANA:" : "ENTRY PERMIT & CUSTOMS DECLARATION:",
              makeStyle(toybox::kSmallFont));
  y = static_cast<int16_t>(y + 22);
  target.text(fui::Rect{kMargin, y, inner, 92}, italian_ ? cur_->docPermitIt : cur_->docPermitEn,
              makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 3));
  y = static_cast<int16_t>(y + 96);
  target.fill(fui::Rect{kMargin, y, inner, 1}, fui::Paint::solid(fui::Color::Black));
  y = static_cast<int16_t>(y + 6);

  if (!stamped_) {
    target.text(fui::Rect{kMargin, y, inner, 20},
                italian_ ? "DICHIARAZIONE VERBALE:" : "APPLICANT SPOKEN STATEMENT:", makeStyle(toybox::kSmallFont));
    y = static_cast<int16_t>(y + 22);
    target.text(fui::Rect{kMargin, y, inner, 110}, italian_ ? cur_->dialogueIt : cur_->dialogueEn,
                makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 4));

    const int16_t btnY = static_cast<int16_t>(body.bottom() - 56);
    const int16_t halfW = static_cast<int16_t>((inner - 12) / 2);
    drawButton(screen, fui::Rect{kMargin, btnY, halfW, 48}, italian_ ? "APPROVA (OK)" : "APPROVE (STAMP)",
               ActionApprove, 0, true);
    drawButton(screen, fui::Rect{static_cast<int16_t>(kMargin + halfW + 12), btnY, halfW, 48},
               italian_ ? "RIFIUTA (STOP)" : "DENY (REJECT)", ActionDeny, 0, false);
  } else {
    char verdict[80];
    if (lastCorrect_) {
      snprintf(verdict, sizeof(verdict), "%s (%s)",
               italian_ ? "DECISIONE CORRETTA!" : "INSPECTION CORRECT!",
               lastStampApprove_ ? (italian_ ? "APPROVATO" : "APPROVED") : (italian_ ? "RIFIUTATO" : "DENIED"));
    } else {
      snprintf(verdict, sizeof(verdict), "%s (%s)",
               italian_ ? "NOTA DISCIPLINARE: ERRORE!" : "MINISTRY CITATION: ERROR!",
               lastStampApprove_ ? (italian_ ? "APPROVATO" : "APPROVED") : (italian_ ? "RIFIUTATO" : "DENIED"));
    }
    const fui::Rect vBox{kMargin, y, inner, 28};
    target.fill(vBox, fui::Paint::solid(fui::Color::Black));
    target.text(toybox::inkCentred(target, vBox, makeStyle(toybox::kSmallFont, fui::TextAlign::Center)), verdict,
                makeStyle(toybox::kSmallFont, fui::TextAlign::Center, fui::Color::White));
    y = static_cast<int16_t>(y + 32);

    target.text(fui::Rect{kMargin, y, inner, 104}, italian_ ? cur_->auditIt : cur_->auditEn,
                makeStyle(toybox::kBodyFont, fui::TextAlign::Left, fui::Color::Black, 4));

    const int16_t btnY = static_cast<int16_t>(body.bottom() - 54);
    drawButton(screen, fui::Rect{kMargin, btnY, inner, 46},
               italian_ ? "PROSSIMO RICHIEDENTE >" : "NEXT APPLICANT >", ActionNextCase, 0, true);
  }

  interactionsReady_ = true;
  renderer.displayBuffer();
}
