#include "simlab/kernel.hpp"

#include <algorithm>
#include <numeric>
#include <unordered_set>
#include <vector>

namespace simlab {

namespace {

float clamp(const float value, const float lower, const float upper) {
    return std::max(lower, std::min(upper, value));
}

float clamp01(const float value) {
    return clamp(value, 0.0F, 1.0F);
}

float average_channel_exposure(const std::vector<ChannelParams>& channels) {
    if (channels.empty()) {
        return 1.0F;
    }

    float total = 0.0F;
    for (const ChannelParams& channel : channels) {
        total += channel.exposure_weight;
    }
    return total / static_cast<float>(channels.size());
}

float average_channel_trust_penalty(const std::vector<ChannelParams>& channels) {
    if (channels.empty()) {
        return 0.0F;
    }

    float total = 0.0F;
    for (const ChannelParams& channel : channels) {
        total += channel.trust_penalty;
    }
    return total / static_cast<float>(channels.size());
}

bool applies_to_group(const Intervention& intervention, const GroupId group_id) {
    if (intervention.target_group_ids.empty()) {
        return true;
    }

    return std::find(
               intervention.target_group_ids.begin(),
               intervention.target_group_ids.end(),
               group_id
           ) != intervention.target_group_ids.end();
}

float sum_vector(const std::vector<float>& values) {
    return std::accumulate(values.begin(), values.end(), 0.0F);
}

RoundMetrics build_round_metrics(
    const PopulationState& state,
    const std::uint32_t round_index,
    const std::uint32_t total_exposures,
    const std::uint32_t total_posts,
    const float rumor_share,
    const float clarification_share
) {
    RoundMetrics metrics{};
    metrics.round_index = round_index;
    metrics.total_exposures = total_exposures;
    metrics.total_posts = total_posts;
    metrics.mean_stance = state.stance.empty() ? 0.0F : sum_vector(state.stance) / static_cast<float>(state.stance.size());
    metrics.mean_trust = state.trust.empty() ? 0.0F : sum_vector(state.trust) / static_cast<float>(state.trust.size());
    metrics.mean_salience =
        state.salience.empty() ? 0.0F : sum_vector(state.salience) / static_cast<float>(state.salience.size());
    metrics.rumor_share = clamp01(rumor_share);
    metrics.clarification_share = clamp01(clarification_share);
    return metrics;
}

}  // namespace

SimulationResult run_simulation(
    const PopulationState& initial_state,
    const InfluenceGraph& graph,
    const KernelConfig& config
) {
    SimulationResult result{};
    result.final_state = initial_state;
    result.round_metrics.reserve(config.rounds);

    const auto agent_count = result.final_state.size();
    const float exposure_weight = average_channel_exposure(config.channels);
    const float trust_penalty = average_channel_trust_penalty(config.channels);

    for (std::uint32_t round_index = 0; round_index < config.rounds; ++round_index) {
        std::vector<float> exposure_signal(agent_count, 0.0F);
        std::vector<float> stance_acc(agent_count, 0.0F);
        std::vector<float> weight_acc(agent_count, 0.0F);
        std::vector<float> intervention_stance(agent_count, 0.0F);
        std::vector<float> intervention_trust(agent_count, 0.0F);
        std::vector<float> intervention_salience(agent_count, 0.0F);

        std::uint32_t total_exposures = 0;
        std::uint32_t total_posts = 0;

        for (std::size_t source = 0; source < agent_count; ++source) {
            const float emission = clamp01(
                result.final_state.activity[source] * (0.5F + (result.final_state.salience[source] * 0.5F))
            );
            if (emission > 0.55F) {
                ++total_posts;
            }

            const auto edge_begin = graph.offsets.empty() ? 0U : graph.offsets[source];
            const auto edge_end = graph.offsets.empty() ? 0U : graph.offsets[source + 1U];
            for (AgentIndex edge_index = edge_begin; edge_index < edge_end; ++edge_index) {
                const AgentIndex target = graph.targets[edge_index];
                const float weight = graph.weights[edge_index];
                const float influence_weight =
                    weight * (0.25F + (result.final_state.influence[source] * 0.75F));

                exposure_signal[target] += emission * influence_weight;
                stance_acc[target] += result.final_state.stance[source] * influence_weight;
                weight_acc[target] += influence_weight;
                ++total_exposures;
            }
        }

        float rumor_share = 0.0F;
        float clarification_share = 0.0F;

        for (const Intervention& intervention : config.interventions) {
            if (intervention.round_index != round_index) {
                continue;
            }

            const float narrative_strength = sum_vector(intervention.narrative_push);
            if (intervention.kind_id == 3U) {
                rumor_share += narrative_strength;
            } else if (intervention.kind_id == 1U) {
                clarification_share += narrative_strength;
            }

            for (std::size_t agent_index = 0; agent_index < agent_count; ++agent_index) {
                if (!applies_to_group(intervention, result.final_state.group_id[agent_index])) {
                    continue;
                }
                intervention_stance[agent_index] += intervention.stance_delta;
                intervention_trust[agent_index] += intervention.trust_delta;
                intervention_salience[agent_index] += intervention.salience_delta;
            }
        }

        for (std::size_t agent_index = 0; agent_index < agent_count; ++agent_index) {
            const float current_stance = result.final_state.stance[agent_index];
            const float neighborhood_mean = weight_acc[agent_index] > 0.0F
                ? stance_acc[agent_index] / weight_acc[agent_index]
                : current_stance;
            const float exposure_norm = clamp01(exposure_signal[agent_index] * 0.25F * exposure_weight);
            const float stance_delta =
                (neighborhood_mean - current_stance)
                * result.final_state.susceptibility[agent_index]
                * (0.10F + (result.final_state.salience[agent_index] * 0.10F));
            const float trust_drag = trust_penalty * exposure_norm * 0.05F;

            result.final_state.stance[agent_index] =
                clamp(current_stance + stance_delta + intervention_stance[agent_index], -1.0F, 1.0F);
            result.final_state.trust[agent_index] = clamp01(
                result.final_state.trust[agent_index] + intervention_trust[agent_index] - trust_drag
            );
            result.final_state.salience[agent_index] = clamp01(
                result.final_state.salience[agent_index]
                + (0.10F * exposure_norm)
                + intervention_salience[agent_index]
                - 0.02F
            );
        }

        result.round_metrics.push_back(build_round_metrics(
            result.final_state,
            round_index,
            total_exposures,
            total_posts,
            rumor_share,
            clarification_share
        ));
    }

    return result;
}

}  // namespace simlab
