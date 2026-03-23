#!/bin/sh
set -e

case "$ROLE" in
    producer)  exec python -m taskqueue.producer ;;
    worker)    exec python -m taskqueue.worker ;;
    reaper)    exec python -m taskqueue.reaper ;;
    cleanup)   exec python -m taskqueue.cleanup ;;
    *)         echo "Unknown ROLE: $ROLE" && exit 1 ;;
esac
