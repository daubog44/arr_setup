#!/bin/sh
set -eu

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef dist-upgrade -y

if [ -f /var/run/reboot-required ]; then
  echo "REBOOT_REQUIRED=1"
else
  echo "REBOOT_REQUIRED=0"
fi
