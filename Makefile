default: build

.PHONY: build
build:
	python ./setup.py build develop;

test:
	true

clean:
	true