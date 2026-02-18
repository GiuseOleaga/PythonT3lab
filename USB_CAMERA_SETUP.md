# USB Phone Camera Setup Guide

This guide explains how to use your Android phone's camera as a USB-connected camera in the application.

## Requirements

1. **Android Phone** with USB Debug enabled
2. **Android Debug Bridge (ADB)** installed on your PC
3. **USB Cable** to connect phone to PC
4. **Camera Streaming App** on your Android phone (optional, for non-ADB methods)

## Step 1: Install ADB (Android Debug Bridge)

### Option A: Install Android SDK Platform Tools (Recommended)

1. Download Android SDK Platform Tools from: https://developer.android.com/tools/releases/platform-tools
2. Extract the ZIP file to a folder (e.g., `C:\android-platform-tools`)
3. Add the folder to your system PATH:
   - Open System Properties → Environment Variables
   - Click "New" under System Variables
   - Variable name: `PATH`
   - Variable value: `C:\android-platform-tools` (or your extraction path)
4. Verify installation:
   - Open Command Prompt or PowerShell
   - Type: `adb --version`
   - You should see the ADB version

### Option B: Using Python ADB Package

Install via pip (alternative to Option A):

```bash
pip install adb-shell
```

## Step 2: Enable USB Debug on Your Android Phone

1. **Open Developer Options:**
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times until you see "You are now a developer"
   
2. **Enable USB Debugging:**
   - Go to Settings → Developer Options
   - Enable "USB Debugging"
   - Select "File Transfer" or "Charge Only" mode when connecting (USB file transfer options may vary)

3. **Trust the Computer:**
   - Connect your phone via USB
   - A prompt will appear on the phone asking to trust the computer
   - Tap "Allow" or "Trust"

## Step 3: Set Up Camera Streaming

The USB camera support uses ADB port forwarding. Your phone needs to run a camera streaming service. Here are some options:

### Option A: Using scrcpy + Camera Streaming
If you want to use scrcpy (Android screen mirroring tool), it can also handle camera streaming:
- Install scrcpy from: https://github.com/Genymobile/scrcpy
- Launch scrcpy to start screen mirroring

### Option B: Using IP Webcam (WiFi Alternative)
If USB streaming is complex, you can use IP Webcam app as an alternative:
1. Install "IP Webcam" from Google Play Store
2. Start the app and note the IP address shown
3. Use "Camera Telefono (IP)" option with the IP address

### Option C: Custom Camera Streaming App
If your phone has a camera streaming capability via ADB, the application will forward the connection automatically.

## Step 4: Use USB Camera in the Application

1. **Connect your Android phone via USB** to your PC
2. **Enable USB Debugging** on your phone (if not already done)
3. **In the Application UI:**
   - Look for "Fotocamera USB (Android)" section in the Webcam settings
   - Click "Rileva dispositivi USB" (Detect USB Devices) button
   - Select your device from the dropdown list
   - (Optional) Change the port number if needed (default: 8080)
   - Click "Start Camera" to begin

## Troubleshooting

### ADB command not found
- Ensure Android SDK Platform Tools are installed
- Verify PATH environment variable is set correctly
- Restart Command Prompt/PowerShell after adding to PATH
- Try the full path: `C:\path\to\adb\adb devices`

### Device not detected
- Ensure phone is connected via USB
- Enable USB Debugging in Developer Options
- Trust the computer when prompted on the phone
- Try: `adb devices` in Command Prompt to manually check
- Use a different USB port or cable if needed

### Cannot connect to camera stream
- Ensure camera streaming is running on your phone
- Check that the port number is correct (usually 8080)
- Verify ADB port forwarding: `adb forward tcp:8080 tcp:8080`
- Check firewall settings allow local connections

### Offline device error
- Disconnect and reconnect the USB cable
- Restart ADB: `adb kill-server` then `adb devices`
- Restart your phone
- Re-enable USB Debugging

## Advanced: Manual ADB Commands

If you need to manually manage ADB forwarding:

```bash
# List connected devices
adb devices

# Connect to specific device by serial
adb -s <device_serial> forward tcp:8080 tcp:8080

# Forward multiple ports
adb -s <device_serial> forward tcp:5037 tcp:5037

# Clear all forwardings
adb forward --remove-all

# Test connection to localhost:8080
curl http://localhost:8080/video
```

## Switching Between Cameras

- **Regular Webcam:** Select from the dropdown in "Webcam" section
- **IP Phone Camera:** Select "Camera Telefono (IP)" and enter the URL
- **USB Phone Camera:** Click "Rileva dispositivi USB" and select your device

## Performance Notes

- USB connection may provide more stable streaming than WiFi
- USB camera performance depends on your phone's camera streaming capability
- Reduce frame rate or resolution if experiencing lag
- USB 2.0 can handle most camera streams; USB 3.0+ recommended for HD

## Additional Resources

- ADB Documentation: https://developer.android.com/tools/adb
- scrcpy GitHub: https://github.com/Genymobile/scrcpy
- Android Device Bridge: https://developer.android.com/studio/command-line/adb

---

**Note:** If you encounter persistent issues with USB camera streaming, the IP Webcam option provides a reliable alternative using WiFi instead of USB.
