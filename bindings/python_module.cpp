#include <cstddef>
#include <cstdint>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "simlab/kernel.hpp"

namespace py = pybind11;

namespace {

simlab::PopulationState to_population_state(const py::dict& payload) {
    simlab::PopulationState state{};
    state.stance = payload["stance"].cast<std::vector<float>>();
    state.trust = payload["trust"].cast<std::vector<float>>();
    state.salience = payload["salience"].cast<std::vector<float>>();
    state.susceptibility = payload["susceptibility"].cast<std::vector<float>>();
    state.activity = payload["activity"].cast<std::vector<float>>();
    state.influence = payload["influence"].cast<std::vector<float>>();
    state.group_id = payload["group_id"].cast<std::vector<simlab::GroupId>>();
    return state;
}

simlab::InfluenceGraph to_graph(const py::dict& payload) {
    simlab::InfluenceGraph graph{};
    graph.offsets = payload["offsets"].cast<std::vector<simlab::AgentIndex>>();
    graph.targets = payload["targets"].cast<std::vector<simlab::AgentIndex>>();
    graph.weights = payload["weights"].cast<std::vector<float>>();
    return graph;
}

simlab::KernelConfig to_config(const py::dict& payload) {
    simlab::KernelConfig config{};
    config.rounds = payload["rounds"].cast<std::uint32_t>();
    config.random_seed = payload["random_seed"].cast<std::uint32_t>();
    config.narrative_count = payload["narrative_count"].cast<std::uint32_t>();
    config.max_posts_per_round = payload["max_posts_per_round"].cast<std::uint32_t>();

    for (const py::handle& item : payload["channels"].cast<py::list>()) {
        const py::dict channel = py::reinterpret_borrow<py::dict>(item);
        config.channels.push_back(simlab::ChannelParams{
            .channel_id = channel["channel_id"].cast<simlab::ChannelId>(),
            .exposure_weight = channel["exposure_weight"].cast<float>(),
            .repost_factor = channel["repost_factor"].cast<float>(),
            .rumor_decay = channel["rumor_decay"].cast<float>(),
            .trust_penalty = channel["trust_penalty"].cast<float>(),
        });
    }

    for (const py::handle& item : payload["interventions"].cast<py::list>()) {
        const py::dict intervention = py::reinterpret_borrow<py::dict>(item);
        config.interventions.push_back(simlab::Intervention{
            .round_index = intervention["round_index"].cast<std::uint32_t>(),
            .kind_id = intervention["kind_id"].cast<std::uint32_t>(),
            .target_group_ids = intervention["target_group_ids"].cast<std::vector<simlab::GroupId>>(),
            .target_channel_ids = intervention["target_channel_ids"].cast<std::vector<simlab::ChannelId>>(),
            .narrative_push = intervention["narrative_push"].cast<std::vector<float>>(),
            .trust_delta = intervention["trust_delta"].cast<float>(),
            .stance_delta = intervention["stance_delta"].cast<float>(),
            .salience_delta = intervention["salience_delta"].cast<float>(),
        });
    }

    return config;
}

py::dict to_python_result(const simlab::SimulationResult& result) {
    py::list round_metrics;
    for (const simlab::RoundMetrics& metric : result.round_metrics) {
        py::dict item;
        item["round_index"] = metric.round_index;
        item["total_exposures"] = metric.total_exposures;
        item["total_posts"] = metric.total_posts;
        item["mean_stance"] = metric.mean_stance;
        item["mean_trust"] = metric.mean_trust;
        item["mean_salience"] = metric.mean_salience;
        item["rumor_share"] = metric.rumor_share;
        item["clarification_share"] = metric.clarification_share;
        round_metrics.append(item);
    }

    py::dict payload;
    py::dict final_state;
    final_state["stance"] = result.final_state.stance;
    final_state["trust"] = result.final_state.trust;
    final_state["salience"] = result.final_state.salience;
    final_state["susceptibility"] = result.final_state.susceptibility;
    final_state["activity"] = result.final_state.activity;
    final_state["influence"] = result.final_state.influence;
    final_state["group_id"] = result.final_state.group_id;

    payload["final_state"] = final_state;
    payload["round_metrics"] = round_metrics;
    return payload;
}

py::dict run_simulation_py(const py::dict& initial_state, const py::dict& graph, const py::dict& config) {
    const simlab::PopulationState native_state = to_population_state(initial_state);
    const simlab::InfluenceGraph native_graph = to_graph(graph);
    const simlab::KernelConfig native_config = to_config(config);
    const simlab::SimulationResult result = simlab::run_simulation(native_state, native_graph, native_config);
    return to_python_result(result);
}

}  // namespace

PYBIND11_MODULE(gan_simlab_cpp, module) {
    module.doc() = "Minimal Python binding for the GAN SimLab C++ kernel.";
    module.def("version", []() { return "0.1.0"; });
    module.def(
        "run_simulation",
        &run_simulation_py,
        py::arg("initial_state"),
        py::arg("graph"),
        py::arg("config")
    );
}
