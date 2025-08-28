#!/bin/sh

# Wait for a service to be ready
wait_for() {
    echo "Testing $1..."
    until curl --output /dev/null --silent --head --fail "$1"; do
        echo "Waiting for $1..."
        sleep 1
    done
    echo "$1 is available"
}

wait_for $API_URL/health
wait_for $NOTIFICATION_URL/health
wait_for $SECURITY_URL/health
wait_for $DASHBOARD_URL/health

exec "$@"
