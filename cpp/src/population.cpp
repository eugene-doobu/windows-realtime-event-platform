#include "simlab/population.hpp"

namespace simlab {

std::size_t PopulationState::size() const noexcept {
    return stance.size();
}

}  // namespace simlab

