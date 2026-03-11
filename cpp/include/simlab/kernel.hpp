#pragma once

#include <cstdint>
#include <vector>

#include "simlab/graph.hpp"
#include "simlab/metrics.hpp"
#include "simlab/population.hpp"
#include "simlab/types.hpp"

namespace simlab {

struct ChannelParams {
    ChannelId channel_id = 0;
    float exposure_weight = 0.0F;
    float repost_factor = 0.0F;
    float rumor_decay = 0.0F;
    float trust_penalty = 0.0F;
};

struct Intervention {
    std::uint32_t round_index = 0;
    std::uint32_t kind_id = 0;
    std::vector<GroupId> target_group_ids;
    std::vector<ChannelId> target_channel_ids;
    std::vector<float> narrative_push;
    float trust_delta = 0.0F;
    float stance_delta = 0.0F;
    float salience_delta = 0.0F;
};

struct KernelConfig {
    std::uint32_t rounds = 0;
    std::uint32_t random_seed = 0;
    std::uint32_t narrative_count = 0;
    std::uint32_t max_posts_per_round = 0;
    std::vector<ChannelParams> channels;
    std::vector<Intervention> interventions;
};

SimulationResult run_simulation(
    const PopulationState& initial_state,
    const InfluenceGraph& graph,
    const KernelConfig& config
);

}  // namespace simlab

