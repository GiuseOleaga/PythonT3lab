# Quick Start: USB Phone Camera

## 3-Minute Setup

### Step 1: Install ADB (5 minutes, one-time)
1. Download Android SDK Platform Tools: https://developer.android.com/tools/releases/platform-tools
2. Extract the ZIP file
3. Copy the folder path
4. Add to Windows PATH (Search "Environment Variables" → New → Paste path → OK)
5. Restart Command Prompt to verify: Type `adb --version`

### Step 2: Enable USB Debug on Phone (2 minutes)
1. Settings → About Phone → Tap "Build Number" 7 times
2. Settings → Developer Options → Enable "USB Debugging"
3. Connect phone to PC with USB cable
4. Tap "Allow" when asked to trust the computer

### Step 3: Use in Application
1. In app, go to "Fotocamera USB (Android)" section
2. Click "Rileva dispositivi USB" button
3. Select your phone from the dropdown
4. Click "Start Camera"

✅ Done! Your phone camera should now appear in the app.

## If It Doesn't Work

| Problem | Solution |
|---------|----------|
| "No devices found" | 1. Check USB cable is properly connected<br>2. Enable USB Debugging on phone<br>3. Restart ADB: Open Command Prompt, type `adb kill-server` |
| "Cannot connect to stream" | 1. Your phone might not have camera streaming enabled<br>2. Try the "Camera Telefono (IP)" option instead<br>3. Use an IP Webcam app from Play Store |
| "ADB not found" | 1. Check Windows PATH: Search "Environment Variables"<br>2. Verify ADB folder is added to PATH<br>3. Restart Command Prompt and try again |

## Alternative: IP Webcam (Easier, No ADB Needed)

If USB camera doesn't work:
1. Install "IP Webcam" from Google Play Store
2. Open app and tap "Start Server"
3. Copy the IP address shown
4. In app, select "Camera Telefono (IP)"
5. Paste the IP address in the URL field
6. Click "Start Camera"

## Common Questions

**Q: Do I need ADB?**  
A: Only for USB connection. IP Webcam method doesn't need it.

**Q: Does it work with iPhone?**  
A: Not currently (this implementation is for Android). Use an IP streaming app instead.

**Q: Can I use both USB and webcam at the same time?**  
A: No, but you can quickly switch between them in the dropdown.

**Q: What if my phone doesn't stream camera?**  
A: You'll need a camera streaming app. IP Webcam is the easiest option.

**Q: Is USB faster than WiFi?**  
A: Usually yes, but depends on your phone's camera streaming capability.

---

**Need help?** See `USB_CAMERA_SETUP.md` for detailed instructions.
