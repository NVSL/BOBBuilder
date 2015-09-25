default: build test

.PHONY: build
build:
	python ./setup.py build develop;
