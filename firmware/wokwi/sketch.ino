/*
 * Gesture Mouse device for Wokwi: an ESP32 that shows each mouse action on an OLED and LEDs.
 * LIVE: frames from the app over Serial. DEMO: a built-in script after DEMO_AFTER_MS of silence.
 */
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino.h>
#include <Wire.h>

#include "device.h"
#include "protocol.h"

#define BAUD 115200
#define WATCHDOG_MS 500u
#define BYTE_TIMEOUT_MS 50u
#define DEMO_AFTER_MS 5000u
#define FLASH_MS 200u  /* a click stays visible this long */
#define LINK_MS 300u   /* the link LED stays on this long after a valid frame */
#define REDRAW_MS 40u
#define HOST_W 1920    /* SerialBackend's default screen size */
#define HOST_H 1080

#define PIN_LED_LEFT 25
#define PIN_LED_RIGHT 26
#define PIN_LED_LINK 27

#define DEMO_GARBAGE 0xF0u
#define DEMO_BAD_CRC 0xF1u

typedef struct {
    proto_parser parser;
    device dev;
    uint32_t frames_ok;
    uint32_t frames_bad;
    uint32_t watchdog_releases;
    uint32_t last_frame_ms;
    uint32_t press_ms[2];
} session;

typedef struct {
    uint16_t wait_ms;
    uint8_t kind; /* a proto_type, DEMO_GARBAGE, or DEMO_BAD_CRC */
    uint8_t len;
    uint8_t payload[4];
} demo_step;

#define LE16(v) (uint8_t)((uint16_t)(int16_t)(v) & 0xFFu), (uint8_t)((uint16_t)(int16_t)(v) >> 8)
#define MOVE(wait, dx, dy) {wait, PROTO_MOVE, 4, {LE16(dx), LE16(dy)}}
#define BUTTON(wait, b, down) {wait, PROTO_BUTTON, 2, {b, down}}
#define STATE(wait, s) {wait, PROTO_STATE, 1, {s}}

static const demo_step DEMO[] = {
    {400, PROTO_HELLO, 1, {PROTO_VERSION}},
    STATE(300, DEVICE_STATE_POINTING),
    MOVE(120, 240, 0), MOVE(120, 240, 0), MOVE(120, 240, 0),
    MOVE(120, 0, 135), MOVE(120, 0, 135), MOVE(120, 0, 135),
    MOVE(120, -240, 0), MOVE(120, -240, 0), MOVE(120, -240, 0),
    MOVE(120, 0, -135), MOVE(120, 0, -135), MOVE(120, 0, -135),
    STATE(300, DEVICE_STATE_PINCH), BUTTON(0, 0, 1), BUTTON(0, 0, 0),
    STATE(400, DEVICE_STATE_DRAGGING), BUTTON(0, 0, 1),
    MOVE(150, -200, 100), MOVE(150, -200, 100), MOVE(150, -200, 100),
    BUTTON(150, 0, 0), STATE(0, DEVICE_STATE_POINTING),
    MOVE(300, 600, -300),
    STATE(400, DEVICE_STATE_RIGHT_CLICK), BUTTON(0, 1, 1), BUTTON(0, 1, 0),
    STATE(400, DEVICE_STATE_SCROLLING),
    {200, PROTO_SCROLL, 1, {(uint8_t)-3}}, {200, PROTO_SCROLL, 1, {(uint8_t)-3}},
    {200, PROTO_SCROLL, 1, {3}},
    STATE(300, DEVICE_STATE_IDLE),
    {400, DEMO_GARBAGE, 0, {0}},
    {300, DEMO_BAD_CRC, 2, {0, 1}}, /* a left press with a broken CRC: must not press */
    {300, PROTO_HEARTBEAT, 0, {0}},
    BUTTON(300, 0, 1),               /* then the host goes silent with the button held */
    {WATCHDOG_MS + 700u, PROTO_HEARTBEAT, 0, {0}},
};
#define DEMO_STEPS (sizeof(DEMO) / sizeof(DEMO[0]))

static const char *const STATE_NAMES[DEVICE_STATE_COUNT] = {
    "IDLE", "POINT", "PINCH", "DRAG", "RIGHT CLICK", "SCROLL", "NO HAND", "PAUSED",
};

static Adafruit_SSD1306 oled(128, 64, &Wire, -1);
static session host;
static session demo;
static uint32_t last_host_byte_ms;
static size_t demo_index;
static uint32_t demo_next_ms;
static uint8_t demo_seq;
static uint32_t last_draw_ms;

static void session_init(session *s, uint32_t now)
{
    memset(s, 0, sizeof(*s));
    proto_parser_init(&s->parser, BYTE_TIMEOUT_MS);
    device_init(&s->dev, WATCHDOG_MS, now);
}

static void on_frame(session *s, device_event ev, const proto_frame *f, uint32_t now)
{
    if (ev == DEVICE_REJECTED) {
        s->frames_bad++;
        return;
    }
    s->frames_ok++;
    s->last_frame_ms = now;
    if (ev == DEVICE_BUTTON && f->payload[1]) {
        s->press_ms[f->payload[0]] = now;
    }
}

/* Feeds one byte through a session. Replies go back over Serial only for the live host. */
static void feed(session *s, uint8_t byte, uint32_t now, bool reply)
{
    uint8_t out[PROTO_MAX_FRAME];
    proto_frame frame;
    proto_result r;
    proto_parser_push(&s->parser, byte, now);
    while ((r = proto_parser_poll(&s->parser, &frame)) != PROTO_NONE) {
        size_t n;
        if (r == PROTO_FRAME) {
            device_event ev;
            n = device_handle(&s->dev, &frame, now, &ev, out, sizeof(out));
            on_frame(s, ev, &frame, now);
        } else {
            s->frames_bad++;
            n = device_nack(s->parser.error_seq, s->parser.error_reason, out, sizeof(out));
        }
        if (reply && n > 0) {
            Serial.write(out, n);
        }
    }
}

static void check_watchdog(session *s, uint32_t now)
{
    uint8_t held = s->dev.buttons;
    if (device_check_watchdog(&s->dev, now) && held) {
        s->watchdog_releases++;
    }
}

static void run_demo(uint32_t now)
{
    static const uint8_t garbage[] = {0x13, 0x37, PROTO_SOF, PROTO_VERSION};
    uint8_t buf[PROTO_MAX_FRAME];
    const demo_step *step;
    size_t n;
    if ((int32_t)(now - demo_next_ms) < 0) {
        return;
    }
    step = &DEMO[demo_index];
    if (step->kind == DEMO_GARBAGE) {
        for (n = 0; n < sizeof(garbage); n++) {
            feed(&demo, garbage[n], now, false);
        }
    } else {
        uint8_t type = step->kind == DEMO_BAD_CRC ? (uint8_t)PROTO_BUTTON : step->kind;
        n = proto_encode(type, demo_seq++, step->payload, step->len, buf, sizeof(buf));
        if (step->kind == DEMO_BAD_CRC) {
            buf[n - 1] ^= 0xFFu;
        }
        for (size_t i = 0; i < n; i++) {
            feed(&demo, buf[i], now, false);
        }
    }
    demo_index = (demo_index + 1) % DEMO_STEPS;
    demo_next_ms = now + DEMO[demo_index].wait_ms;
}

static bool lit(const session *s, int button, uint8_t mask, uint32_t now)
{
    return (s->dev.buttons & mask) != 0 ||
           (s->press_ms[button] != 0 && now - s->press_ms[button] < FLASH_MS);
}

static int clamp(int v, int lo, int hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

static void draw(const session *s, const char *mode, uint32_t now)
{
    /* Cursor area: 85x48 pixels for a 1920x1080 screen; device x and y count from its center. */
    const int bx = 0, by = 16, bw = 85, bh = 48;
    int cx = clamp(bx + bw / 2 + (int)(s->dev.x * bw / HOST_W), bx + 2, bx + bw - 3);
    int cy = clamp(by + bh / 2 + (int)(s->dev.y * bh / HOST_H), by + 2, by + bh - 3);
    bool left = lit(s, 0, DEVICE_BUTTON_LEFT, now);
    bool right = lit(s, 1, DEVICE_BUTTON_RIGHT, now);
    uint8_t state = s->dev.state < DEVICE_STATE_COUNT ? s->dev.state : 0;

    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);
    oled.setCursor(0, 0);
    oled.print(mode);
    oled.print(' ');
    oled.print(STATE_NAMES[state]);
    oled.setCursor(0, 8);
    oled.printf("ok%lu bad%lu wd%lu", (unsigned long)s->frames_ok, (unsigned long)s->frames_bad,
                (unsigned long)s->watchdog_releases);

    oled.drawRect(bx, by, bw, bh, SSD1306_WHITE);
    if (left) {
        oled.fillCircle(cx, cy, 3, SSD1306_WHITE);
    } else {
        oled.drawCircle(cx, cy, 3, SSD1306_WHITE);
    }

    oled.drawRect(90, 16, 17, 14, SSD1306_WHITE);
    oled.drawRect(110, 16, 17, 14, SSD1306_WHITE);
    if (left) {
        oled.fillRect(90, 16, 17, 14, SSD1306_WHITE);
    }
    if (right) {
        oled.fillRect(110, 16, 17, 14, SSD1306_WHITE);
    }
    oled.setTextColor(left ? SSD1306_BLACK : SSD1306_WHITE);
    oled.setCursor(96, 20);
    oled.print('L');
    oled.setTextColor(right ? SSD1306_BLACK : SSD1306_WHITE);
    oled.setCursor(116, 20);
    oled.print('R');
    oled.setTextColor(SSD1306_WHITE);
    oled.setCursor(90, 36);
    oled.printf("S%+ld", (long)s->dev.scroll);
    oled.display();

    digitalWrite(PIN_LED_LEFT, left ? HIGH : LOW);
    digitalWrite(PIN_LED_RIGHT, right ? HIGH : LOW);
    digitalWrite(PIN_LED_LINK, s->last_frame_ms != 0 && now - s->last_frame_ms < LINK_MS);
}

void setup()
{
    uint32_t now = millis();
    Serial.setRxBufferSize(1024);
    Serial.begin(BAUD);
    pinMode(PIN_LED_LEFT, OUTPUT);
    pinMode(PIN_LED_RIGHT, OUTPUT);
    pinMode(PIN_LED_LINK, OUTPUT);
    Wire.begin();
    oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
    oled.setTextSize(1);
    session_init(&host, now);
    session_init(&demo, now);
    last_host_byte_ms = now;
}

void loop()
{
    uint32_t now = millis();
    while (Serial.available() > 0) {
        last_host_byte_ms = now;
        feed(&host, (uint8_t)Serial.read(), now, true);
    }
    check_watchdog(&host, now);

    bool demo_mode = now - last_host_byte_ms > DEMO_AFTER_MS;
    if (demo_mode) {
        run_demo(now);
        check_watchdog(&demo, now);
    } else if (demo.frames_ok != 0 || demo.frames_bad != 0) {
        session_init(&demo, now); /* the next demo starts from its first step */
        demo_index = 0;
        demo_next_ms = now;
    }

    if (now - last_draw_ms >= REDRAW_MS) {
        last_draw_ms = now;
        if (demo_mode) {
            draw(&demo, "DEMO", now);
        } else {
            draw(&host, host.frames_ok != 0 ? "LIVE" : "WAIT", now);
        }
    }
}
