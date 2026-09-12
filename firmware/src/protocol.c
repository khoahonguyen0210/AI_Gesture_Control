#include "protocol.h"

#include <string.h>

uint16_t proto_crc16(const uint8_t *data, size_t len)
{
    uint32_t crc = 0xFFFFu;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint32_t)data[i] << 8;
        for (int bit = 0; bit < 8; bit++) {
            crc = (crc & 0x8000u) ? ((crc << 1) ^ 0x1021u) : (crc << 1);
            crc &= 0xFFFFu;
        }
    }
    return (uint16_t)crc;
}

int proto_payload_size(uint8_t type)
{
    switch (type) {
    case PROTO_HELLO: return 1;
    case PROTO_HELLO_ACK: return 3;
    case PROTO_MOVE: return 4;
    case PROTO_BUTTON: return 2;
    case PROTO_SCROLL: return 1;
    case PROTO_STATE: return 1;
    case PROTO_HEARTBEAT: return 0;
    case PROTO_RELEASE_ALL: return 0;
    case PROTO_ACK: return 1;
    case PROTO_NACK: return 2;
    default: return -1;
    }
}

size_t proto_encode(uint8_t type, uint8_t seq, const uint8_t *payload, uint8_t len,
                    uint8_t *out, size_t out_size)
{
    size_t total = PROTO_HEADER_SIZE + (size_t)len + 2u;
    if (len > PROTO_MAX_PAYLOAD || out == NULL || out_size < total || (len > 0 && payload == NULL)) {
        return 0;
    }
    out[0] = PROTO_SOF;
    out[1] = PROTO_VERSION;
    out[2] = type;
    out[3] = seq;
    out[4] = len;
    if (len > 0) {
        memcpy(&out[PROTO_HEADER_SIZE], payload, len);
    }
    uint16_t crc = proto_crc16(&out[1], 4u + (size_t)len);
    out[PROTO_HEADER_SIZE + len] = (uint8_t)(crc & 0xFFu);
    out[PROTO_HEADER_SIZE + len + 1u] = (uint8_t)(crc >> 8);
    return total;
}

void proto_parser_init(proto_parser *p, uint32_t timeout_ticks)
{
    memset(p, 0, sizeof(*p));
    p->timeout_ticks = timeout_ticks;
}

static void drop(proto_parser *p, size_t n)
{
    if (n >= p->count) {
        p->count = 0;
        return;
    }
    memmove(p->buf, &p->buf[n], p->count - n);
    p->count -= n;
}

void proto_parser_push(proto_parser *p, uint8_t byte, uint32_t tick)
{
    if (p->count > 0 && (uint32_t)(tick - p->last_tick) > p->timeout_ticks) {
        p->count = 0;
    }
    if (p->count == sizeof(p->buf)) {
        drop(p, 1);
    }
    p->buf[p->count++] = byte;
    p->last_tick = tick;
}

static proto_result fail(proto_parser *p, uint8_t reason, size_t skip)
{
    p->error_reason = reason;
    p->error_seq = p->buf[3];
    drop(p, skip);
    return PROTO_ERROR;
}

proto_result proto_parser_poll(proto_parser *p, proto_frame *frame)
{
    while (p->count > 0 && p->buf[0] != PROTO_SOF) {
        drop(p, 1);
    }
    if (p->count < PROTO_HEADER_SIZE) {
        return PROTO_NONE;
    }
    uint8_t len = p->buf[4];
    if (len > PROTO_MAX_PAYLOAD) {
        return fail(p, PROTO_BAD_LENGTH, 1);
    }
    size_t total = PROTO_HEADER_SIZE + (size_t)len + 2u;
    if (p->count < total) {
        return PROTO_NONE;
    }
    uint16_t got = (uint16_t)(p->buf[PROTO_HEADER_SIZE + len] |
                              (uint16_t)(p->buf[PROTO_HEADER_SIZE + len + 1u] << 8));
    if (got != proto_crc16(&p->buf[1], 4u + (size_t)len)) {
        /* Drop one byte only: a real frame may start inside the bad one. */
        return fail(p, PROTO_BAD_CRC, 1);
    }
    if (p->buf[1] != PROTO_VERSION) {
        return fail(p, PROTO_BAD_VERSION, total);
    }
    int expected = proto_payload_size(p->buf[2]);
    if (expected < 0) {
        return fail(p, PROTO_UNKNOWN_TYPE, total);
    }
    if (expected != (int)len) {
        return fail(p, PROTO_BAD_LENGTH, total);
    }
    frame->version = p->buf[1];
    frame->type = p->buf[2];
    frame->seq = p->buf[3];
    frame->len = len;
    memset(frame->payload, 0, sizeof(frame->payload));
    memcpy(frame->payload, &p->buf[PROTO_HEADER_SIZE], len);
    drop(p, total);
    return PROTO_FRAME;
}
