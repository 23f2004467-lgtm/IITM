# Deployment Guide

## Local Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Run server:**
   ```bash
   python main.py
   # Or: uvicorn main:app --host 0.0.0.0 --port 8000
   ```

4. **Test endpoint:**
   ```bash
   curl -X POST http://localhost:8000/quiz \
     -H "Content-Type: application/json" \
     -d '{
       "email": "your-email@example.com",
       "secret": "your-secret",
       "url": "https://tds-llm-analysis.s-anand.net/demo"
     }'
   ```

## Deployment Options

### Option 1: Railway
1. Create account at [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Add environment variables:
   - `QUIZ_SECRET`
   - `QUIZ_EMAIL`
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL` (optional, defaults to gpt-4o)
   - `PORT` (optional, Railway sets this automatically)
4. Deploy

### Option 2: Render
1. Create account at [render.com](https://render.com)
2. New Web Service → Connect GitHub repo
3. Build command: `pip install -r requirements.txt && playwright install chromium`
4. Start command: `python main.py`
5. Add environment variables (same as Railway)
6. Deploy

### Option 3: Heroku
1. Create account at [heroku.com](https://heroku.com)
2. Install Heroku CLI
3. Create app: `heroku create your-app-name`
4. Add buildpack: `heroku buildpacks:add heroku/python`
5. Add buildpack for Playwright: `heroku buildpacks:add jontewks/puppeteer`
6. Set environment variables: `heroku config:set QUIZ_SECRET=... QUIZ_EMAIL=... OPENAI_API_KEY=...`
7. Deploy: `git push heroku main`

### Option 4: DigitalOcean App Platform
1. Create account at [digitalocean.com](https://digitalocean.com)
2. Create App → Connect GitHub
3. Configure build and run commands
4. Add environment variables
5. Deploy

### Option 5: AWS/GCP/Azure
- Use containerized deployment (Docker)
- Or use serverless (AWS Lambda, Google Cloud Functions, Azure Functions)
- Note: Playwright may require special setup for serverless

## Important Notes

1. **HTTPS Required**: The endpoint must be accessible via HTTPS
2. **Playwright**: Ensure Playwright browsers are installed in deployment environment
3. **Environment Variables**: Never commit `.env` file
4. **Timeout**: The quiz solving must complete within 3 minutes
5. **API Key**: Keep your OpenAI API key secure

## Docker Deployment (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t llm-quiz-solver .
docker run -p 8000:8000 --env-file .env llm-quiz-solver
```

