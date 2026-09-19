// libFuzzer entry point. Any difference between the C and C++ parsers stops the run.
#include <cstdlib>

#include "differential.hpp"

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
    if (!diff::same_result(data, size)) {
        std::abort();
    }
    return 0;
}
