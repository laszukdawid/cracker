#!/usr/bin/env bash
set -x
INSTALL_DIR=$(pwd)
echo "Install dir $INSTALL_DIR"

cd ..
echo "cd $(pwd)" > cracker
echo "python3 -m cracker.main" >> cracker

chmod +x cracker


# These two require root permission.
# TODO: Install it locally
mv cracker /usr/bin/
cp $INSTALL_DIR/cracker.desktop /usr/share/applications/
cp $INSTALL_DIR/papuga.jpeg ~/.local/share/icons/
