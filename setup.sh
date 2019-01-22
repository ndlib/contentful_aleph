#!/bin/bash

mkdir -p hesburgh_util_pip
mkdir -p lib

# This zip contains amazon linux compiled libs
unzip gevent.zip -d lib

# install for deployment
pip install hesburgh-utilities==1.0.9 -t hesburgh_util_pip

# install for local development, zip is used for deployment
pip install gevent --user

pushd lib
ln -sf ../hesburgh_util_pip/hesburgh
popd
