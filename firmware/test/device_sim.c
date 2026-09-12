/*
 * Runs the device code on a laptop, with no hardware.
 * Input lines:  "T <ms>" sets the simulated time; "X <hex bytes>" delivers bytes.
 * Output lines: one per event, plus "REPLY <hex>" for every frame the device sends back.
 * Usage: device_sim <watchdog_ms> <byte_timeout_ms>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "device.h"
#include "protocol.h"

static void print_reply(const uint8_t *buf, size_t n)
{
    if (n == 0) {
        return;
    }
    printf("REPLY");
    for (size_t i = 0; i < n; i++) {
        printf(" %02x", buf[i]);
    }
    printf("\n");
}

static void print_event(device_event ev, const proto_frame *f, const device *d)
{
    const uint8_t *p = f->payload;
    switch (ev) {
    case DEVICE_HELLO: printf("HELLO v%u\n", p[0]); break;
    case DEVICE_MOVE:
        printf("MOVE %d %d\n", (int16_t)(uint16_t)(p[0] | (p[1] << 8)),
               (int16_t)(uint16_t)(p[2] | (p[3] << 8)));
        break;
    case DEVICE_BUTTON:
        printf("BUTTON %s %s\n", p[0] ? "right" : "left", p[1] ? "down" : "up");
        break;
    case DEVICE_SCROLL: printf("SCROLL %d\n", (int8_t)p[0]); break;
    case DEVICE_STATE: printf("STATE %u\n", p[0]); break;
    case DEVICE_HEARTBEAT: printf("HEARTBEAT\n"); break;
    case DEVICE_RELEASE_ALL: printf("RELEASE_ALL buttons=%u\n", d->buttons); break;
    case DEVICE_REJECTED: printf("REJECTED seq=%u type=0x%02x\n", f->seq, f->type); break;
    }
}

static void feed(proto_parser *parser, device *d, uint8_t byte, uint32_t now)
{
    uint8_t reply[PROTO_MAX_FRAME];
    proto_frame frame;
    proto_result r;
    proto_parser_push(parser, byte, now);
    while ((r = proto_parser_poll(parser, &frame)) != PROTO_NONE) {
        size_t n;
        if (r == PROTO_FRAME) {
            device_event ev;
            n = device_handle(d, &frame, now, &ev, reply, sizeof(reply));
            print_event(ev, &frame, d);
        } else {
            printf("BAD_FRAME seq=%u reason=%u\n", parser->error_seq, parser->error_reason);
            n = device_nack(parser->error_seq, parser->error_reason, reply, sizeof(reply));
        }
        print_reply(reply, n);
    }
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: device_sim <watchdog_ms> <byte_timeout_ms>\n");
        return 2;
    }
    uint32_t watchdog = (uint32_t)strtoul(argv[1], NULL, 10);
    uint32_t byte_timeout = (uint32_t)strtoul(argv[2], NULL, 10);
    uint32_t now = 0;
    proto_parser parser;
    device dev;
    char line[4096];

    proto_parser_init(&parser, byte_timeout);
    device_init(&dev, watchdog, now);

    while (fgets(line, sizeof(line), stdin) != NULL) {
        char *cursor = line + 1;
        if (line[0] == 'T') {
            now = (uint32_t)strtoul(cursor, NULL, 10);
            if (device_check_watchdog(&dev, now)) {
                printf("WATCHDOG release_all at %lu ms\n", (unsigned long)now);
            }
        } else if (line[0] == 'X') {
            for (;;) {
                char *end;
                unsigned long value = strtoul(cursor, &end, 16);
                if (end == cursor) {
                    break;
                }
                if (value > 0xFFu) {
                    fprintf(stderr, "byte out of range\n");
                    return 2;
                }
                feed(&parser, &dev, (uint8_t)value, now);
                cursor = end;
            }
        }
        fflush(stdout);
    }
    printf("END buttons=%u state=%u x=%ld y=%ld scroll=%ld\n", dev.buttons, dev.state,
           (long)dev.x, (long)dev.y, (long)dev.scroll);
    return 0;
}
