/*
 * Gesture Mouse serial protocol, version 1.
 *
 * Frame: SOF(0xA5) VER TYPE SEQ LEN PAYLOAD[LEN] CRC16
 * LEN is 0..16. CRC-16/CCITT-FALSE over VER..PAYLOAD, sent low byte first.
 * Multi-byte payload values are little-endian.
 * Plain C with fixed buffers and no hardware calls, so it can run on a microcontroller.
 */
#ifndef GESTURE_PROTOCOL_H
#define GESTURE_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#define PROTO_SOF 0xA5u
#define PROTO_VERSION 0x01u
#define PROTO_HEADER_SIZE 5u
#define PROTO_MAX_PAYLOAD 16u
#define PROTO_MAX_FRAME (PROTO_HEADER_SIZE + PROTO_MAX_PAYLOAD + 2u)

enum proto_type {
    PROTO_HELLO = 0x01,
    PROTO_HELLO_ACK = 0x02,
    PROTO_MOVE = 0x10,
    PROTO_BUTTON = 0x11,
    PROTO_SCROLL = 0x12,
    PROTO_STATE = 0x13,
    PROTO_HEARTBEAT = 0x20,
    PROTO_RELEASE_ALL = 0x21,
    PROTO_ACK = 0x30,
    PROTO_NACK = 0x31
};

enum proto_nack_reason {
    PROTO_BAD_CRC = 1,
    PROTO_BAD_LENGTH = 2,
    PROTO_UNKNOWN_TYPE = 3,
    PROTO_BAD_VERSION = 4
};

typedef struct {
    uint8_t version;
    uint8_t type;
    uint8_t seq;
    uint8_t len;
    uint8_t payload[PROTO_MAX_PAYLOAD];
} proto_frame;

typedef enum {
    PROTO_NONE = 0,  /* need more bytes */
    PROTO_FRAME = 1, /* a valid frame was written to *frame */
    PROTO_ERROR = 2  /* a bad frame was dropped; see error fields */
} proto_result;

typedef struct {
    uint8_t buf[PROTO_MAX_FRAME];
    size_t count;
    uint32_t last_tick;
    uint32_t timeout_ticks;
    uint8_t error_reason;
    uint8_t error_seq;
} proto_parser;

uint16_t proto_crc16(const uint8_t *data, size_t len);

/* Expected payload length for a type, or -1 for an unknown type. */
int proto_payload_size(uint8_t type);

/* Writes a frame to out. Returns its size, or 0 if the input is invalid or out is too small. */
size_t proto_encode(uint8_t type, uint8_t seq, const uint8_t *payload, uint8_t len,
                    uint8_t *out, size_t out_size);

void proto_parser_init(proto_parser *p, uint32_t timeout_ticks);

/* Adds one byte. A partial frame older than timeout_ticks is dropped first. */
void proto_parser_push(proto_parser *p, uint8_t byte, uint32_t tick);

/* Call until it returns PROTO_NONE after each push. */
proto_result proto_parser_poll(proto_parser *p, proto_frame *frame);

#endif
