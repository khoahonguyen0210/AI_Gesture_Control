# Wokwi ESP32 demo

This folder runs the device code from [`firmware/src/`](../src/) on a simulated ESP32 board with a small OLED screen and three LEDs. A simulated board cannot work as a USB mouse for Windows, so it shows each action on its screen instead. The [gesture table](../../README.md#key-features) in the main README lists what each gesture does on the board.

## The board

| Part | Meaning |
|---|---|
| Top line | The mode (`LIVE`, `DEMO`, or `WAIT`) and the gesture name, such as `POINT`, `DRAG`, or `NO HAND` |
| Second line | `ok` is the number of good messages, `bad` the number of rejected messages, and `wd` the number of times the timeout released the buttons |
| Box with a dot | The computer screen. The dot is the cursor, and it is filled while the left button is down |
| `L` and `R` boxes | The left and right buttons. Each is filled while pressed |
| `S` number | The total scroll |
| Green, blue, and yellow LEDs | Left button, right button, and messages arriving |

If no app is connected for 5 seconds, the board plays a built-in demo. The demo also sends random bytes, a message with a broken CRC (the check number), and a held button followed by silence. You can watch the device reject the bad input and release the button on its own.

## Setup

You need [Wokwi for VS Code](https://docs.wokwi.com/vscode/getting-started) with its free license for open-source projects, and PlatformIO to build the firmware. Install PlatformIO in its own environment, so its packages do not mix with the app's:

```powershell
py -3.12 -m venv research/envs/platformio
research\envs\platformio\Scripts\python -m pip install platformio
research\envs\platformio\Scripts\pio run -d firmware/wokwi
python -m pip install -e ".[serial]"
```

In VS Code, press F1, choose "Wokwi: Select Config File", pick `firmware/wokwi/wokwi.toml`, and start the simulator. Then run:

```powershell
python -m gesture_mouse --serial rfc2217://localhost:4000
```

The app first sends a HELLO message. If the board does not answer, the app stops and tells you why. With `--serial`, the real mouse is never moved. The same option also accepts a real port, such as `--serial COM5`.

The simulator slows down or pauses when its tab is hidden, including when another window covers it. Put the camera window and the Wokwi tab side by side, or move the Wokwi tab into its own window (right-click the tab, then "Move into New Window"). The app does not wait for replies, so a slow simulator does not freeze it. If a button press gets no ACK within 2 seconds, the app releases every button and stops, as the protocol requires.

To measure how fast the board answers:

```powershell
python scripts/serial_check.py rfc2217://localhost:4000
```

It sends 300 heartbeat messages, then prints the reply times and any messages that got no ACK.

To run only the demo in the browser, create a new ESP32 project on [wokwi.com](https://wokwi.com). Add `sketch.ino`, `diagram.json`, and `libraries.txt` from this folder, plus `protocol.h`, `protocol.c`, `device.h`, and `device.c` from `firmware/src/`.

## Manual checks

The simulator needs a person to watch it, so check it by hand after you start it:

| Check | Do this | Expect |
|---|---|---|
| Demo | Start the simulator and wait 5 seconds | `DEMO` on the screen. The dot draws a box. The `bad` count rises after the broken message, and `wd` rises after the host goes silent |
| Connect | Run `python -m gesture_mouse --serial rfc2217://localhost:4000` | `LIVE` on the screen, and the app log shows `Device on ... answered` |
| Gestures | Try each gesture in the gesture table | The OLED screen and LEDs react as listed |
| Pause | Press `p` during a drag | `PAUSED` on the screen, and the green LED turns off |
| Reply time | Run `python scripts/serial_check.py rfc2217://localhost:4000` with the tab visible | 300 of 300 messages answered |
| No device | Stop the simulator, then run the same command | The app stops with an error and exit code 6 |
