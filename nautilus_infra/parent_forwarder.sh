#!/bin/bash
# Kill any existing forwarders
pkill -f "VSOCK-LISTEN:9092"

echo "Starting parent forwarder script..."

# Start Sui CLI proxy service
echo "Starting Sui CLI proxy service on port 9999..."
python3 sui_proxy.py &
SUI_PROXY_PID=$!
echo "Sui proxy started with PID: $SUI_PROXY_PID"

# Forward VSOCK port 9999 to local Sui proxy
echo "Setting up VSOCK forwarding for Sui proxy..."
/usr/local/bin/socat VSOCK-LISTEN:9999,fork TCP:127.0.0.1:9999 &
SUI_VSOCK_PID=$!
echo "Sui VSOCK forwarder started with PID: $SUI_VSOCK_PID"

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