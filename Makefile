SHELL := /bin/sh

test:
	./run_tests.sh

style-tests:
	./check-style

typing-tests:
	./check-typing

typing-tests:
	./check-packages

.PHONY: test, style-tests, typing-tests, packages-tests
