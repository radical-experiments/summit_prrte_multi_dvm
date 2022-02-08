#!/usr/bin/env python3

__author__    = 'RADICAL-Cybertools Team'
__email__     = 'info@radical-cybertools.org'
__copyright__ = 'Copyright 2022, The RADICAL-Cybertools Team'
__license__   = 'MIT'

import glob
import json
import os

import statistics as st

GPUS_PER_NODE = 6
BASE_DIR = '../../data/workspace'
LOCAL_CHECK_TIME_WINDOW = 20.
GLOBAL_CHECK_TIME_WINDOW = 120.

# SID = 'rp.session.login5.matitov.018968.0000'  # 1 DVM, 256 nodes
# SID = 'rp.session.login3.matitov.019026.0001'  # 1 DVM, 256 nodes
# SID = 'rp.session.login3.matitov.019026.0002'  # 2 DVMs, 256 nodes
# SID = 'rp.session.login5.matitov.018970.0001'  # 256 DVMs, 256 nodes
# SID = 'rp.session.login4.matitov.019010.0000'  # 8 DVMs, 2048 nodes
# SID = 'rp.session.login3.matitov.019024.0001'  # 2 DVMs, 512 nodes
SID = 'rp.session.login3.matitov.019027.0000'  # 8 DVMs, 1024 nodes


def get_scheduling_rate():
    prof_file = '%s/%s/pilot.0000/agent_scheduling.0000.prof' % (BASE_DIR, SID)
    sched_times = []  # without time gaps due to delayed submission
    sched_tasks = []
    exec_pending_count = 0
    starttime = endtime = 0.
    with open(prof_file, encoding='utf8') as fd:
        while True:
            line = fd.readline()
            if not line:
                break

            if not starttime:
                if 'AGENT_SCHEDULING_PENDING,' in line:
                    starttime = float(line.split(',')[0].strip())
                continue

            if 'put' in line and 'AGENT_EXECUTING_PENDING,' in line:
                exec_pending_count += 1
                check_time = float(line.split(',')[0].strip())
                if endtime and (check_time - endtime) > LOCAL_CHECK_TIME_WINDOW:
                    sched_times.append(endtime - starttime)
                    last_count = 0 if not sched_tasks else sched_tasks[-1]
                    sched_tasks.append(exec_pending_count - last_count - 1)
                    starttime, endtime = check_time, 0.
                    continue
                endtime = check_time

            elif 'unschedule_stop' in line:
                check_time = float(line.split(',')[0].strip())
                if (check_time - endtime) > GLOBAL_CHECK_TIME_WINDOW:
                    sched_times.append(endtime - starttime)
                    last_count = 0 if not sched_tasks else sched_tasks[-1]
                    sched_tasks.append(exec_pending_count - last_count)
                    break  # no new scheduled tasks -> break

    print('rates', [round(sched_tasks[i] / sched_times[i], 2)
                    for i in range(len(sched_times))])
    sched_time = sum(sched_times)
    sched_rate = round(exec_pending_count / sched_time, 2)
    return sched_time, exec_pending_count, sched_rate
    # submitted tasks for execution per sec


def get_launching_rate():
    prof_file = '%s/%s/pilot.0000/agent_executing.0000.prof' % (BASE_DIR, SID)
    launch_times = []
    launch_tasks = []
    exec_launching_count = 0
    starttime = endtime = 0.
    with open(prof_file, encoding='utf8') as fd:
        while True:
            line = fd.readline()
            if not line:
                break

            if not starttime:
                if 'AGENT_EXECUTING_PENDING' in line:
                    starttime = float(line.split(',')[0].strip())
                continue

            if 'exec_ok' in line:
                exec_launching_count += 1
                check_time = float(line.split(',')[0].strip())
                if endtime and (check_time - endtime) > LOCAL_CHECK_TIME_WINDOW:
                    launch_times.append(endtime - starttime)
                    last_count = 0 if not launch_tasks else launch_tasks[-1]
                    launch_tasks.append(exec_launching_count - last_count - 1)
                    starttime, endtime = check_time, 0.
                    continue
                endtime = check_time

            elif 'exec_stop' in line:  # exec_stop
                check_time = float(line.split(',')[0].strip())
                if (check_time - endtime) > GLOBAL_CHECK_TIME_WINDOW:
                    launch_times.append(endtime - starttime)
                    last_count = 0 if not launch_tasks else launch_tasks[-1]
                    launch_tasks.append(exec_launching_count - last_count)
                    break

    print('rates', [round(launch_tasks[i] / launch_times[i], 2)
                    for i in range(len(launch_times))])
    launch_time = sum(launch_times)
    launch_rate = round(exec_launching_count / launch_time, 2)
    return launch_time, exec_launching_count, launch_rate
    # launching tasks per sec


def get_utilization_per_dvm():

    dvm_info = {}
    # set pilot sandbox name as "<sid>.pilot"
    for t_sandbox in glob.glob('%s/%s.pilot/task.*' % (BASE_DIR, SID)):

        if not os.path.isdir(t_sandbox):
            continue

        f_path = '%s/%s' % (t_sandbox, os.path.basename(t_sandbox))

        # get only tasks that were executed
        f_err_path, f_out_path = '%s.err' % f_path, '%s.out' % f_path
        if (os.path.isfile(f_err_path) and not os.path.getsize(f_err_path)) or \
                (os.path.isfile(f_out_path) and not os.path.getsize(f_out_path)):
            continue

        # get only successfully finished tasks
        with open('%s.err' % f_path, encoding='utf8') as fd:
            debug_msgs = ''.join(fd.readlines())
        if 'COMPLETED WITH STATUS 0' not in debug_msgs:
            continue

        # check that task has startup and finish times
        exec_start = app_start = exec_stop = 0.
        with open('%s.prof' % f_path, encoding='utf8') as fd:
            for line in fd.readlines():
                if 'task_exec_start' in line:
                    exec_start = float(line.split(',')[0])
                elif 'app_start' in line:
                    app_start = float(line.split(',')[0])
                elif 'task_exec_stop' in line:
                    exec_stop = float(line.split(',')[0])

        if not exec_start or not exec_stop:
            continue

        if not app_start:
            # adjust task placement duration (subtract sleep duration)
            with open('%s.sh' % f_path, encoding='utf8') as fd:
                for line in fd.readlines():
                    if line.startswith('prun'):
                        app_start = exec_stop - int(line.split('"')[3])
                        break
        # (b) task placement: `os.path.getmtime('%s.out' % f_path) - exec_start`

        t_info = {'cpus' : 0,
                  'gpus' : 0,
                  'start': exec_start,
                  'exec' : exec_stop - exec_start,
                  'plac' : app_start - exec_start}  # task placement to DVM

        # get task data from RP task description
        with open('%s.sl' % f_path, encoding='utf8') as fd:
            t_data = json.loads(fd.read().replace("\'", "\""))
        for rank in t_data['nodes']:
            t_info['cpus'] += len(rank['core_map'][0])
            if rank['gpu_map']:
                t_info['gpus'] += len(rank['gpu_map'])

        # init DVM info and include task info
        dvm_id = int(t_data['partition_id'])
        if dvm_id not in dvm_info:
            # get DVM slots
            hosts_file = '%s/../prrte.%03d.hosts' % (t_sandbox, dvm_id)
            with open(hosts_file, encoding='utf8') as fd:
                hosts = fd.read().splitlines()
            n_hosts = len(hosts)
            # init DVM info
            dvm_info[dvm_id] = {
                'start'    : exec_start,
                'end'      : exec_stop,
                'cpu_slots': n_hosts * int(hosts[0].split('=')[1]),
                'gpu_slots': n_hosts * GPUS_PER_NODE,
                'cpu_util' : 0.,  # RP OVH: place and finish task
                'gpu_util' : 0.,  # RP OVH: place and finish task
                'tasks'    : []
            }
        else:
            if dvm_info[dvm_id]['start'] > exec_start:
                dvm_info[dvm_id]['start'] = exec_start
            if dvm_info[dvm_id]['end'] < exec_stop:
                dvm_info[dvm_id]['end'] = exec_stop

        dvm_info[dvm_id]['cpu_util'] += t_info['exec'] * t_info['cpus']
        dvm_info[dvm_id]['gpu_util'] += t_info['exec'] * t_info['gpus']
        dvm_info[dvm_id]['tasks'].append(t_info)

    output_reformatted = {}
    output_placements = []

    total_tasks_count = 0
    for idx, d in dvm_info.items():
        n_tasks = len(d['tasks'])
        exec_dvm = d['end'] - d['start']
        placements = [t['plac'] for t in d['tasks']]
        mu_placements = st.mean(placements)
        print('%03g - %s - cpu util: %s, gpu util: %s, placement (s): %s %s' % (
            idx,
            n_tasks,
            round(d['cpu_util'] / (d['cpu_slots'] * exec_dvm), 2),
            round(d['gpu_util'] / (d['gpu_slots'] * exec_dvm), 2),
            round(mu_placements, 2),
            round(st.pstdev(placements, mu_placements), 2),
        ))
        total_tasks_count += n_tasks

        output_reformatted[idx] = {
            'tasks': n_tasks,
            'cpu': round(d['cpu_util'] / (d['cpu_slots'] * exec_dvm), 2),
            'gpu': round(d['gpu_util'] / (d['gpu_slots'] * exec_dvm), 2)
        }
        output_placements.extend(placements)
    print('num dvms: %s | num tasks: %s' % (len(dvm_info), total_tasks_count))
    mu_placements = st.mean(output_placements)
    placement_values = (
        round(mu_placements, 2),
        round(st.pstdev(output_placements, mu_placements), 2),
        round(min(output_placements), 2),
        round(max(output_placements), 2)
    )
    print('placement (s) as (mean, std, min, max): ', placement_values)
    print(output_reformatted)
    print(output_placements)


def get_placement_times():

    output_placements = []
    # set pilot sandbox name as "<sid>.pilot"
    for t_sandbox in glob.glob('%s/%s.pilot/task.*' % (BASE_DIR, SID)):

        if not os.path.isdir(t_sandbox):
            continue

        f_path = '%s/%s' % (t_sandbox, os.path.basename(t_sandbox))

        # get only tasks that were executed
        f_err_path, f_out_path = '%s.err' % f_path, '%s.out' % f_path
        if (os.path.isfile(f_err_path) and not os.path.getsize(f_err_path)) or \
                (os.path.isfile(f_out_path) and not os.path.getsize(f_out_path)):
            continue

        # get only FAILED tasks
        with open('%s.err' % f_path, encoding='utf8') as fd:
            debug_msgs = ''.join(fd.readlines())
        if 'COMPLETED WITH STATUS 0' in debug_msgs:
            continue

        # check that task has startup and finish times
        exec_start = app_start = 0.
        with open('%s.prof' % f_path, encoding='utf8') as fd:
            for line in fd.readlines():
                if 'task_exec_start' in line:
                    exec_start = float(line.split(',')[0])
                elif 'app_start' in line:
                    app_start = float(line.split(',')[0])

        if not exec_start and not app_start:
            continue

        output_placements.append(app_start - exec_start)
        print(app_start - exec_start)

    mu_placements = st.mean(output_placements)
    placement_values = (
        round(mu_placements, 2),
        round(st.pstdev(output_placements, mu_placements), 2),
        round(min(output_placements), 2),
        round(max(output_placements), 2)
    )
    print('placement (s) as (mean, std, min, max): ', placement_values)
    print(len(output_placements), output_placements)


# ------------------------------------------------------------------------------
#
if __name__ == '__main__':

    # print(get_scheduling_rate())
    # print(get_launching_rate())
    # get_utilization_per_dvm()
    get_placement_times()

# ------------------------------------------------------------------------------
