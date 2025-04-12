# main.py - RECEIVER
from device_registry import DeviceRegistry
from virtual_buttons import VirtualButton
import network
import espnow
import time
import machine
import ubinascii
import crypto

r_version = "1.0.0"

time.sleep(1)
print(f">> Receiver version {r_version}")

VIRTUAL_BUTTON_GPIO = 10
PAIR_GPIO = 20
LED_PIN = 2

# === GPIO SETUP ===
PAIR_PIN = machine.Pin(PAIR_GPIO, machine.Pin.IN, machine.Pin.PULL_UP)  # Use GPIO21 instead of GPIO0
LED = machine.Pin(LED_PIN, machine.Pin.OUT)
button = VirtualButton(VIRTUAL_BUTTON_GPIO)

# === HELPER ===
def blink(times=1, speed=0.2):
    for _ in range(times):
        LED.on()
        time.sleep(speed)
        LED.off()
        time.sleep(speed)


# === NETWORK INIT ===
sta = network.WLAN(network.STA_IF)
sta.active(True)

e = espnow.ESPNow()
e.active(True)

broadcast_address = b'\xff\xff\xff\xff\xff\xff'
e.add_peer(broadcast_address)

registry = DeviceRegistry()

print("Receiver name:", registry.name)

# === REGISTRATION MODE CHECK ===
waiting_time = 2
print(f">> {str(waiting_time)} seconds to enable remotes pairing mode.")
time.sleep(waiting_time)  # Give user time to press PAIR button

pairing_mode = not PAIR_PIN.value()
if pairing_mode:
    print(">> PAIRING MODE ACTIVE")
    LED.on()
else:
    print(">> NORMAL BOOT ACTIVE")
    blink(2)

# initialise start_pairing ticks anyway.
start_pairing = time.ticks_ms()

# === MAIN LOOP ===
while True:
    try:
        mac, msg = e.irecv()
        if not msg:
            continue
        printable_mac = ubinascii.hexlify(mac).decode()
    except Exception as err:
        print(f"Error reading message...: {e}")
        print("TODO: handle this better. lets reboot, so sorry")
        machine.soft_reset()
        continue
    try:
        try:
            print(f"[{printable_mac}]: {msg}")
        except:
            print("error printing received message")
            pass

        if msg.startswith(b"PAIR:"):
            if not pairing_mode:
                print("[IGNORE] Received some pairing messages but not in pairing mode.")
                continue
            try:
                parts = msg.split(b":")
                remote_pubkey = parts[1]
                try:
                    remote_name = parts[2].decode()
                except:
                    remote_name = None
            except Exception as ex:
                print("Malformed PAIR message:", ex)
                continue

            added = registry.add_device(mac, remote_pubkey, remote_name)
            if added:
                print(f"Paired new remote: {remote_name}")
                blink(3, 0.1)
            else:
                print(f"Remote {printable_mac} already registered.")

            print("Notifying....")
            # Send back our info
            e.send(broadcast_address, b'RECEIVER PAIRING')
            try:
                e.add_peer(mac)
            except Exception as err:
                print(f"[{printable_mac}] peer already added.")

            time.sleep(1.5)
            reply = b"RECEIVER:" + registry.name.encode() + b":" + mac + b":" + b"MyFakeKey"
            try:
                e.send(mac, reply)
            except Exception as ex:
                print("Failed to respond to pairing:", ex)
            finally:
                print("pairing process is over.")
                pairing_mode = False
                print("Rebooting for normal boot-up process.")
                machine.soft_reset()

        if msg == b"HI":
            print(f"[{printable_mac}] >> Remote is saying hi")
            try:
                dev = registry.get_by_mac(mac)
                if not dev:
                    print(f"[{printable_mac}] Ignoring unknown remote.")
                else:
                    try:
                        e.add_peer(mac)
                        time.sleep(0.2)
                    except:
                        print("no registration done or might was done already")
                    try:
                        time.sleep(0.2)
                        e.send(broadcast_address, b"RECEIVER READY")
                        e.send(mac, b"RECEIVER READY")
                        print(f"[{printable_mac}] [broadcast] Waving back...")
                    except:
                        print("[CRITICAL]: no 'RECEIVER READY' could be sent as broadcast")
            except:
                print("Failed to add as peer after hello")

        if msg == b"BYE":
            print("Remote is saying bye")
            try:
                dev = registry.get_by_mac(mac)
                if not dev:
                    print(f"Ignoring unknown remote {printable_mac}.")
                else:
                    e.del_peer(mac)
            except:
                print("Failed to del peer after bye")
                pass

        if msg.startswith(b"TRIGGER"):
            dev = registry.get_by_mac(mac)
            name = dev["name"] if dev else "UNKNOWN"
            print(f"{name}: Trigger from {printable_mac}")

            if not dev:
                print(f"f[{printable_mac}] >> Unknown remote. Ignoring...")
                blink(1)
                continue

            # e.add_peer(mac)  # Ensure peer is registered

            nonce = crypto.generate_random_key(16)
            challenge = b"CHALLENGE " + nonce
            e.send(mac, challenge)
            print(f"[{printable_mac}] >> Sent challenge.")

            start = time.ticks_ms()
            while time.ticks_diff(time.ticks_ms(), start) < 1500:
                m, reply = e.irecv()
                if reply and m == mac:
                    decrypted = crypto.xor_encrypt(reply, bytes(dev["pubkey"]))
                    if decrypted == nonce:
                        print(f"[{printable_mac}]>> {name} authenticated successfully!")
                        e.del_peer(mac)

                        blink(2, 0.05)
                        LED.on()
                        button.push(200)
                        LED.off()
                    else:
                        print(f"[{printable_mac}] {name} failed auth !!!!!!")
                    break

    except Exception as err:
        print("Exception:", str(err))

    if pairing_mode and time.ticks_diff(time.ticks_ms(), start_pairing) > 60000:
        print("Pairing timeout.")
        pairing_mode = False
        LED.off()
