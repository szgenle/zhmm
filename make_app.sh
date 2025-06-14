#!/bin/zsh
rm -rf build dist
rm -rf ./QiJie.spec

poetry add pyinstaller --group dev
#cp -rf ../zimo/resources/ ./QiJie/resources/
#cd QiJie
#pyinstaller --onefile --windowed --name "zhmm" --add-data "resources/*:resources"  --icon=myicon.icns zhmm/main.py --paths zhmm/
poetry run pyinstaller --onefile --windowed --name "zhmm" --osx-bundle-identifier "com.szgenle.zhmm" --icon=myicon.icns zhmm/main.py --paths zhmm/
