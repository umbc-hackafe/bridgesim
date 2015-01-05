JS_TARGETS := index.min.js three/three.min.js

THREE := three/three.js three/OBJMTLLoader.js three/OBJLoader.js three/MTLLoader.js three/DDSLoader.js three/CompressedTextureLoader.js three/Group.js

COMPILE_FLAGS=--compilation_level SIMPLE --language_in ECMASCRIPT5 --jscomp_off=globalThis --jscomp_off=checkTypes

all: $(JS_TARGETS)

three/three.min.js: $(THREE)
	closure $(COMPILE_FLAGS) --js_output_file $@ $^

index.min.js: index.js client.js map.js $(THREE)
	closure $(COMPILE_FLAGS) --js_output_file $@ $^

clean:
	rm $(JS_TARGETS)
