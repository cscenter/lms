SHELL := /bin/sh

PORT := 8004

.PHONY: run

run:
	osascript launch.scpt $(PORT)
