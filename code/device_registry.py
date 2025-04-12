import ujson
import os


class DeviceRegistry:
    def __init__(self, path="authorized_devices.json", receiver_name="Receiver-001"):
        self.path = path
        self.receiver_name = receiver_name
        self.devices = []
        self._ensure_file()
        self._load()

    def _ensure_file(self):
        if self.path not in os.listdir():
            with open(self.path, "w") as f:
                ujson.dump({"receiver": self.receiver_name, "devices": []}, f)

    def _load(self):
        with open(self.path) as f:
            data = ujson.load(f)
            self.name = data.get("receiver", "UnknownReceiver")
            self.devices = data.get("devices", [])

    def _save(self):
        with open(self.path, "w") as f:
            ujson.dump({"receiver": self.name, "devices": self.devices}, f)

    def get_by_mac(self, mac):
        for dev in self.devices:
            if dev["mac"] == list(mac):
                return dev
        return None

    def add_device(self, mac, pubkey, name=None, device_id=None):
        mac_list = list(mac)
        if self.get_by_mac(mac):
            return False
        if not name:
            from crypto import random_name
            name = random_name()
        entry = {
            "mac": mac_list,
            "pubkey": list(pubkey),
            "name": name,
            "id": device_id or name.lower()
        }
        self.devices.append(entry)
        self._save()
        return True

    def list_devices(self):
        return self.devices

    def remove_by_mac(self, mac):
        mac_list = list(mac)
        before = len(self.devices)
        self.devices = [d for d in self.devices if d["mac"] != mac_list]
        after = len(self.devices)
        removed = before - after
        if removed > 0:
            print(f"🗑️ Removed {removed} device(s) with MAC {mac_list}")
            self._save()
        else:
            print(f"⚠️ No device found with MAC {mac_list}")

    def remove_by_name(self, name):
        before = len(self.devices)
        self.devices = [d for d in self.devices if d.get("name", "").lower() != name.lower()]
        after = len(self.devices)
        removed = before - after
        if removed > 0:
            print(f"🗑️ Removed {removed} device(s) with name '{name}'")
            self._save()
        else:
            print(f"⚠️ No device found with name '{name}'")
