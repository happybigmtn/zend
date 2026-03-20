#!/bin/bash
#
# fetch_upstreams.sh - Fetch pinned upstream dependencies
#
# Reads upstream/manifest.lock.json and checks out each dependency to third_party/
# Idempotent: rerunning updates existing checkouts to pinned revision
#
set -e

MANIFEST="upstream/manifest.lock.json"
THIRD_PARTY="third_party"

if [ ! -f "$MANIFEST" ]; then
    echo "Error: Manifest not found at $MANIFEST"
    exit 1
fi

# Create third_party directory if it doesn't exist
mkdir -p "$THIRD_PARTY"

# Check for jq dependency
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed"
    exit 1
fi

echo "Reading manifest: $MANIFEST"

# Get list of dependency names
deps=$(jq -r '.dependencies | keys[]' "$MANIFEST")

for dep in $deps; do
    echo ""
    echo "Processing: $dep"

    repo_url=$(jq -r ".dependencies[\"$dep\"].repository" "$MANIFEST")
    pinned_ref=$(jq -r ".dependencies[\"$dep\"].pinned_ref" "$MANIFEST")
    dep_type=$(jq -r ".dependencies[\"$dep\"].type" "$MANIFEST")

    target_dir="$THIRD_PARTY/$dep"

    if [ -d "$target_dir" ]; then
        echo "  Updating existing checkout: $target_dir"

        cd "$target_dir"

        # Fetch latest changes
        git fetch origin

        # Handle different pin types
        if [ "$pinned_ref" = "latest-release" ]; then
            # Find latest release tag
            latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
            if [ -n "$latest_tag" ]; then
                git checkout "$latest_tag"
                echo "  Checked out latest release: $latest_tag"
            else
                echo "  Warning: No release tags found, staying on current branch"
            fi
        else
            # Checkout the pinned ref (branch or tag)
            git checkout "$pinned_ref"
            echo "  Checked out: $pinned_ref"
        fi

        cd - > /dev/null
    else
        echo "  Cloning: $repo_url"

        # Clone the repository
        git clone "$repo_url" "$target_dir"

        cd "$target_dir"

        # Handle different pin types
        if [ "$pinned_ref" = "latest-release" ]; then
            # Find latest release tag
            latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
            if [ -n "$latest_tag" ]; then
                git checkout "$latest_tag"
                echo "  Checked out latest release: $latest_tag"
            else
                echo "  Warning: No release tags found, staying on main branch"
            fi
        else
            # Checkout the pinned ref (branch or tag)
            if git rev-parse --verify "$pinned_ref" &> /dev/null; then
                git checkout "$pinned_ref"
                echo "  Checked out: $pinned_ref"
            else
                echo "  Warning: Ref '$pinned_ref' not found, using default branch"
            fi
        fi

        cd - > /dev/null
    fi

    purpose=$(jq -r ".dependencies[\"$dep\"].purpose" "$MANIFEST")
    echo "  Purpose: $purpose"
done

echo ""
echo "Upstream fetch complete. Dependencies in: $THIRD_PARTY/"
