#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Machine Aesthetics Application${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if backend directory exists
if [ ! -d "./backend" ]; then
  echo -e "${RED}Error: backend directory not found.${NC}"
  exit 1
fi

# Check if Python and Node.js are installed
if ! command -v python &> /dev/null; then
  echo -e "${RED}Error: Python is not installed. Please install Python 3.${NC}"
  exit 1
fi

if ! command -v node &> /dev/null; then
  echo -e "${RED}Error: Node.js is not installed. Please install Node.js.${NC}"
  exit 1
fi

# Make sure the directories exist for data output
mkdir -p public/data/output
mkdir -p public/emotions

# Check if essential files exist, if not, create minimal versions
if [ ! -f "./public/emotions/emotion_curves.json" ]; then
  echo -e "${BLUE}Creating default emotion_curves.json file${NC}"
  # Copy from backend if it exists, otherwise create minimal version
  if [ -f "./backend/output/emotion_curves.json" ]; then
    cp ./backend/output/emotion_curves.json ./public/emotions/
  fi
fi

# Create default files if they don't exist
if [ ! -f "./public/data/output/top2_emotion_summary.csv" ]; then
  echo -e "${BLUE}Creating default top2_emotion_summary.csv file${NC}"
  echo "emotion,valence,arousal,dominance,duration" > ./public/data/output/top2_emotion_summary.csv
  echo "serene,0.0,0.0,0.0,11.6" >> ./public/data/output/top2_emotion_summary.csv
  echo "surprised,0.0,0.5,0.2,3.3" >> ./public/data/output/top2_emotion_summary.csv
fi

if [ ! -f "./public/data/output/arousal_100.csv" ]; then
  echo -e "${BLUE}Creating default arousal_100.csv file${NC}"
  echo "arousal" > ./public/data/output/arousal_100.csv
  for i in {1..100}; do
    echo "$((RANDOM % 100)).$((RANDOM % 100))" >> ./public/data/output/arousal_100.csv
  done
fi

# Start the Flask backend server in the background
echo -e "${GREEN}Starting Flask backend server...${NC}"
cd backend || exit
python app.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to initialize
sleep 2

# Check if backend started successfully
if kill -0 $BACKEND_PID 2>/dev/null; then
  echo -e "${GREEN}Backend server started successfully (PID: $BACKEND_PID)${NC}"
else
  echo -e "${RED}Failed to start backend server${NC}"
  exit 1
fi

# Start the React frontend
echo -e "${GREEN}Starting React frontend...${NC}"
npm start

# When frontend is stopped, also stop the backend
echo -e "${BLUE}Stopping backend server (PID: $BACKEND_PID)...${NC}"
kill $BACKEND_PID
echo -e "${GREEN}Done.${NC}" 