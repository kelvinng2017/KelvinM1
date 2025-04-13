#!/usr/bin/env sh

if ["${1}" == ""]; then
    unzip -o secsgem.zip -d /home/${USER}/.local/lib/python2.7/site-packages
else
    unzip -o secsgem.zip -d /home/${USER}/.local/lib/python${1}/site-packages
fi
