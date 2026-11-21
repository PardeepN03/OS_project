# OS Resource Monitoring & Alert System — Alert Fix

## Improvements
- Immediate threshold re-check when a threshold value is edited.
- Added **Check thresholds now** button for manual verification.
- Alert log reports the resource, measured percentage and configured threshold.
- The existing 60-second cooldown prevents repeated warnings for the same resource.
- Retains the colorful dashboard and optimized refresh intervals.

## Run on Windows
```bash
pip install -r requirements.txt
python app.py
```

## Demonstrating alerts
1. Run the application and wait for the first metric sample.
2. Set CPU threshold below the displayed CPU usage (for example, 1%).
3. Set memory and disk thresholds below their displayed values if you want to demonstrate multiple warnings.
4. Press **Check thresholds now**.
5. Read the warning entries in Alert Log.
6. Restore normal thresholds afterwards.

If a resource has already generated a warning in the last 60 seconds, the cooldown prevents a duplicate warning. Wait 60 seconds before testing that same resource again, or restart the app for a clean demonstration.
