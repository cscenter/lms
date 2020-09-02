#!/bin/sh -f

# Trigger a new Travis-CI job.
# Ordinarily, a new Travis job is triggered when a commit is pushed to a
# GitHub repository.  The trigger-travis.sh script provides a programmatic
# way to trigger a new Travis job.

# Usage:
#   trigger-travis.sh [--branch BRANCH] GITHUBID GITHUBPROJECT TRAVIS_ACCESS_TOKEN TRAVIS_BUILD_ID [MESSAGE]
# For example:
#   trigger-travis.sh typetools checker-framework `cat ~/private/.travis-access-token` "Trigger for testing"
#
# where TRAVIS_ACCESS_TOKEN is, or ~/private/.travis-access-token contains,
# the Travis access token.
#
# Your Travis access token is the text after "Your access token is " in
# the output of this compound command:
#   travis login && travis token
# (If the travis program isn't installed, then use either of these two commands:
#    gem install travis
#    sudo apt-get install ruby-dev && sudo gem install travis
# Don't do "sudo apt-get install travis" which installs a trajectory analyzer.)
# Note that the Travis access token output by `travis token` differs from the
# Travis token available at https://travis-ci.org/profile .
# If you store it in a file, make sure the file is not readable by others,
# for example by running:  chmod og-rwx ~/private/.travis-access-token

# To use this script to trigger a dependent build in Travis, do two things:
#
# 1. Set an environment variable TRAVIS_ACCESS_TOKEN by navigating to
#   https://travis-ci.org/MYGITHUBID/MYGITHUBPROJECT/settings
# The TRAVIS_ACCESS_TOKEN environment variable will be set when Travis runs
# the job, but won't be visible to anyone browsing https://travis-ci.org/.
#
# 2. Add the following to your .travis.yml file, where you replace
# OTHERGITHUB* by a specific downstream project, but you leave
# $TRAVIS_ACCESS_TOKEN as literal text:
#
# jobs:
#   include:
#     - stage: trigger downstream
#       jdk: oraclejdk8
#       script: |
#         echo "TRAVIS_BRANCH=$TRAVIS_BRANCH TRAVIS_PULL_REQUEST=$TRAVIS_PULL_REQUEST"
#         if [[ ($TRAVIS_BRANCH == master) &&
#               ($TRAVIS_PULL_REQUEST == false) ]] ; then
#           curl -LO --retry 3 https://raw.github.com/mernst/plume-lib/master/bin/trigger-travis.sh
#           sh trigger-travis.sh OTHERGITHUBID OTHERGITHUBPROJECT $TRAVIS_ACCESS_TOKEN
#         fi

# TODO: Show how to use the --branch command-line argument.
# TODO: Enable the script to clone a particular branch rather than master.
# This would require a way to know the relationships among branches in
# different GitHub projects.  It's easier to run all your tests within a
# single Travis job, if they fit within Travis's 50-minute time limit.

# An alternative to this script would be to install the Travis command-line
# client and then run:
#   travis restart -r OTHERGITHUBID/OTHERGITHUBPROJECT
# That is undesirable because it restarts an old job, destroying its history,
# rather than starting a new job which is our goal.

# Parts of this script were originally taken from
# http://docs.travis-ci.com/user/triggering-builds/


if [ "$#" -lt 3 ] || [ "$#" -ge 6 ]; then
  echo "Wrong number of arguments $# to trigger-travis.sh; run like:"
  echo " trigger-travis.sh [--branch BRANCH] GITHUBID GITHUBPROJECT TRAVIS_ACCESS_TOKEN [MESSAGE]" >&2
  exit 1
fi

if [ "$1" = "--branch" ] ; then
  shift
  BRANCH="$1"
  shift
else
  BRANCH=master
fi

USER=$1
REPO=$2
TOKEN=$3
TRAVIS_BUILD_ID=$4
if [ $# -eq 5 ] ; then
    MESSAGE=",\"message\": \"$5\""
elif [ -n "$TRAVIS_REPO_SLUG" ] ; then
    MESSAGE=",\"message\": \"Triggered by upstream build of $TRAVIS_REPO_SLUG commit "`git rev-parse --short HEAD`"\""
else
    MESSAGE=""
fi
## For debugging:
# echo "USER=$USER"
# echo "REPO=$REPO"
# echo "TOKEN=$TOKEN"
# echo "MESSAGE=$MESSAGE"

body="{
  \"request\": {
    \"branch\":\"$BRANCH\",
    \"mode\":\"deep_merge_append\",
    \"config\": {
      \"env\": [
          \"DOCKER_COMPOSE_VERSION=1.25.5 DOCKER_BUILD_ID=$TRAVIS_BUILD_ID\"
      ]
    }
    $MESSAGE
  }
}"

# It does not work to put / in place of %2F in the URL below.  I'm not sure why.
curl -s -v -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Travis-API-Version: 3" \
  -H "Authorization: token ${TOKEN}" \
  -d "$body" \
  https://api.travis-ci.com/repo/${USER}%2F${REPO}/requests \
 | tee /tmp/travis-request-output.$$.txt

if grep -q '"@type": "error"' /tmp/travis-request-output.$$.txt; then
    exit 1
fi
if grep -q 'access denied' /tmp/travis-request-output.$$.txt; then
    exit 1
fi