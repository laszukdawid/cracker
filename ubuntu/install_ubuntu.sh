#!/usr/bin/env bash
install_dir=$(pwd)
echo "Install dir $install_dir"

cd ..
echo "cd $(pwd)" > cracker
echo "python3 -m aws_polly_gui.main" >> cracker

chmod +x cracker


# These two require root permission.
# TODO: Install it locally
mv cracker /usr/bin/
cp $install_dir/cracker.desktop /usr/share/applications/
cp $install_dir/papuga.jpeg ~/.local/share/icons/
