#!/bin/bash

# export the blueprints directory to an environment variable so we know where to find the infrastructure code
# to do the deploy. For local deploy, this assumes that the blueprints repo is a "sibling" to this
# project in your folder structure.
export BLUEPRINTS_DIR="../contentful_aleph_blueprints"
export LOCAL_DEPLOY=true

# provide some friendly defaults so the user does not need to assuming they are deploying a dev build
export STAGE=${STAGE:="dev"}
export STACK_NAME=${STACK_NAME:="contentful-aleph-${STAGE}"}
export OWNER=${OWNER:=$(id -un)}
export CONTACT=${CONTACT:=$OWNER@nd.edu}
export VERSION=$(git rev-parse HEAD) # used by sentry. Right now we are just using the commit SHA.
export GITHUB_REPO=$(git config --get remote.origin.url | sed 's/.*\/\([^ ]*\/[^.]*\).*/\1/') # ndlib/contentful_maps

./scripts/codebuild/install.sh || { exit 1; }
./scripts/codebuild/pre_build.sh || { exit 1; }
./scripts/codebuild/build.sh "$@" || { exit 1; } # you can pass parameters to the cdk deploy command (such as context)
./scripts/codebuild/post_build.sh || { exit 1; }
