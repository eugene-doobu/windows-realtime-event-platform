#pragma once

#include <cstdint>
#include <vector>

#include "simlab/population.hpp"

namespace simlab {

struct RoundMetrics {
    std::uint32_t round_index = 0;
    std::uint32_t total_exposures = 0;
    std::uint32_t total_posts = 0;
    float mean_stance = 0.0F;
    float mean_trust = 0.0F;
    float mean_salience = 0.0F;
    float rumor_share = 0.0F;
    float clarification_share = 0.0F;
};

struct SimulationResult {
    PopulationState final_state;
    std::vector<RoundMetrics> round_metrics;
};

}  // namespace simlab

