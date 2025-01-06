#!/usr/bin/env bash
##
# Run tests in CI.
#
set -ex

echo "::group::Lint"
ahoy lint
echo "::endgroup::"

echo "::group::Unit Test"
ahoy test-unit
echo "::endgroup::"

echo "::group::Install Site"
ahoy install-site
echo "::endgroup::"
echo "::group::BDD testing"
ahoy test-bdd
echo "::endgroup::"

