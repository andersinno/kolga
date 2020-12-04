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

docs:
	cd docs && $(MAKE) clean && $(MAKE) html

.PHONY: test, sast-tests, style-tests, typing-tests, packages-tests, docs
