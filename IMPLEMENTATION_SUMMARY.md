# USB Phone Camera Feature - Implementation Summary

## Overview
Added support for connecting and using an Android phone's camera via USB connection using ADB (Android Debug Bridge).

## Changes Made to main.py

### 1. **Added Imports**
- Added `import subprocess` for calling ADB commands to detect and manage USB devices

### 2. **New Methods Added**

#### `detect_usb_devices()`
- Detects Android devices connected via USB using ADB
- Returns a list of device IDs that are currently connected
- Handles ADB not being installed gracefully with logging

#### `refresh_usb_devices()`
- Callable from the UI to refresh the list of connected USB devices
- Updates the USB device selector dropdown
- Shows user feedback via message box about connected devices
- Provides helpful diagnostic information if no devices are found

#### `change_to_usb_camera(index)`
- Switches the camera feed to a selected USB-connected Android device
- Handles ADB port forwarding setup automatically
- Attempts to establish connection to camera stream via localhost with configurable port
- Includes comprehensive error handling with user-friendly messages
- Logs connection attempts and device information
- Falls back to default webcam if connection fails

### 3. **Updated Methods**

#### `__init__()` 
- Added USB device detection on startup
- Added tracking variables:
  - `self.usb_devices` - list of connected USB device IDs
  - `self.current_camera_type` - tracks whether using "webcam", "phone_ip", or "phone_usb"
  - `self.current_usb_device` - stores currently selected USB device
  - `self.usb_camera_port` - default port for USB camera streaming (8080)

#### `change_camera(index)`
- Updated to set `self.current_camera_type` appropriately
- Now distinguishes between different camera source types
- Changed UI label from "Camera Telefono" to "Camera Telefono (IP)" for clarity

#### `create_webcam_group()`
- Added new UI section for USB camera controls:
  - Label: "Fotocamera USB (Android)"
  - "Rileva dispositivi USB" (Detect USB Devices) button
  - Dropdown selector for available USB devices
  - Port input field for camera streaming port (default: 8080)
- Updated IP camera label for clarity

## UI Changes

### New Controls in Webcam Panel

1. **USB Detection Button**
   - Caption: "Rileva dispositivi USB"
   - Function: Refreshes and detects connected USB devices
   - Shows feedback message with count of devices found

2. **USB Device Selector**
   - Dropdown showing all connected Android devices
   - Automatically populated when devices are detected
   - Shows device ID (serial number)

3. **USB Port Input Field**
   - Sets the port for camera streaming
   - Default value: 8080
   - Allows customization if phone uses different port

## How It Works

### USB Connection Flow

1. User connects Android phone to PC via USB
2. User enables USB Debugging on phone
3. In the application:
   - Click "Rileva dispositivi USB" to detect connected devices
   - Select device from dropdown
   - Enter camera streaming port (if not default)
   - Click "Start Camera"

### Backend Process

1. App calls `adb devices` to list connected devices
2. When device selected, app establishes ADB port forwarding:
   ```
   adb -s <device_id> forward tcp:<port> tcp:<port>
   ```
3. Attempts to open video feed from `http://localhost:<port>/video`
4. If successful, displays camera feed in the UI
5. If fails, shows error message and reverts to default webcam

## Requirements

### System Requirements
- **ADB (Android Debug Bridge)** - Must be installed separately
  - Download from: https://developer.android.com/tools/releases/platform-tools
  - Must be added to system PATH

### Device Requirements
- Android phone with USB debugging capability
- USB cable (USB 2.0 or higher)
- Camera streaming capability (via scrcpy, IP Webcam, or similar)

### Python Dependencies
- All existing dependencies (no new packages needed)
- `subprocess` module (built-in Python)

## Error Handling

The implementation includes robust error handling for:

1. **ADB Not Installed**
   - Gracefully logs warning if ADB not found
   - Informs user via message box

2. **No Devices Connected**
   - Clears selector and shows informative message
   - Provides troubleshooting tips

3. **Connection Timeout**
   - Catches timeout errors
   - Reverts to default camera
   - Shows timeout-specific error message

4. **Camera Stream Unavailable**
   - Handles connection failures gracefully
   - Provides detailed error message with troubleshooting steps
   - Reverts to default webcam safely

5. **Port Forwarding Failures**
   - Handles subprocess errors
   - Provides user feedback

## Logging

- All USB device detection attempts are logged
- Connection events are logged for debugging
- Errors are logged with context information
- Uses existing logging system in `logs/faceapp_logging.log`

## Backward Compatibility

- All existing functionality preserved
- Regular webcam selection still works exactly as before
- IP camera option still available (with clarified label)
- No breaking changes to existing code

## Future Enhancements

Potential improvements for future versions:

1. Auto-detection of camera streaming apps on USB phone
2. Automatic ADB installation check
3. Support for multiple USB devices simultaneously
4. Bandwidth/quality adjustment for USB streams
5. Persistent device selection preferences
6. Integration with scrcpy for full device mirroring
7. Support for iOS devices (if using alternative streaming)

## Testing Checklist

- [ ] Verify subprocess import doesn't break existing functionality
- [ ] Test with no USB devices connected
- [ ] Test with single USB device connected and debugged
- [ ] Test with multiple USB devices
- [ ] Test port forwarding with different port numbers
- [ ] Test fallback to default camera on connection failure
- [ ] Verify logging of all USB operations
- [ ] Test with camera streaming disabled on phone
- [ ] Verify UI responsiveness during device detection
- [ ] Test switching between webcam, IP, and USB cameras

---

**Documentation:** See `USB_CAMERA_SETUP.md` for detailed setup instructions.
