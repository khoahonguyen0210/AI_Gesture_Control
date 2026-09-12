/* Device side: runs host commands, keeps output state, and releases everything on silence. */
#ifndef GESTURE_DEVICE_H
#define GESTURE_DEVICE_H

#include <stddef.h>
#include <stdint.h>

#include "protocol.h"

#define DEVICE_FW_MAJOR 0u
#define DEVICE_FW_MINOR 1u
#define DEVICE_BUTTON_LEFT 0x01u
#define DEVICE_BUTTON_RIGHT 0x02u

typedef enum {
    DEVICE_REJECTED = 0,
    DEVICE_HELLO,
    DEVICE_MOVE,
    DEVICE_BUTTON,
    DEVICE_SCROLL,
    DEVICE_STATE,
    DEVICE_HEARTBEAT,
    DEVICE_RELEASE_ALL
} device_event;

typedef struct {
    uint32_t watchdog_ticks;
    uint32_t last_valid_tick;
    int watchdog_fired;
    uint8_t buttons;
    uint8_t state;
    int32_t x;
    int32_t y;
    int32_t scroll;
} device;

void device_init(device *d, uint32_t watchdog_ticks, uint32_t tick);

/*
 * Runs one valid frame and writes the reply (ACK, HELLO_ACK, or NACK) to out.
 * Returns the reply size. *event says what happened; DEVICE_REJECTED means nothing ran.
 */
size_t device_handle(device *d, const proto_frame *f, uint32_t tick, device_event *event,
                     uint8_t *out, size_t out_size);

size_t device_nack(uint8_t seq, uint8_t reason, uint8_t *out, size_t out_size);

void device_release_all(device *d);

/* Returns 1 once per silence longer than the watchdog time, after releasing all outputs. */
int device_check_watchdog(device *d, uint32_t tick);

#endif
