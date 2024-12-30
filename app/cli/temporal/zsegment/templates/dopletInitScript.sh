#!/bin/bash

# Exit on any error
# set -e

echo "Installing Connector"
curl -O <<debUrl>>
sudo dpkg -i --force-all connector.deb
rm ./connector.deb

# File path for UFW default configuration
UFW_CONFIG="/etc/default/ufw"

# Disable IPv6 in the configuration file
echo "Disabling IPv6 in UFW..."
sudo sed -i 's/^IPV6=.*/IPV6=no/' "$UFW_CONFIG"

# Restart UFW to apply the changes
echo "Restarting UFW..."
sudo ufw disable
sudo ufw --force enable

# Add a rule to allow SSH (port 22) for IPv4
echo "Allowing traffic on port 22 for SSH..."
sudo ufw allow 22