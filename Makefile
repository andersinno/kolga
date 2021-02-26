SHELL := /bin/sh

test:
	./run_tests.sh

sast-tests:
	./check-sast

style-tests:
	./check-style

typing-tests:
	./check-typing

package-tests:
	./check-packages

static-tests: sast-tests typing-tests style-tests package-tests

docs:
	cd docs && $(MAKE) clean && $(MAKE) html

.PHONY: test, sast-tests, style-tests, typing-tests, packages-tests, docs
