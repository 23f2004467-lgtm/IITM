# Fix Build Command - Remove install-deps

## Problem
`playwright install-deps chromium` tries to use `su` (root access) which fails in Render's environment.

## Solution
Remove `install-deps` from build command. Render's environment should have the necessary system libraries, or Playwright will work without them.

## Updated Build Command

In Render Dashboard:
1. Go to Settings
2. Find "Build Command"
3. Use this (without install-deps):
   ```
   pip install --upgrade pip && pip install -r requirements.txt && python -m playwright install chromium
   ```

## Alternative: Use Docker

If Playwright still doesn't work, switch to Docker deployment which gives full control.

## What I Changed

Updated `render.yaml` to remove `install-deps`:
```yaml
buildCommand: pip install --upgrade pip && pip install -r requirements.txt && python -m playwright install chromium
```

This should work because:
- Playwright browsers will be installed
- System dependencies may already be present in Render's environment
- Or Playwright will work without them for basic operations

