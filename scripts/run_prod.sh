#!/bin/bash

# Start the Telegram Bot in the background
echo "🤖 Starting Telegram Bot..."
python3 -m src.utils.telegram_bot &

# Start the Streamlit Dashboard in the foreground
echo "🚀 Starting Streamlit Dashboard..."
streamlit run src.utils.dashboard --server.port $PORT --server.address 0.0.0.0
