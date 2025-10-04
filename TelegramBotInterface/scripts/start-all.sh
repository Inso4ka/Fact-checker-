#!/usr/bin/env bash

set -e

echo "🚀 Starting Inngest and Mastra servers..."

trap 'kill 0' SIGINT SIGTERM EXIT

cd "$(dirname "$0")/.."

export NODE_ENV="${NODE_ENV:-development}"

echo "📦 Starting Inngest server on port 3000..."
npx inngest-cli dev -u http://localhost:5000/api/inngest --host 127.0.0.1 --port 3000 &
INNGEST_PID=$!

sleep 3

echo "🎯 Starting Mastra dev server on port 5000..."
npm run dev:mastra &
MASTRA_PID=$!

wait
