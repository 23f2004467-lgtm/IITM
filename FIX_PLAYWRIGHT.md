# Fix Playwright Installation Issue

## Problem
Playwright browsers are not installed in Render environment, causing error:
```
Executable doesn't exist at /opt/render/.cache/ms-playwright/chromium-1140/chrome-linux/chrome
```

## Solution
Updated `render.yaml` build command to properly install Playwright browsers:

```yaml
buildCommand: pip install --upgrade pip && pip install -r requirements.txt && python -m playwright install chromium && python -m playwright install-deps chromium
```

This ensures:
1. Install Python packages
2. Install Playwright browsers
3. Install system dependencies for Chromium

## Next Steps

1. **Commit and push the fix:**
   ```bash
   git add render.yaml
   git commit -m "Fix: Install Playwright browsers and dependencies in build"
   git push origin main
   ```

2. **Render will auto-redeploy** with the fix

3. **Test again** after deployment completes

## Alternative: Manual Fix in Render Dashboard

If render.yaml doesn't work, update build command in Render dashboard:

1. Go to Render dashboard
2. Click on your service
3. Go to Settings
4. Find "Build Command"
5. Update to:
   ```
   pip install --upgrade pip && pip install -r requirements.txt && python -m playwright install chromium && python -m playwright install-deps chromium
   ```
6. Save and redeploy

## Test After Fix

Once redeployed, test again:
```bash
./test_demo_simple.sh
```

The error should be resolved and quiz solving should work!

