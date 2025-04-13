#!/bin/bash

rm -rf ~/tsc_backup
rm -rf ~/Tsc_Core

mkdir ~/tsc_backup
mkdir ~/Tsc_Core

# Compile server files
cd ./
chmod 777 *.py
chmod 777 *.sh
python2 -m  compileall ./

# Copy all server files to another folder
cp -R ./  ~/tsc_backup
cp -R ./  ~/Tsc_Core

# Remove all source files and move compiled files to correct folder
cd ~/Tsc_Core

rm -rf ./*.py
rm -rf ./auto_setting_file/*
rm -rf ./algorithm/*.py
rm -rf ./erack/*.py
rm -rf ./iot/*.py
rm -rf ./semi/*.py
rm -rf ./vehicles/*.py
rm -rf ./workstation/*.py
rm -rf *.gz
rm -rf *.sml
rm -rf *.bak
rm -rf ./log/*


cp ~/tsc_backup/controller.py ./
rm -rf ~/tsc_backup

