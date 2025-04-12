# main.py - REMOTE (auto-pairing support + no deepsleep)

import network
import espnow
import machine
import time
import ubinascii
import crypto
import ujson

broadcast_address = b'\xff\xff\xff\xff\xff\xff'

# === GPIO & LED SETUP ===
LED = machine.Pin(2, machine.Pin.OUT)
PAIR_BTN = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_UP)  # GPIO0


def blink(times=1, speed=0.2):
    for _ in range(times):
        LED.on()
        time.sleep(speed)
        LED.off()
        time.sleep(speed)


def led_on(duration=1):
    LED.on()
    time.sleep(duration)
    LED.off()


# === NETWORK INIT ===
sta = network.WLAN(network.STA_IF)
sta.active(True)

e = espnow.ESPNow()
e.active(True)
e.add_peer(b'\xff\xff\xff\xff\xff\xff')  # Broadcast

# === LOAD OR INIT CONFIG ===
try:
    with open("remote_info.json") as f:
        info = ujson.load(f)
except Exception as e:
    info = {
        "pubkey": list(crypto.generate_random_key(8)),
        "name": crypto.random_name(),
        "known_receivers": []
    }
    with open("remote_info.json", "w") as f:
        ujson.dump(info, f)

pubkey = bytes(info["pubkey"])
name = info["name"]
receivers = info.get("known_receivers", [])

if receivers:
    # === BOOT DELAY ===
    print("waiting 2 secs before booting up....")
    time.sleep(2)
else:
    time.sleep(1)
    print("No receivers registered, shall get into pairing mode then!")

# === PAIRING MODE ===
if not PAIR_BTN.value() or not receivers:
    print(">> PAIRING MODE ACTIVE")
    print(f">> Requesting pairing as: {name.encode()}")
    blink(3, 0.1)
    msg = b"PAIR:" + pubkey + b":" + name.encode()
    e.send(b'\xff' * 6, msg)
    print("Sent pairing request.")

    # Wait 5s for response
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 6000:
        mac, msg = e.irecv()
        if msg and msg.startswith(b"RECEIVER PAIRING"):
            print(f"Found a possible receiver: {mac}")
            e.add_peer(mac)
            time.sleep(1)
            break
        else:
            print(msg)
            print(mac)

    # Wait 5s for response
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 5000:
        mac, msg = e.irecv()
        print("heee")
        try:
            print(msg)
            print(mac)
        except Exception as e:
            print("petada")

        try:
            if msg and msg.startswith(b'RECEIVER:'):
                print("received some info from receiver exchange.")
                parts = msg.split(b":")
                print(parts)
                recv_name = parts[1].decode()
                recv_mac = list(mac)
                recv_key = list(parts[3])
                print(f"Registered receiver: {recv_name}")

                # Prevent duplicates
                existing = [r for r in info["known_receivers"] if r["mac"] == recv_mac]
                if not existing:
                    info["known_receivers"].append({
                        "name": recv_name,
                        "mac": recv_mac,
                        "pubkey": recv_key
                    })
                    with open("remote_info.json", "w") as f:
                        ujson.dump(info, f)
                    blink(2)
        except Exception as ex:
            print("Bad receiver response:", ex)

    print("Exiting pairing mode.")
    print("Better reboot me...")
    machine.soft_reset()

# === NORMAL MODE ===

blink(2)
print("Greeting receivers.")

if receivers:
    e.send(broadcast_address, b"HI")


start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), start) < 3000:
    host, msg = e.irecv()
    printable_mac = ubinascii.hexlify(host).decode()

    if msg and host:
        if msg.startswith(b"RECEIVER READY"):
            print(f"[{printable_mac}] Possible receiver waving back.")
            try:
                e.add_peer(host)
            except Exception as err:
                pass
            time.sleep(0.2)
            try:
                e.send(host, b"TRIGGER")
            except Exception as err:
                pass
        elif msg.startswith(b"CHALLENGE "):
            for receiver in receivers:
                try:
                    print(receiver)
                    mac = bytes(receiver["mac"])
                    rkey = bytes(receiver["pubkey"])
                    if mac != host:
                        print("MAC not matching in known receivers")
                        continue
                    # e.add_peer(mac)
                    print(f">> CHALLENGE Received from {receiver['name']} ({ubinascii.hexlify(mac).decode()})")
                    challenge = msg[len("CHALLENGE "):]
                    reply = crypto.xor_encrypt(challenge, pubkey)
                    e.send(mac, reply)
                    led_on(1)
                    break
                except Exception as ex:
                    print(f"Error with {receiver.get('name')}: {ex}")
        else:
            print(f"[{printable_mac}] {msg}")

print("Done.")
while True:
    # Add some sleep to avoid some heat in case power keeps going...
    time.sleep(10)
    pass
