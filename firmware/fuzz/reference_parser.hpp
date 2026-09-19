// Second, independent parser for protocol version 1, written in C++17 from the protocol rules.
// It reads a whole byte buffer at once. Differential tests compare it with the C parser.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <vector>

namespace ref {

constexpr std::uint8_t kSof = 0xA5;
constexpr std::uint8_t kVersion = 0x01;
constexpr std::size_t kHeader = 5;
constexpr std::size_t kMaxPayload = 16;

enum class Reason : std::uint8_t { BadCrc = 1, BadLength = 2, UnknownType = 3, BadVersion = 4 };

struct Frame {
    std::uint8_t type;
    std::uint8_t seq;
    std::vector<std::uint8_t> payload;
    bool operator==(const Frame& o) const {
        return type == o.type && seq == o.seq && payload == o.payload;
    }
};

struct Error {
    Reason reason;
    std::uint8_t seq;
    bool operator==(const Error& o) const { return reason == o.reason && seq == o.seq; }
};

// Exactly one of frame or error is set.
struct Event {
    std::optional<Frame> frame;
    std::optional<Error> error;
    bool operator==(const Event& o) const { return frame == o.frame && error == o.error; }
};

constexpr std::array<std::uint16_t, 256> make_crc_table() {
    std::array<std::uint16_t, 256> table{};
    for (std::uint32_t i = 0; i < 256; ++i) {
        std::uint32_t crc = i << 8;
        for (int bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x8000u) ? ((crc << 1) ^ 0x1021u) : (crc << 1);
        }
        table[i] = static_cast<std::uint16_t>(crc & 0xFFFFu);
    }
    return table;
}

inline std::uint16_t crc16(const std::uint8_t* data, std::size_t len) {
    static constexpr auto table = make_crc_table();
    std::uint32_t crc = 0xFFFFu;
    for (std::size_t i = 0; i < len; ++i) {
        crc = ((crc << 8) ^ table[((crc >> 8) ^ data[i]) & 0xFFu]) & 0xFFFFu;
    }
    return static_cast<std::uint16_t>(crc);
}

inline std::optional<std::size_t> payload_size(std::uint8_t type) {
    switch (type) {
    case 0x01: return 1;  // HELLO
    case 0x02: return 3;  // HELLO_ACK
    case 0x10: return 4;  // MOVE
    case 0x11: return 2;  // BUTTON
    case 0x12: return 1;  // SCROLL
    case 0x13: return 1;  // STATE
    case 0x20: return 0;  // HEARTBEAT
    case 0x21: return 0;  // RELEASE_ALL
    case 0x30: return 1;  // ACK
    case 0x31: return 2;  // NACK
    default: return std::nullopt;
    }
}

// Rules: skip bytes until SOF; a length over 16 or a bad CRC drops one byte and searches again;
// a frame with a good CRC but a bad version, unknown type, or wrong length is dropped whole.
inline std::vector<Event> parse(const std::uint8_t* data, std::size_t size) {
    std::vector<Event> events;
    std::size_t i = 0;
    auto error = [&](Reason reason, std::uint8_t seq) {
        events.push_back(Event{std::nullopt, Error{reason, seq}});
    };
    while (i < size) {
        if (data[i] != kSof) {
            ++i;
            continue;
        }
        if (size - i < kHeader) {
            break;
        }
        const std::uint8_t seq = data[i + 3];
        const std::size_t len = data[i + 4];
        if (len > kMaxPayload) {
            error(Reason::BadLength, seq);
            ++i;
            continue;
        }
        const std::size_t total = kHeader + len + 2;
        if (size - i < total) {
            break;
        }
        const std::uint16_t sent = static_cast<std::uint16_t>(
            data[i + kHeader + len] | (data[i + kHeader + len + 1] << 8));
        if (sent != crc16(&data[i + 1], 4 + len)) {
            error(Reason::BadCrc, seq);
            ++i;
            continue;
        }
        const std::uint8_t version = data[i + 1];
        const std::uint8_t type = data[i + 2];
        const auto expected = payload_size(type);
        if (version != kVersion) {
            error(Reason::BadVersion, seq);
        } else if (!expected) {
            error(Reason::UnknownType, seq);
        } else if (*expected != len) {
            error(Reason::BadLength, seq);
        } else {
            Frame frame{type, seq, {data + i + kHeader, data + i + kHeader + len}};
            events.push_back(Event{std::move(frame), std::nullopt});
        }
        i += total;
    }
    return events;
}

}  // namespace ref
