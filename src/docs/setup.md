# Setup Guide

This guide walks you through setting up the HRMS Chatbot for local deployment.

## Fully Local Deployment
The HRMS Chatbot is designed to run entirely on your local network, with no internet dependency except for SMTP (used for password reset emails). This makes it ideal for secure company LAN environments.

## Prerequisites
- Python 3.8+
- PostgreSQL 13+
- Ollama (installed manually)
- Git
- SMTP server (for password resets and email verification)

## Installation Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/HRMS-Chatbot.git
   cd HRMS-Chatbot
   ```
2. **Set Up a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Install Ollama**:
   - Download and install Ollama from [ollama.ai](https://ollama.ai).
   - Pull a model: `ollama pull llama3`.
   - Ensure Ollama runs locally: `ollama run llama3`.
4. **Configure PostgreSQL**:
   - Create a database: `createdb hrms_chatbot`.
   - Create a `.env` file based on `.env.example`:
     ```
     DATABASE_URL=postgresql://user:password@localhost:5432/hrms_chatbot
     SMTP_HOST=smtp.yourserver.com
     SMTP_PORT=587
     SMTP_USER=your-email@yourserver.com
     SMTP_PASSWORD=your-password
     ```
5. **Populate the Knowledge Base**:
   ```bash
   python src/backend/scripts/populate_database.py
   ```
6. **Run the Application**:
   ```bash
   python src/backend/app.py
   ```
7. **Access the Chatbot**:
   - Open `http://localhost:5000` in your browser.

## Troubleshooting
- **Ollama Not Responding**: Ensure Ollama is running (`ollama run llama3`).
- **SMTP Issues**: Verify SMTP settings; if unavailable, password resets will fail.
