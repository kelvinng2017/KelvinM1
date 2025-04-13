#!/bin/bash

useCompiledFiles() {
  DIR=`echo $1 | sed 's/__pycache__//'`;
  rm $DIR/*.py && mv $DIR/__pycache__/* $DIR && rmdir $DIR/__pycache__ && for file in $DIR/*; do mv "$file" "`echo $file | sed 's/\.cpython-38//'`"; done
}

rm -rf agvc_test

mkdir agvc_test

# Compile server files
cd ~/agvc
python3.8 -m compileall .

# Copy all server files to another folder
cp -R ~/agvc/* ~/agvc_test/

# Remove all source files and move compiled files to correct folder
cd ~/agvc_test
export -f useCompiledFiles
find . -type d -name '__pycache__' -exec bash -c 'useCompiledFiles "{}"' \;

# Remove all compiled files
cd ~/agvc
find . -type d -name '__pycache__' -exec rm -rf {} \;

# Remove all not required to compiled files
rm ~/agvc_test/config.pyc ~/agvc_test/gunicorn.conf.pyc
