CSS_TARGETS := common.min.css common.css index.min.css index.css lobby.min.css lobby.css common/fullwindow_canvas.min.css common/fullwindow_canvas.css

all: $(CSS_TARGETS)

FULLWINDOW_CANVAS_DEPS := common/fullwindow_canvas.less
common/fullwindow_canvas.css: $(FULLWINDOW_CANVAS_DEPS)
	lessc $(COMPILER_FLAGS) $< $@

common/fullwindow_canvas.min.css: $(FULLWINDOW_CANVAS_DEPS)
	lessc $(COMPILER_FLAGS) -x $< $@

COMMON_DEPS := common.less
common.css: $(COMMON_DEPS)
	lessc $(COMPILER_FLAGS) $< $@

common.min.css: $(COMMON_DEPS)
	lessc $(COMPILER_FLAGS) -x $< $@

INDEX_DEPS := index.less common/fullwindow_canvas.less
index.css: $(INDEX_DEPS)
	lessc $(COMPILER_FLAGS) $< $@

index.min.css: $(INDEX_DEPS)
	lessc $(COMPILER_FLAGS) -x $< $@

LOBBY_DEPS := lobby.less
lobby.css: $(LOBBY_DEPS)
	lessc $(COMPILER_FLAGS) $< $@

lobby.min.css: $(LOBBY_DEPS)
	lessc $(COMPILER_FLAGS) -x $< $@

clean:
	rm $(CSS_TARGETS)
