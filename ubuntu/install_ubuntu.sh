#!/usr/bin/env bash
set -e
INSTALL_DIR=$(pwd)
echo "Install dir $INSTALL_DIR"

cd ..
if [[ ! -d .venv ]] && [[ ! -d .env ]] && [[ -z ${FORCE} ]]
then
    echo "You likely haven't created virtual environment for this package."
    echo "I know this because there isn't .venv nor .env directory."
    echo "If I'm incorrect then use FORCE=true flag, i.e."
    echo "\`FORCE=true bash install_ubuntu.sh\`"
    exit 0
fi

cat << EOF > cracker_tmp
cd $(pwd)
.venv/bin/python -m cracker.main
EOF

chmod +x cracker_tmp


# These two require root permission.
cp $INSTALL_DIR/cracker.desktop ~/.local/share/applications/
# sudo cp $INSTALL_DIR/icon.jpeg ~/.local/share/icons/cracker.jpeg
cp $INSTALL_DIR/icon.png ~/.local/share/icons/cracker.png
sudo mv cracker_tmp /usr/bin/cracker
