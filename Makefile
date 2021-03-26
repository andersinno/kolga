SHELL := /bin/sh

test:
	./run_tests.sh

sast-tests:
	./utils/check-sast

style-tests:
	./utils/check-style

typing-tests:
	./utils/check-typing

package-tests:
	./utils/check-packages

helm-tests:
	./utils/check-chart

static-tests: sast-tests typing-tests style-tests package-tests

docs:
	cd docs && $(MAKE) clean && $(MAKE) html

.PHONY: test, sast-tests, style-tests, typing-tests, packages-tests, helm-tests, docs
