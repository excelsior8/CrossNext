#pragma once
#include "../../activities/Activity.h"
#include "InterceptScreens.h"
class InterceptActivity final : public Activity {
 public:
  InterceptActivity(GfxRenderer& r, MappedInputManager& i) : Activity("Intercept", r, i) {}
  static std::unique_ptr<Activity> create(GfxRenderer&, MappedInputManager&);
  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  intercept::State state;
  intercept::StoryMeta extraMetas[intercept::MAX_EXTRA_STORIES]{};
  intercept::DiskNode currentDiskNode{};
  unsigned extraCount = 0;
  int storyIndex = 0;
  sdart::Pack assets;
  interceptui::View view = interceptui::View::Menu;
  interceptui::Work work;
  toybox::Interactions interactions;
  int selected = 0, page = 0;
  bool ready = false, writable = true, failed = false;
  const intercept::StoryMeta* currentMeta() const {
    return (storyIndex > 0 && unsigned(storyIndex) <= extraCount) ? &extraMetas[storyIndex - 1] : nullptr;
  }
  const char* currentSlug() const {
    const auto* m = currentMeta();
    return m ? m->slug : nullptr;
  }
  uint16_t currentMaxNodes() const {
    const auto* m = currentMeta();
    return m ? m->nodeCount : intercept::nodeCount;
  }
  void openStoryAssets();
  void syncActiveStory();
  void action(freeink::ui::ActionId, int);
  void back();
};
