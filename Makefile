SHELL := /bin/sh

PORT := 8004

.PHONY: run css

run:
	osascript launch.scpt $(PORT)

css:
	npm run gulp:build
