import audiocore
import audiobusio
import board
import busio
import sdcardio
import storage
import os
import json
from adafruit_pn532.i2c import PN532_I2C
import audiomixer
import time


spi = busio.SPI(board.GP10, board.GP11, board.GP12)

sdcard = sdcardio.SDCard(spi, board.GP13)


while True:
    try:
        # SD card setup
        vfs = storage.VfsFat(sdcard)
        storage.mount(vfs, "/sd")
        print("SD card mounted!")
        break
    except Exception as e:
        print("Retrying - SD card failed:", e)
        time.sleep(2)

test_volume = 0.6


# I2S audio setup
audio = audiobusio.I2SOut(board.GP18, board.GP19, board.GP20)


mixer = audiomixer.Mixer(voice_count=1, sample_rate=11025, channel_count=1, bits_per_sample=16, samples_signed=True)


while True:
    try:
        # Load tag mappings from SD card
        with open("/sd/tags.json", "r") as f:
            TAG_MAP = json.load(f)
            test_volume = TAG_MAP.get("volume", 6) / 10.0
            mixer.voice[0].level = test_volume  # this is where volume is set
            print("Volume set to", TAG_MAP.get("volume", 6))
        print("Loaded", len(TAG_MAP), "tags")
        break
    except Exception as e:
        print("Retrying - loading SD card data: ", e)
        time.sleep(2)


# NFC setup

i2c = busio.I2C(board.GP5, board.GP4, frequency=50000)

while True:
    try:
        pn532 = PN532_I2C(i2c, debug=False)
        pn532.SAM_configuration()

        print("Waiting for NFC tag...")
        break
    except Exception as e:
        print("Retrying - loading NFC: ", e)
        time.sleep(2)

removed_count = 0

while True:
    time.sleep(0.2)
    pn532.SAM_configuration()
    uid = pn532.read_passive_target(timeout=0.5)
    print("reading...")
    if uid is not None:
        # uid_str = "".join([hex(i) for i in uid])
        uid_str = "".join([f"{i:02x}" for i in uid])
        print("Tag UID:", uid_str)
        if uid_str in TAG_MAP:
            filename = "/sd/" + TAG_MAP[uid_str]
            print("Playing:", filename)
            # wave = audiocore.WaveFile(open(filename, "rb"))

            wave = audiocore.WaveFile(open(filename, "rb"))
            audio.play(mixer)
            mixer.voice[0].play(wave)
            # audio.play(wave)
            # audio.volume = test_volume
            while audio.playing:
                time.sleep(0.2)
                pn532.SAM_configuration()
                still_there = pn532.read_passive_target(timeout=0.3)
                if still_there is None:
                    removed_count += 1
                    print("removed_count:", removed_count)
                    if removed_count >= 3:
                        audio.stop()
                        print("Tag removed, stopped!")
                        removed_count = 0
                        break
                else:
                    removed_count = 0
        else:
            print("Unknown tag!")

print("program exited")
