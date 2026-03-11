#pragma once

#include <cstddef>
#include <vector>

#include "simlab/types.hpp"

namespace simlab {

struct PopulationState {
    std::vector<float> stance;
    std::vector<float> trust;
    std::vector<float> salience;
    std::vector<float> susceptibility;
    std::vector<float> activity;
    std::vector<float> influence;
    std::vector<GroupId> group_id;

    [[nodiscard]] std::size_t size() const noexcept;
};

}  // namespace simlab

