#!/usr/bin/env bash
# ============================================================================
# run_local_checks.sh
# One-click self-check script for the AgentScope project
# ============================================================================
set -eo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

echo "=========================================================="
echo "🚀 Starting AgentScope Project Local Self-Checks..."
echo "=========================================================="

# 1. Python Syntax & Compilation Check
echo -e "\n🔍 [1/5] Checking Python syntax..."
python3 -m compileall backend simulator real_agent_sdk || {
  echo "❌ Python compilation failed!"
  exit 1
}
echo "✅ Python syntax check passed."

# Ensure temp directory exists
mkdir -p tmp

# 2. Generate offline mock dataset
echo -e "\n📦 [2/5] Generating offline mock dataset with seed 42..."
python3 simulator/main.py --mode offline --count 10 --seed 42 --output tmp/mixed_seed_42.jsonl || {
  echo "❌ Simulator data generation failed!"
  exit 1
}
echo "✅ Mock data generated: tmp/mixed_seed_42.jsonl"

# 3. Run simulator self-check
echo -e "\n🛡️ [3/5] Running simulator self-checks..."
cd simulator
python3 self_check.py --dir ../tmp || {
  echo "❌ Simulator self-check failed!"
  exit 1
}
cd ..
echo "✅ Simulator self-check passed."

# 4. Optional Maven Build check
echo -e "\n☕ [4/5] Checking Maven environment..."
if command -v mvn &> /dev/null; then
  echo "Found maven. Building Spark Batch & Streaming projects..."
  
  echo "Building spark-batch..."
  cd spark-batch
  mvn -q -DskipTests clean package || {
    echo "❌ spark-batch build failed!"
    exit 1
  }
  cd ..
  
  echo "Building spark-streaming..."
  cd spark-streaming
  mvn -q -DskipTests clean package || {
    echo "❌ spark-streaming build failed!"
    exit 1
  }
  cd ..
  echo "✅ Maven builds completed successfully."
else
  echo "⚠️ Maven (mvn) command not found. Skipping Spark job compilation checks."
fi

# 5. Optional NPM build check
echo -e "\n🌐 [5/5] Checking Node/NPM environment..."
if command -v npm &> /dev/null; then
  echo "Found npm. Building frontend project..."
  cd frontend
  npm install --no-audit --no-fund &> /dev/null || echo "npm install warning, trying build..."
  npm run build || {
    echo "❌ Frontend build failed!"
    exit 1
  }
  cd ..
  echo "✅ Frontend build completed successfully."
else
  echo "⚠️ NPM (npm) command not found. Skipping frontend compilation check."
fi

echo -e "\n=========================================================="
echo "🎉 All local checks completed successfully!"
echo "=========================================================="
