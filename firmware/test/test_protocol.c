/* Tests for the protocol parser and device logic. Exit code 0 means every check passed. */
#include <stdio.h>
#include <string.h>

#include "device.h"
#include "protocol.h"

static int failures = 0;
static int checks = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        checks++;                                                       \
        if (!(cond)) {                                                  \
            failures++;                                                 \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);      \
        }                                                               \
    } while (0)

typedef struct {
    int frames;
    int errors;
    proto_frame last;
    uint8_t last_reason;
    uint8_t last_error_seq;
} results;

static void feed(proto_parser *p, const uint8_t *bytes, size_t n, uint32_t tick, results *r)
{
    for (size_t i = 0; i < n; i++) {
        proto_result res;
        proto_parser_push(p, bytes[i], tick);
        while ((res = proto_parser_poll(p, &r->last)) != PROTO_NONE) {
            if (res == PROTO_FRAME) {
                r->frames++;
            } else {
                r->errors++;
                r->last_reason = p->error_reason;
                r->last_error_seq = p->error_seq;
            }
        }
    }
}

static size_t frame_of(uint8_t type, uint8_t seq, const uint8_t *payload, uint8_t len,
                       uint8_t *out)
{
    return proto_encode(type, seq, payload, len, out, PROTO_MAX_FRAME);
}

static void test_crc_check_value(void)
{
    const uint8_t text[] = "123456789";
    CHECK(proto_crc16(text, 9) == 0x29B1u);
    CHECK(proto_crc16(text, 0) == 0xFFFFu);
}

static void test_encode_rejects_bad_input(void)
{
    uint8_t out[PROTO_MAX_FRAME];
    uint8_t big[PROTO_MAX_PAYLOAD + 1] = {0};
    CHECK(proto_encode(PROTO_MOVE, 1, big, PROTO_MAX_PAYLOAD + 1, out, sizeof(out)) == 0);
    CHECK(proto_encode(PROTO_HEARTBEAT, 1, NULL, 0, out, 4) == 0);
    CHECK(proto_encode(PROTO_MOVE, 1, NULL, 4, out, sizeof(out)) == 0);
    CHECK(proto_encode(PROTO_HEARTBEAT, 1, NULL, 0, out, sizeof(out)) == 7);
}

static void test_every_type_round_trips(void)
{
    const uint8_t types[] = {PROTO_HELLO, PROTO_HELLO_ACK, PROTO_MOVE, PROTO_BUTTON,
                             PROTO_SCROLL, PROTO_STATE, PROTO_HEARTBEAT, PROTO_RELEASE_ALL,
                             PROTO_ACK, PROTO_NACK};
    uint8_t payload[PROTO_MAX_PAYLOAD] = {1, 0xFE, 0x03, 0x80};
    for (size_t i = 0; i < sizeof(types); i++) {
        proto_parser p;
        results r = {0};
        uint8_t buf[PROTO_MAX_FRAME];
        uint8_t len = (uint8_t)proto_payload_size(types[i]);
        size_t n = frame_of(types[i], (uint8_t)i, payload, len, buf);
        proto_parser_init(&p, 100);
        feed(&p, buf, n, 0, &r);
        CHECK(r.frames == 1 && r.errors == 0);
        CHECK(r.last.type == types[i] && r.last.seq == i && r.last.len == len);
        CHECK(memcmp(r.last.payload, payload, len) == 0);
    }
}

static void test_bad_crc(void)
{
    proto_parser p;
    results r = {0};
    uint8_t buf[PROTO_MAX_FRAME];
    size_t n = frame_of(PROTO_HEARTBEAT, 9, NULL, 0, buf);
    buf[n - 1] ^= 0x01u;
    proto_parser_init(&p, 100);
    feed(&p, buf, n, 0, &r);
    CHECK(r.frames == 0 && r.errors >= 1);
    CHECK(r.last_reason == PROTO_BAD_CRC && r.last_error_seq == 9);
}

static void test_short_frame_times_out(void)
{
    proto_parser p;
    results r = {0};
    uint8_t buf[PROTO_MAX_FRAME];
    size_t n = frame_of(PROTO_SCROLL, 3, (const uint8_t *)"\x05", 1, buf);
    proto_parser_init(&p, 50);
    feed(&p, buf, n - 2, 0, &r);
    CHECK(r.frames == 0 && r.errors == 0);
    feed(&p, buf, n, 200, &r);
    CHECK(r.frames == 1 && r.last.payload[0] == 5);
}

static void test_garbage_between_frames(void)
{
    proto_parser p;
    results r = {0};
    uint8_t a[PROTO_MAX_FRAME], b[PROTO_MAX_FRAME];
    const uint8_t junk[] = {0x00, 0xFF, 0x12, PROTO_SOF, 0x01, 0x13};
    size_t na = frame_of(PROTO_HEARTBEAT, 1, NULL, 0, a);
    size_t nb = frame_of(PROTO_STATE, 2, (const uint8_t *)"\x02", 1, b);
    proto_parser_init(&p, 100);
    feed(&p, junk, 3, 0, &r);
    feed(&p, a, na, 0, &r);
    feed(&p, junk, sizeof(junk), 0, &r);
    feed(&p, b, nb, 0, &r);
    CHECK(r.frames == 2);
    CHECK(r.last.type == PROTO_STATE && r.last.seq == 2);
}

static void test_oversized_length(void)
{
    proto_parser p;
    results r = {0};
    uint8_t buf[PROTO_MAX_FRAME];
    size_t n = frame_of(PROTO_HEARTBEAT, 4, NULL, 0, buf);
    const uint8_t bad[] = {PROTO_SOF, PROTO_VERSION, PROTO_MOVE, 7, 200};
    proto_parser_init(&p, 100);
    feed(&p, bad, sizeof(bad), 0, &r);
    CHECK(r.errors == 1 && r.last_reason == PROTO_BAD_LENGTH && r.last_error_seq == 7);
    feed(&p, buf, n, 0, &r);
    CHECK(r.frames == 1 && r.last.seq == 4);
}

static void test_wrong_length_type_and_version(void)
{
    proto_parser p;
    results r = {0};
    uint8_t buf[PROTO_MAX_FRAME];
    size_t n;
    proto_parser_init(&p, 100);

    n = frame_of(PROTO_MOVE, 1, (const uint8_t *)"\x01\x02", 2, buf);
    feed(&p, buf, n, 0, &r);
    CHECK(r.last_reason == PROTO_BAD_LENGTH && r.frames == 0);

    n = frame_of(0x7E, 2, NULL, 0, buf);
    feed(&p, buf, n, 0, &r);
    CHECK(r.last_reason == PROTO_UNKNOWN_TYPE && r.last_error_seq == 2);

    n = frame_of(PROTO_HEARTBEAT, 3, NULL, 0, buf);
    buf[1] = 0x02;
    {
        uint16_t crc = proto_crc16(&buf[1], 4);
        buf[5] = (uint8_t)(crc & 0xFFu);
        buf[6] = (uint8_t)(crc >> 8);
    }
    feed(&p, buf, n, 0, &r);
    CHECK(r.last_reason == PROTO_BAD_VERSION && r.last_error_seq == 3);
    CHECK(r.frames == 0 && r.errors == 3);
}

static void test_sequence_wraps_and_back_to_back(void)
{
    proto_parser p;
    results r = {0};
    uint8_t stream[PROTO_MAX_FRAME * 3];
    size_t n = 0;
    n += frame_of(PROTO_HEARTBEAT, 254, NULL, 0, &stream[n]);
    n += frame_of(PROTO_HEARTBEAT, 255, NULL, 0, &stream[n]);
    n += frame_of(PROTO_HEARTBEAT, 0, NULL, 0, &stream[n]);
    proto_parser_init(&p, 100);
    feed(&p, stream, n, 0, &r);
    CHECK(r.frames == 3 && r.last.seq == 0);
}

static void test_frame_inside_bad_frame_is_found(void)
{
    proto_parser p;
    results r = {0};
    uint8_t good[PROTO_MAX_FRAME];
    size_t ng = frame_of(PROTO_HEARTBEAT, 8, NULL, 0, good);
    uint8_t stream[64] = {PROTO_SOF, PROTO_VERSION, PROTO_MOVE, 1, 4};
    memcpy(&stream[5], good, ng);
    proto_parser_init(&p, 100);
    feed(&p, stream, 5 + ng, 0, &r);
    CHECK(r.frames == 1 && r.last.seq == 8);
}

static void test_random_bytes_never_break_the_parser(void)
{
    proto_parser p;
    results r = {0};
    uint32_t seed = 12345u;
    uint8_t good[PROTO_MAX_FRAME];
    size_t ng = frame_of(PROTO_HEARTBEAT, 77, NULL, 0, good);
    proto_parser_init(&p, 100);
    for (uint32_t i = 0; i < 1000000u; i++) {
        uint8_t byte;
        seed = seed * 1103515245u + 12345u;
        byte = (uint8_t)(seed >> 16);
        feed(&p, &byte, 1, i / 1000u, &r);
        CHECK(p.count <= sizeof(p.buf));
    }
    r.frames = 0;
    feed(&p, good, ng, 5000u, &r);
    CHECK(r.frames == 1 && r.last.seq == 77);
}

static void test_device_buttons_and_release(void)
{
    device d;
    device_event ev;
    proto_frame f = {PROTO_VERSION, PROTO_BUTTON, 1, 2, {0, 1}};
    uint8_t out[PROTO_MAX_FRAME];
    device_init(&d, 500, 0);
    CHECK(device_handle(&d, &f, 10, &ev, out, sizeof(out)) > 0);
    CHECK(ev == DEVICE_BUTTON && d.buttons == DEVICE_BUTTON_LEFT && out[2] == PROTO_ACK);
    f.type = PROTO_RELEASE_ALL;
    f.len = 0;
    device_handle(&d, &f, 20, &ev, out, sizeof(out));
    CHECK(ev == DEVICE_RELEASE_ALL && d.buttons == 0);
    f.type = PROTO_BUTTON;
    f.len = 2;
    f.payload[0] = 5;
    device_handle(&d, &f, 30, &ev, out, sizeof(out));
    CHECK(ev == DEVICE_REJECTED && out[2] == PROTO_NACK && d.buttons == 0);
}

static void test_device_rejects_host_bound_types(void)
{
    device d;
    device_event ev;
    proto_frame f = {PROTO_VERSION, PROTO_ACK, 4, 1, {4}};
    uint8_t out[PROTO_MAX_FRAME];
    device_init(&d, 500, 0);
    device_handle(&d, &f, 10, &ev, out, sizeof(out));
    CHECK(ev == DEVICE_REJECTED && out[2] == PROTO_NACK && out[6] == PROTO_UNKNOWN_TYPE);
}

static void test_device_hello(void)
{
    device d;
    device_event ev;
    proto_frame f = {PROTO_VERSION, PROTO_HELLO, 0, 1, {PROTO_VERSION}};
    uint8_t out[PROTO_MAX_FRAME];
    device_init(&d, 500, 0);
    CHECK(device_handle(&d, &f, 1, &ev, out, sizeof(out)) == 10);
    CHECK(ev == DEVICE_HELLO && out[2] == PROTO_HELLO_ACK && out[6] == DEVICE_FW_MAJOR);
    f.payload[0] = 9;
    device_handle(&d, &f, 2, &ev, out, sizeof(out));
    CHECK(ev == DEVICE_REJECTED && out[6] == PROTO_BAD_VERSION);
}

static void test_watchdog(void)
{
    device d;
    device_event ev;
    proto_frame down = {PROTO_VERSION, PROTO_BUTTON, 1, 2, {1, 1}};
    proto_frame beat = {PROTO_VERSION, PROTO_HEARTBEAT, 2, 0, {0}};
    uint8_t out[PROTO_MAX_FRAME];
    device_init(&d, 500, 0);
    device_handle(&d, &down, 100, &ev, out, sizeof(out));
    CHECK(device_check_watchdog(&d, 600) == 0 && d.buttons == DEVICE_BUTTON_RIGHT);
    device_handle(&d, &beat, 550, &ev, out, sizeof(out));
    CHECK(device_check_watchdog(&d, 1000) == 0 && d.buttons != 0);
    CHECK(device_check_watchdog(&d, 1051) == 1 && d.buttons == 0);
    CHECK(device_check_watchdog(&d, 5000) == 0);
    CHECK(device_check_watchdog(&d, 0xFFFFFFF0u) == 0);
}

static void test_moves_and_scroll(void)
{
    device d;
    device_event ev;
    proto_frame move = {PROTO_VERSION, PROTO_MOVE, 1, 4, {0x0A, 0x00, 0xFD, 0xFF}};
    proto_frame scroll = {PROTO_VERSION, PROTO_SCROLL, 2, 1, {0xFE}};
    uint8_t out[PROTO_MAX_FRAME];
    device_init(&d, 500, 0);
    device_handle(&d, &move, 1, &ev, out, sizeof(out));
    device_handle(&d, &scroll, 2, &ev, out, sizeof(out));
    CHECK(d.x == 10 && d.y == -3 && d.scroll == -2);
}

int main(void)
{
    test_crc_check_value();
    test_encode_rejects_bad_input();
    test_every_type_round_trips();
    test_bad_crc();
    test_short_frame_times_out();
    test_garbage_between_frames();
    test_oversized_length();
    test_wrong_length_type_and_version();
    test_sequence_wraps_and_back_to_back();
    test_frame_inside_bad_frame_is_found();
    test_random_bytes_never_break_the_parser();
    test_device_buttons_and_release();
    test_device_rejects_host_bound_types();
    test_device_hello();
    test_watchdog();
    test_moves_and_scroll();
    printf("%d checks, %d failed\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
