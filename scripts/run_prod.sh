#!/bin/bash

# Ensure PORT is set (default to 7860 for Hugging Face)
export PORT=${PORT:-7860}

# Start the Telegram Bot in the background
echo "🤖 Starting Telegram Bot..."
python3 -m src.utils.telegram_bot &

# Start the AI Worker in the background
echo "🧠 Starting AI Worker (Drafting/Sending)..."
python3 -m src.agent.worker &

# Start the Streamlit Dashboard in the foreground
echo "🚀 Starting Streamlit Dashboard on port $PORT..."
streamlit run src.utils.dashboard --server.port $PORT --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
