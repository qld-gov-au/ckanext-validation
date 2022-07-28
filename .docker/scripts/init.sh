#!/usr/bin/env sh
##
# Initialise CKAN data for testing.
#
set -e

if [ "$VENV_DIR" != "" ]; then
  . ${VENV_DIR}/bin/activate
fi
CLICK_ARGS="--yes" ckan_cli db clean
ckan_cli db init
ckan_cli db upgrade

# Initialise validation tables
PASTER_PLUGIN=ckanext-validation ckan_cli validation init-db

# Create some base test data
. $APP_DIR/scripts/create-test-data.sh
