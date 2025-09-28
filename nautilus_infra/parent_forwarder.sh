#!/bin/bash
# Kill any existing forwarders
pkill -f "VSOCK-LISTEN:9092"

echo "Starting parent forwarders..."

# Forward VSOCK port 9092 to the IP (static - matching secrets.json)
echo "Testing connection to IP first..."
timeout 5 nc -z 3.9.67.15 9092
if [ $? -eq 0 ]; then
    echo "IP is reachable, starting forwarder..."
    /usr/local/bin/socat VSOCK-LISTEN:9092,fork TCP:3.9.67.15:9092 &
    echo "Parent forwarder started for 3.9.67.15 on VSOCK port 9092"
else
    echo "WARNING: Cannot reach 3.9.67.15"
fi

echo "Parent forwarders setup complete"