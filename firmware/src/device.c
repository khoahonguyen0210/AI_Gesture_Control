#include "device.h"

#include <string.h>

void device_init(device *d, uint32_t watchdog_ticks, uint32_t tick)
{
    memset(d, 0, sizeof(*d));
    d->watchdog_ticks = watchdog_ticks;
    d->last_valid_tick = tick;
}

void device_release_all(device *d)
{
    d->buttons = 0;
    d->state = 0;
}

size_t device_nack(uint8_t seq, uint8_t reason, uint8_t *out, size_t out_size)
{
    uint8_t payload[2] = {seq, reason};
    return proto_encode(PROTO_NACK, seq, payload, 2, out, out_size);
}

static size_t ack(uint8_t seq, uint8_t *out, size_t out_size)
{
    return proto_encode(PROTO_ACK, seq, &seq, 1, out, out_size);
}

static int16_t read_i16(const uint8_t *p)
{
    return (int16_t)(uint16_t)(p[0] | (uint16_t)(p[1] << 8));
}

size_t device_handle(device *d, const proto_frame *f, uint32_t tick, device_event *event,
                     uint8_t *out, size_t out_size)
{
    const uint8_t *p = f->payload;
    *event = DEVICE_REJECTED;

    switch (f->type) {
    case PROTO_HELLO:
        if (p[0] != PROTO_VERSION) {
            return device_nack(f->seq, PROTO_BAD_VERSION, out, out_size);
        }
        device_release_all(d);
        d->x = 0;
        d->y = 0;
        d->scroll = 0;
        *event = DEVICE_HELLO;
        break;
    case PROTO_MOVE:
        d->x += read_i16(&p[0]);
        d->y += read_i16(&p[2]);
        *event = DEVICE_MOVE;
        break;
    case PROTO_BUTTON: {
        if (p[0] > 1 || p[1] > 1) {
            return device_nack(f->seq, PROTO_BAD_LENGTH, out, out_size);
        }
        uint8_t mask = p[0] == 0 ? DEVICE_BUTTON_LEFT : DEVICE_BUTTON_RIGHT;
        d->buttons = p[1] ? (uint8_t)(d->buttons | mask) : (uint8_t)(d->buttons & ~mask);
        *event = DEVICE_BUTTON;
        break;
    }
    case PROTO_SCROLL:
        d->scroll += (int8_t)p[0];
        *event = DEVICE_SCROLL;
        break;
    case PROTO_STATE:
        if (p[0] >= DEVICE_STATE_COUNT) {
            return device_nack(f->seq, PROTO_BAD_LENGTH, out, out_size);
        }
        d->state = p[0];
        *event = DEVICE_STATE;
        break;
    case PROTO_HEARTBEAT:
        *event = DEVICE_HEARTBEAT;
        break;
    case PROTO_RELEASE_ALL:
        device_release_all(d);
        *event = DEVICE_RELEASE_ALL;
        break;
    default:
        /* Device-to-host types are never run on the device. */
        return device_nack(f->seq, PROTO_UNKNOWN_TYPE, out, out_size);
    }

    d->last_valid_tick = tick;
    d->watchdog_fired = 0;
    if (*event == DEVICE_HELLO) {
        uint8_t reply[3] = {PROTO_VERSION, DEVICE_FW_MAJOR, DEVICE_FW_MINOR};
        return proto_encode(PROTO_HELLO_ACK, f->seq, reply, 3, out, out_size);
    }
    return ack(f->seq, out, out_size);
}

int device_check_watchdog(device *d, uint32_t tick)
{
    if (d->watchdog_fired || (uint32_t)(tick - d->last_valid_tick) <= d->watchdog_ticks) {
        return 0;
    }
    device_release_all(d);
    d->watchdog_fired = 1;
    return 1;
}
