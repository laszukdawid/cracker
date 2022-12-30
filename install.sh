set -e

# Ubuntu specific installation
sudo apt-get install -y pyqt5-dev python3-pyqt5 python3-pyqt5.qtmultimedia vlc libvlc-dev

#apt install -y gstreamer1.0-plugins-bad
#apt install -y gstreamer1.0-qt5
#apt install -y gstreamer1.0-nice
#apt install -y libgstreamer-plugins-bad1.0-dev
#apt install -y libqt5multimedia5-plugins
#apt install -y libqt5gstreamer-dev
#apt install -y libqt5gstreamer-1.0-0

printf "\n\n"
echo "Remember to remove ~/.local/.../PyQt5*"
