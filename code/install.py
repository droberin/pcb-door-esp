#!/usr/bin/env python3
import os
import sys
import glob
import subprocess
import argparse

def find_serial_ports():
    return glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")


def detect_install_type(port):
    try:
        result = subprocess.run(["mpremote", "connect", port, "fs", "ls"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to list files on device: {result.stderr}")
            return None

        device_files = result.stdout.split()
        if "authorized_devices.json" in device_files or "device_registry.py" in device_files:
            return "receiver"
        elif "remote_info.json" in device_files:
            return "remote"
        else:
            print("No device type detected by content.")
        return None

    except Exception as e:
        print(f"Error detecting install type: {e}")
        return None


def prompt_port():
    ports = find_serial_ports()
    if not ports:
        print("No serial ports found. Connect your device and try again.")
        return input("Enter port manually (e.g., /dev/ttyUSB0, COM3, etc.): ")
    print("Available serial ports:")
    for i, port in enumerate(ports):
        print(f"  {i + 1}. {port}")
    choice = input("Select a port (number) or enter manually: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(ports):
        return ports[int(choice) - 1]
    return choice


def upload_files(port, install_type):
    remote_files = ["remote_info.json"]
    receiver_files = ["device_registry.py",  "virtual_buttons.py", "authorized_devices.json"]

    # Rename appropriate file to main.py
    if install_type == "remote":
        source = "remote.py"
    elif install_type == "receiver":
        source = "receiver.py"
    else:
        print("Unknown install type.")
        return

    if not os.path.exists(source):
        print(f"❌ Missing source file: {source}")
        return

    # Copy to main.py
    print(f"Generating main.py from {source}")
    with open(source, "r") as src, open("main.py", "w") as dst:
        dst.write(src.read())

    upload_list = ["main.py", "crypto.py"]
    if install_type == "remote":
        upload_list += [f for f in remote_files if os.path.isfile(f)]
    elif install_type == "receiver":
        upload_list += [f for f in receiver_files if os.path.isfile(f)]

    for file in upload_list:
        print(f"Uploading {file}...")
        result = subprocess.run(["mpremote", "connect", port, "fs", "cp", file, ":"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to upload {file}:\n{result.stderr}")
        else:
            print(f"✅ Uploaded {file}")

    os.remove("main.py")  # Clean up after ourselves


def main():
    parser = argparse.ArgumentParser(description="Install or update MicroPython files to a device.")
    parser.add_argument("--port", help="Serial port of the device (e.g., /dev/ttyUSB0)")
    parser.add_argument("--type", choices=["remote", "receiver"], help="Type of install: remote or receiver")
    args = parser.parse_args()

    port = args.port or prompt_port()
    if not os.path.exists(port):
        print(f"Port {port} does not exist.")
        sys.exit(1)

    detected_type = detect_install_type(port)
    if args.type:
        if detected_type and detected_type != args.type:
            print(f"❌ Mismatch: you requested '{args.type}' but files suggest '{detected_type}'. Aborting.")
            sys.exit(1)
        install_type = args.type
    else:
        if not detected_type:
            print("❌ Couldn't detect install type automatically. Use --type.")
            if "y" != str(input("Wanna set it up as a remote? [N/y]")).lower().strip():
                print("Process aborted")
                sys.exit(1)
            else:
                install_type = "remote"
        else:
            print(f"✅ Auto-detected install type: {detected_type}")
            install_type = detected_type

    upload_files(port, install_type)


if __name__ == "__main__":
    main()
