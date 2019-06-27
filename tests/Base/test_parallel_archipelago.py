# Ignoring some linting rules in tests
# pylint: disable=redefined-outer-name
# pylint: disable=missing-docstring
import pytest
import numpy as np

from bingo.Base.MultipleValues import SinglePointCrossover, \
                                      SinglePointMutation, \
                                      MultipleValueChromosomeGenerator
from bingo.Base.Island import Island
from bingo.Base.MuPlusLambdaEA import MuPlusLambda
from bingo.Base.TournamentSelection import Tournament
from bingo.Base.Evaluation import Evaluation
from bingo.Base.FitnessFunction import FitnessFunction

try:
    from bingo.Base.ParallelArchipelago import ParallelArchipelago
    PAR_ARCH_LOADED = True
except ImportError:
    CppBackend = None
    PAR_ARCH_LOADED = False


POP_SIZE = 5
SELECTION_SIZE = 10
VALUE_LIST_SIZE = 10
OFFSPRING_SIZE = 20
ERROR_TOL = 10e-6


class MultipleValueFitnessFunction(FitnessFunction):
    def __call__(self, individual):
        fitness = np.count_nonzero(individual.values)
        self.eval_count += 1
        return fitness


def generate_three():
    return 3


def generate_two():
    return 2


def generate_one():
    return 1


def generate_zero():
    return 0


def mutation_function():
    return np.random.choice([False, True])


@pytest.fixture
def evol_alg():
    crossover = SinglePointCrossover()
    mutation = SinglePointMutation(mutation_function)
    selection = Tournament(SELECTION_SIZE)
    fitness = MultipleValueFitnessFunction()
    evaluator = Evaluation(fitness)
    return MuPlusLambda(evaluator, selection, crossover, mutation,
                        0.2, 0.4, OFFSPRING_SIZE)


@pytest.fixture
def zero_island(evol_alg):
    generator = MultipleValueChromosomeGenerator(generate_zero,
                                                 VALUE_LIST_SIZE)
    return Island(evol_alg, generator, POP_SIZE)


@pytest.fixture
def one_island(evol_alg):
    generator = MultipleValueChromosomeGenerator(generate_one,
                                                 VALUE_LIST_SIZE)
    return Island(evol_alg, generator, POP_SIZE)


@pytest.fixture
def two_island(evol_alg):
    generator = MultipleValueChromosomeGenerator(generate_two,
                                                 VALUE_LIST_SIZE)
    return Island(evol_alg, generator, POP_SIZE)


@pytest.fixture
def three_island(evol_alg):
    generator = MultipleValueChromosomeGenerator(generate_three,
                                                 VALUE_LIST_SIZE)
    return Island(evol_alg, generator, POP_SIZE)


@pytest.fixture
def island_list(zero_island, one_island, two_island, three_island):
    return [zero_island, one_island, two_island, three_island]


@pytest.fixture
def island(evol_alg):
    generator = MultipleValueChromosomeGenerator(mutation_function,
                                                 VALUE_LIST_SIZE)
    return Island(evol_alg, generator, POP_SIZE)


def test_mpi4py_could_be_imported():
    import mpi4py


@pytest.mark.skipif(not PAR_ARCH_LOADED,
                    reason="ParallelArchipelago import failure. "
                           "Likely due to an import error of mpi4py.")
def test_best_individual_returned(one_island):
    generator = MultipleValueChromosomeGenerator(generate_zero,
                                                 VALUE_LIST_SIZE)
    best_indv = generator()
    one_island.load_population([best_indv], replace=False)
    archipelago = ParallelArchipelago(one_island)
    assert archipelago.get_best_individual().fitness == 0


@pytest.mark.skipif(not PAR_ARCH_LOADED,
                    reason="ParallelArchipelago import failure. "
                           "Likely due to an import error of mpi4py.")
def test_best_fitness_returned(one_island):
    generator = MultipleValueChromosomeGenerator(generate_zero,
                                                 VALUE_LIST_SIZE)
    best_indv = generator()
    one_island.load_population([best_indv], replace=False)
    archipelago = ParallelArchipelago(one_island)
    assert archipelago.get_best_fitness() == 0


@pytest.mark.skipif(not PAR_ARCH_LOADED,
                    reason="ParallelArchipelago import failure. "
                           "Likely due to an import error of mpi4py.")
def test_potential_hof_members(mocker, one_island):
    island_a = mocker.Mock(hall_of_fame=['a'])
    archipelago = ParallelArchipelago(one_island)
    archipelago._island = island_a
    assert archipelago._get_potential_hof_members() == ['a']


@pytest.mark.skipif(not PAR_ARCH_LOADED,
                    reason="ParallelArchipelago import failure. "
                           "Likely due to an import error of mpi4py.")
@pytest.mark.parametrize("sync_freq", [1, 10])
@pytest.mark.parametrize("non_blocking", [True, False])
def test_fitness_eval_count(one_island, sync_freq, non_blocking):
    num_islands = 1
    archipelago = ParallelArchipelago(one_island, sync_frequency=sync_freq,
                                      non_blocking=non_blocking)
    assert archipelago.get_fitness_evaluation_count() == 0
    archipelago.evolve(1)
    if non_blocking:
        expected_evals = num_islands * (POP_SIZE +
                                              sync_freq * OFFSPRING_SIZE)
    else:
        expected_evals = num_islands * (POP_SIZE + OFFSPRING_SIZE)
    assert archipelago.get_fitness_evaluation_count() == expected_evals