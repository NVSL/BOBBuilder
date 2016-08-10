default: build

.PHONY: build
build:
	pip install -e .

test:
	true

clean:
	true