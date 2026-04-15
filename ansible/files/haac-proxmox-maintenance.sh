#!/bin/sh
set -eu

codename="$(. /etc/os-release && printf '%s' "${VERSION_CODENAME:-bookworm}")"

if [ -f /etc/apt/sources.list.d/pve-enterprise.list ]; then
  sed -i -E 's/^(deb .*enterprise.*)$/# \1/' /etc/apt/sources.list.d/pve-enterprise.list || true
fi

if [ -f /etc/apt/sources.list.d/ceph.list ]; then
  sed -i -E 's/^(deb .*enterprise.*)$/# \1/' /etc/apt/sources.list.d/ceph.list || true
fi

marker_begin="# BEGIN ANSIBLE MANAGED: Proxmox no-subscription repo"
marker_end="# END ANSIBLE MANAGED: Proxmox no-subscription repo"
repo_line="deb http://download.proxmox.com/debian/pve ${codename} pve-no-subscription"

if ! grep -Fq "$marker_begin" /etc/apt/sources.list 2>/dev/null; then
  {
    printf '%s\n' "$marker_begin"
    printf '%s\n' "$repo_line"
    printf '%s\n' "$marker_end"
  } >> /etc/apt/sources.list
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef dist-upgrade -y

if [ -f /var/run/reboot-required ]; then
  echo "REBOOT_REQUIRED=1"
else
  echo "REBOOT_REQUIRED=0"
fi
