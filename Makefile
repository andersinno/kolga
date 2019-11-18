SHELL := /bin/sh

test:
	./run_tests.sh

style-tests:
	./check-style

typing-tests:
	./check-typing

typing-tests:
	./check-packages

docs:
	cd docs && $(MAKE) clean && $(MAKE) html

.PHONY: test, style-tests, typing-tests, packages-tests, docs
