#!/bin/sh
cd "${0%/*}" || exit
CUR_DIR=$(pwd -P)
# This two step process is performed to separate the CI logic (autosourcing the config)
# from the configuration build step (this script)
TARGET_DIR="$CUR_DIR"/../src/dodekaserver/resources/conf
echo "Building conf..."
rm -rf "$TARGET_DIR" || exit 1
cp -r "$CUR_DIR"/autosourced_config "$TARGET_DIR" || exit 1
