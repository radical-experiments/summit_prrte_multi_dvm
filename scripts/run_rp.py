#!/usr/bin/env python3

__author__    = 'RADICAL-Cybertools Team'
__email__     = 'info@radical-cybertools.org'
__copyright__ = 'Copyright 2021-2022, The RADICAL-Cybertools Team'
__license__   = 'MIT'

import argparse
import os

from random import randint

import radical.pilot as rp

RESOURCE_NAMES = {
    'local' : {'resource': 'local.summit_sim',
               'project' : None,
               'queue'   : None},
    'remote': {'resource': 'ornl.summit_prte',
               'project' : 'GEO111',  # original project used: CHM155_003
               'queue'   : 'debug'}
}

SMT_LEVEL            = 4
N_CORES_PER_NODE     = 42
N_CPUS_PER_NODE      = N_CORES_PER_NODE * SMT_LEVEL
N_GPUS_PER_NODE      = 6

N_EXEC_NODES_MAIN    = 248  # "main" (i.e., active) nodes
N_EXEC_NODES_SUPP    = 8    # "supplementary" nodes (~3%)
N_EXEC_NODES_BASE    = N_EXEC_NODES_MAIN + N_EXEC_NODES_SUPP

CPUS_RANGE_S         = [ 1, 21]     # up to one socket size
CPUS_RANGE_L         = [42, 84]     # 2-4 times of socket size
TASK_RUNTIME_RANGE_S = [480,  600]  # 08-10min (4x)
TASK_RUNTIME_RANGE_L = [960, 1200]  # 16-20min (2x)
N_GENERATIONS_S      = 4
N_GENERATIONS_L      = 2

N_TASKS_BASE         = 8200         # total number of tasks per 256 nodes
N_TASKS_L_RATIO      = .1           # ratio of "large" tasks


def get_task_cpus_per_generation(n_tasks, n_generations, n_slots,
                                 runtime_range, cpus_range=None):
    output = []
    avg_n_cpus = int((n_slots * n_generations) / n_tasks)
    cpus_range = cpus_range or [avg_n_cpus - 1, avg_n_cpus + 1]
    if avg_n_cpus < 1:
        raise RuntimeError('AVG value (%s) not set' % avg_n_cpus)
    elif not (cpus_range[0] < avg_n_cpus < cpus_range[1]):
        raise RuntimeError('AVG value (%s) not within the range' % avg_n_cpus)
    elif not cpus_range[0]:
        cpus_range[0] = 1
    var = min(cpus_range[1] - avg_n_cpus, avg_n_cpus - cpus_range[0])
    cpus_range = [avg_n_cpus - var, avg_n_cpus + var]
    print('# tasks: %s ' % n_tasks,
          'avg cpus: %s ' % avg_n_cpus,
          'cpus range: %s' % cpus_range)
    output.extend([[randint(*cpus_range), 0, randint(*runtime_range)]
                   for _ in range(n_tasks)])
    return output


def get_task_cpus_large(n_tasks, ratio_l, n_bases):
    output = []
    n_tasks_l = int(n_tasks * ratio_l)
    tasks_l = sorted(get_task_cpus_per_generation(
        n_tasks=n_tasks_l,
        n_generations=N_GENERATIONS_L,
        n_slots=(SMT_LEVEL - 1) * N_CORES_PER_NODE * N_EXEC_NODES_MAIN,
        runtime_range=TASK_RUNTIME_RANGE_L,
        cpus_range=CPUS_RANGE_L), reverse=True, key=lambda x: x[0])
    # set GPUs to the largest tasks
    n_tasks_with_gpus = N_EXEC_NODES_MAIN * N_GENERATIONS_L
    for idx in range(n_tasks_with_gpus):
        tasks_l[idx][1] = N_GPUS_PER_NODE
    # set tasks with GPUs first
    output.extend(tasks_l[:n_tasks_with_gpus] * n_bases)
    output.extend(tasks_l[n_tasks_with_gpus:] * n_bases)
    return output


def get_task_cpus_small(n_tasks, ratio_l, n_bases):
    output = []
    n_tasks_s = n_tasks - int(n_tasks * ratio_l)
    output.extend(get_task_cpus_per_generation(
        n_tasks=n_tasks_s,
        n_generations=N_GENERATIONS_S,
        n_slots=N_CORES_PER_NODE * N_EXEC_NODES_MAIN,
        runtime_range=TASK_RUNTIME_RANGE_S,
        cpus_range=CPUS_RANGE_S) * n_bases)
    return output


def generate_task_description(cpus, gpus, runtime):
    return rp.TaskDescription({'cpu_processes': 1,
                               'cpu_threads'  : cpus,
                               'gpu_processes': gpus,
                               'executable'   : './hello_rp.sh',
                               'arguments'    : [runtime],
                               'input_staging': [
                                   {'source': 'pilot:///hello_rp.sh',
                                    'target': 'task:///hello_rp.sh',
                                    'action': rp.LINK}]})


def main():

    # environment setup
    os.environ['RADICAL_LOG_LVL'] = 'DEBUG'
    os.environ['RADICAL_PROFILE'] = 'TRUE'

    # input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--local', action='store_true',
                        help='Run experiment locally', default=False)
    parser.add_argument('-b', '--nbases', type=int, choices=[1, 2, 4, 8],
                        help='Number to multiply base number of nodes',
                        default=1)
    parser.add_argument('-a', '--nagents', type=int,
                        help='Number of nodes for sub-agents', default=0)
    parser.add_argument('-t', '--runtime', type=int,
                        help='Experiment runtime', default=60)
    opts = parser.parse_args()

    # pilot settings definition
    n_nodes = (N_EXEC_NODES_BASE * opts.nbases) + opts.nagents
    pd = {'cores'        : n_nodes * N_CPUS_PER_NODE,
          'gpus'         : n_nodes * N_GPUS_PER_NODE,
          'runtime'      : opts.runtime,
          'access_schema': 'local',
          'input_staging': ['hello_rp.sh']}
    pd.update(RESOURCE_NAMES['local' if opts.local else 'remote'])

    # run RP
    session = rp.Session()
    try:
        pmgr = rp.PilotManager(session=session)
        tmgr = rp.TaskManager(session=session)
        tmgr.add_pilots(pmgr.submit_pilots(rp.PilotDescription(pd)))

        # submit "large" tasks first
        tds = []
        for _cpus, _gpus, _runtime in \
                get_task_cpus_large(N_TASKS_BASE, N_TASKS_L_RATIO, opts.nbases):
            tds.append(generate_task_description(_cpus, _gpus, _runtime))
        tmgr.submit_tasks(tds)
        # wait until all "large" tasks reach the scheduler
        tmgr.wait_tasks(state=rp.AGENT_SCHEDULING)

        # submit "small" tasks (after "large" tasks are scheduled)
        tds = []
        for _cpus, _gpus, _runtime in \
                get_task_cpus_small(N_TASKS_BASE, N_TASKS_L_RATIO, opts.nbases):
            tds.append(generate_task_description(_cpus, _gpus, _runtime))
        tmgr.submit_tasks(tds)
        tmgr.wait_tasks()
    finally:
        session.close(download=True)


if __name__ == '__main__':
    main()
