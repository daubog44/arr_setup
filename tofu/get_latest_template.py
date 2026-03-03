#!/usr/bin/env python3
import urllib.request
import re
import json
import sys


def get_latest_debian13_template():
    base_url = "http://download.proxmox.com/images/system/"
    try:
        req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")

        # Proxmox standard naming for debian 13 LXC templates
        pattern = r'href="(debian-13-standard_[0-9\.\-]+_amd64\.tar\.zst)"'
        matches = re.findall(pattern, html)

        if not matches:
            return None

        # Parse version numbers to find the highest one
        def parse_version(filename):
            match = re.search(r"standard_([0-9\.\-]+)_amd64", filename)
            if not match:
                return (0, 0, 0)
            vs = match.group(1).replace("-", ".").split(".")
            return tuple(int(x) if x.isdigit() else 0 for x in vs)

        latest_file = max(matches, key=parse_version)
        return f"{base_url}{latest_file}"

    except Exception as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    # The external data source expects empty JSON on stdin or args
    # It must output valid JSON
    latest_url = get_latest_debian13_template()
    if latest_url:
        # print("find!")
        print(json.dumps({"url": latest_url}))
    else:
        # Fallback to the latest known good version
        print(
            json.dumps(
                {
                    "url": "http://download.proxmox.com/images/system/debian-13-standard_13.1-2_amd64.tar.zst"
                }
            )
        )
