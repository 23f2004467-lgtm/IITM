# Fix Render Deployment - Python 3.13 Issue

## Problem
Render is using Python 3.13.4, which causes:
- `pydantic-core` tries to build from source (requires Rust)
- Build fails due to filesystem permissions
- `pandas` compatibility issues

## Solution Applied

### 1. Fixed runtime.txt
Changed from `python-3.11.9` to `3.11.9` (correct format)

### 2. Reverted pandas version
Changed back to `pandas==2.1.4` (compatible with Python 3.11, has pre-built wheels)

### 3. Created render.yaml
This explicitly tells Render to use Python 3.11

## Manual Fix in Render Dashboard

If `runtime.txt` still doesn't work, set Python version manually:

1. Go to your Render service dashboard
2. Click **Settings**
3. Find **"Python Version"** or **"Environment"** section
4. Set to: `3.11.9`
5. Save
6. Redeploy

## Alternative: Use Pre-built Wheels

If issues persist, we can pin all packages to versions with pre-built wheels:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
playwright==1.40.0
openai==1.3.0
aiohttp==3.9.1
pandas==2.1.4
numpy==1.26.2
python-multipart==0.0.6
PyPDF2==3.0.1
openpyxl==3.1.2
```

## Next Steps

1. Commit and push the fixes:
   ```bash
   git add runtime.txt requirements.txt render.yaml
   git commit -m "Fix: Force Python 3.11 and use compatible package versions"
   git push origin main
   ```

2. Render will auto-redeploy

3. If it still uses Python 3.13, manually set it in Render dashboard

