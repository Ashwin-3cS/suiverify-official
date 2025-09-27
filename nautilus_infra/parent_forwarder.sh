#!/bin/bash
# Kill any existing forwarders
pkill -f "VSOCK-LISTEN:9092"

echo "Starting parent forwarders..."

# Forward VSOCK port 9092 to the IP (static - matching secrets.json)
echo "Testing connection to IP first..."
timeout 5 nc -z #ip will come here
if [ $? -eq 0 ]; then
    echo "IP is reachable, starting forwarder..."
    /usr/local/bin/socat VSOCK-LISTEN:9092,fork TCP: & # TCP: ip will come here
    echo "Parent forwarder started for ip on VSOCK port 9092"
else
    echo "WARNING: Cannot reach ip"
fi

echo "Parent forwarders setup complete"