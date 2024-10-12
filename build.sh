#!/bin/bash

# Path to the addon.xml file
ADDON_XML="addon.xml"

# Extract the current version using a more robust method
CURRENT_VERSION=$(grep -o 'version="[0-9]\+\.[0-9]\+\.[0-9]\+"' $ADDON_XML | sed 's/version="//' | sed 's/"//')

# Check if the version was extracted successfully
if [ -z "$CURRENT_VERSION" ]; then
  echo "Failed to extract the current version from addon.xml"
  exit 1
fi

# Split the version into components
IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"

# Increment the minor version
VERSION_PARTS[1]=$((VERSION_PARTS[1] + 1))

# Construct the new version string
NEW_VERSION="${VERSION_PARTS[0]}.${VERSION_PARTS[1]}.${VERSION_PARTS[2]}"

# Update the version in addon.xml
sed -i '' "s/version=\"$CURRENT_VERSION\"/version=\"$NEW_VERSION\"/" $ADDON_XML

# Log the version update
echo "Updated version from $CURRENT_VERSION to $NEW_VERSION"

# Compress the project folder into a zip file, excluding .venv and .vscode directories
ZIP_FILE="plugin.video.skipintro-$NEW_VERSION.zip"
zip -r $ZIP_FILE . -x "*.git*" "*.DS_Store" "*.venv*" ".vscode*"
mv $ZIP_FILE ..
# Log the completion
echo "Compressed the project into $ZIP_FILE"
