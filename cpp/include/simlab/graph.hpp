#pragma once

#include <cstddef>
#include <vector>

#include "simlab/types.hpp"

namespace simlab {

struct InfluenceGraph {
    std::vector<AgentIndex> offsets;
    std::vector<AgentIndex> targets;
    std::vector<float> weights;

    [[nodiscard]] std::size_t size() const noexcept;
};

}  // namespace simlab

