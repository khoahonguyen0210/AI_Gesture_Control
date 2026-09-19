// Runs the C parser and the C++ reference parser on the same bytes and compares the results.
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "protocol.h"
#include "reference_parser.hpp"

namespace diff {

inline std::vector<ref::Event> run_c_parser(const std::uint8_t* data, std::size_t size,
                                            bool& overflow) {
    proto_parser parser;
    proto_parser_init(&parser, 1000);
    std::vector<ref::Event> events;
    proto_frame frame;
    overflow = false;
    for (std::size_t i = 0; i < size; ++i) {
        proto_parser_push(&parser, data[i], 0);
        proto_result result;
        while ((result = proto_parser_poll(&parser, &frame)) != PROTO_NONE) {
            if (result == PROTO_FRAME) {
                ref::Frame f{frame.type, frame.seq, {frame.payload, frame.payload + frame.len}};
                events.push_back(ref::Event{std::move(f), std::nullopt});
            } else {
                ref::Error e{static_cast<ref::Reason>(parser.error_reason), parser.error_seq};
                events.push_back(ref::Event{std::nullopt, e});
            }
        }
        overflow = overflow || parser.count > sizeof(parser.buf);
    }
    return events;
}

// True when both parsers agree, the C buffer stayed in bounds, and both CRCs agree.
inline bool same_result(const std::uint8_t* data, std::size_t size) {
    bool overflow = false;
    const auto c_events = run_c_parser(data, size, overflow);
    const auto ref_events = ref::parse(data, size);
    return !overflow && c_events == ref_events && proto_crc16(data, size) == ref::crc16(data, size);
}

}  // namespace diff
