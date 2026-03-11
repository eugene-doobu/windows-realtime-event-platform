#include "simlab/graph.hpp"

namespace simlab {

std::size_t InfluenceGraph::size() const noexcept {
    return offsets.empty() ? 0U : offsets.size() - 1U;
}

}  // namespace simlab

