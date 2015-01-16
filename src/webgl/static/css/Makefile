LESS_TARGETS := lobby.less index.less

CSS_TARGETS := $(patsubst %.less, %.css, $(LESS_TARGETS))
MIN_CSS_TARGETS := $(patsubst %.less, %.min.css, $(LESS_TARGETS))

DEPS := $(patsubst %, %.d, $(CSS_TARGETS) $(MIN_CSS_TARGETS))

all: $(CSS_TARGETS) $(MIN_CSS_TARGETS)

-include $(DEPS)

%.css: %.less
	lessc -M $< $@ > $@.d
	lessc $< $@

%.min.css: %.less
	lessc -M $< $@ > $@.d
	lessc -x $< $@

clean:
	rm $(CSS_TARGETS) $(MIN_CSS_TARGETS) $(DEPS)
