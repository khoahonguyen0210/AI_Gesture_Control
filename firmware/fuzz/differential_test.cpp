// Deterministic differential test: many seeded byte streams through both parsers.
// Exit code 0 means the C parser and the C++ reference parser agreed on every stream.
#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>

#include "differential.hpp"

namespace {

using Bytes = std::vector<std::uint8_t>;

constexpr std::uint8_t kTypes[] = {0x01, 0x02, 0x10, 0x11, 0x12, 0x13, 0x20, 0x21, 0x30, 0x31};
constexpr int kStreams = 200000;

void append_frame(Bytes& out, std::mt19937& rng) {
    std::uniform_int_distribution<int> byte(0, 255);
    std::uniform_int_distribution<int> percent(0, 99);
    const bool odd_type = percent(rng) < 10;
    const std::uint8_t type = odd_type ? static_cast<std::uint8_t>(byte(rng))
                                       : kTypes[static_cast<std::size_t>(byte(rng)) % 10];
    std::size_t len = ref::payload_size(type).value_or(static_cast<std::size_t>(byte(rng) % 17));
    if (percent(rng) < 10) {
        len = static_cast<std::size_t>(byte(rng) % 17);
    }
    Bytes body{percent(rng) < 5 ? static_cast<std::uint8_t>(byte(rng)) : ref::kVersion, type,
               static_cast<std::uint8_t>(byte(rng)), static_cast<std::uint8_t>(len)};
    for (std::size_t i = 0; i < len; ++i) {
        body.push_back(static_cast<std::uint8_t>(byte(rng)));
    }
    const std::uint16_t crc = ref::crc16(body.data(), body.size());
    out.push_back(ref::kSof);
    out.insert(out.end(), body.begin(), body.end());
    out.push_back(static_cast<std::uint8_t>(crc & 0xFFu));
    out.push_back(static_cast<std::uint8_t>(crc >> 8));
}

void damage(Bytes& s, std::mt19937& rng) {
    std::uniform_int_distribution<int> percent(0, 99);
    std::uniform_int_distribution<int> byte(0, 255);
    if (s.empty()) {
        return;
    }
    std::uniform_int_distribution<std::size_t> pos(0, s.size() - 1);
    const int kind = percent(rng);
    if (kind < 25) {
        s[pos(rng)] ^= static_cast<std::uint8_t>(1u << (byte(rng) % 8));
    } else if (kind < 40) {
        s.erase(s.begin() + static_cast<std::ptrdiff_t>(pos(rng)));
    } else if (kind < 55) {
        s.insert(s.begin() + static_cast<std::ptrdiff_t>(pos(rng)),
                 static_cast<std::uint8_t>(byte(rng)));
    } else if (kind < 65) {
        s.resize(pos(rng));
    } else if (kind < 75) {
        s.insert(s.begin() + static_cast<std::ptrdiff_t>(pos(rng)), ref::kSof);
    }
}

bool check(const Bytes& s, int& failures) {
    if (diff::same_result(s.data(), s.size())) {
        return true;
    }
    if (failures++ < 5) {
        std::printf("MISMATCH (%zu bytes):", s.size());
        for (std::uint8_t b : s) {
            std::printf(" %02x", b);
        }
        std::printf("\n");
    }
    return false;
}

}  // namespace

int main() {
    int failures = 0;
    int streams = 0;
    std::mt19937 rng(20261010u);
    std::uniform_int_distribution<int> count(1, 12);
    std::uniform_int_distribution<int> damages(0, 3);
    std::uniform_int_distribution<int> byte(0, 255);

    const std::vector<Bytes> fixed = {
        {},
        {ref::kSof},
        {ref::kSof, ref::kSof, ref::kSof, ref::kSof, ref::kSof, ref::kSof, ref::kSof},
        {ref::kSof, 0x01, 0x10, 0x07, 0xFF},
    };
    for (const Bytes& s : fixed) {
        check(s, failures);
        ++streams;
    }

    for (int n = 0; n < kStreams; ++n) {
        Bytes s;
        for (int f = count(rng); f > 0; --f) {
            if (byte(rng) < 20) {
                s.push_back(static_cast<std::uint8_t>(byte(rng)));
            }
            append_frame(s, rng);
        }
        for (int d = damages(rng); d > 0; --d) {
            damage(s, rng);
        }
        check(s, failures);
        ++streams;
    }

    for (int n = 0; n < 2000; ++n) {
        Bytes s(static_cast<std::size_t>(byte(rng)) * 4);
        for (auto& b : s) {
            b = static_cast<std::uint8_t>(byte(rng));
        }
        check(s, failures);
        ++streams;
    }

    std::printf("%d streams, %d mismatches\n", streams, failures);
    return failures == 0 ? 0 : 1;
}
