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

SID_PATH = '../data/rp.session.login5.matitov.018968.0000'
SID_PILOT_PATH = '../data/rp.session.login5.matitov.018968.0000.pilot'

# SID_PATH = '../data/rp.session.login5.matitov.018970.0001'
# SID_PILOT_PATH = '../data/rp.session.login5.matitov.018970.0001.pilot'

# SID_PATH = '../data/rp.session.login4.matitov.019010.0000'
# SID_PILOT_PATH = '../data/rp.session.login4.matitov.019010.0000.pilot'


def get_scheduling_rate():
    prof_file = '%s/pilot.0000/agent_scheduling.0000.prof' % SID_PATH
    check_time_window = 120.  # no new scheduled tasks -> break
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
                endtime = float(line.split(',')[0].strip())
                exec_pending_count += 1

            elif 'unschedule_stop' in line:
                check_time = float(line.split(',')[0].strip())
                if (check_time - endtime) > check_time_window:
                    break

    sched_time = endtime - starttime
    sched_rate = round(exec_pending_count / sched_time, 2)
    return sched_time, exec_pending_count, sched_rate
    # submitted tasks for execution per sec


def get_launching_rate():
    prof_file = '%s/pilot.0000/agent_executing.0000.prof' % SID_PATH
    check_time_window = 120
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
                endtime = float(line.split(',')[0].strip())
                exec_launching_count += 1

            elif 'AGENT_EXECUTING_PENDING' in line:
                check_time = float(line.split(',')[0].strip())
                if (check_time - endtime) > check_time_window:
                    break

    launch_time = endtime - starttime
    launch_rate = round(exec_launching_count / launch_time, 2)
    return launch_time, exec_launching_count, launch_rate
    # launching tasks per sec


# os.path.getsize(path)  # size in bytes
# os.path.getctime(path)
# fileStatsObj = os.stat(filePath)
# modificationTime = time.ctime(fileStatsObj[stat.ST_MTIME])

def get_utilization_per_dvm():

    dvm_info = {}
    for t_sandbox in glob.glob('%s/*/task.*' % SID_PILOT_PATH):
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
        exec_start = exec_stop = 0.
        with open('%s.prof' % f_path, encoding='utf8') as fd:
            for line in fd.readlines():
                if 'task_exec_start' in line:
                    exec_start = float(line.split(',')[0])
                elif 'task_exec_stop' in line:
                    exec_stop = float(line.split(',')[0])
        if not exec_start or not exec_stop:
            continue

        t_info = {'cpus' : 0,
                  'gpus' : 0,
                  'start': exec_start,
                  'exec' : exec_stop - exec_start,
                  'plac' : exec_stop - exec_start}  # task placement to DVM
        # (b) task placement: `os.path.getmtime('%s.out' % f_path) - exec_start`

        # adjust task placement duration (subtract sleep duration)
        with open('%s.sh' % f_path, encoding='utf8') as fd:
            for line in fd.readlines():
                if line.startswith('prun'):
                    t_info['plac'] -= int(line.split('"')[3])
                    break

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
    print('num dvms: %s | num tasks: %s' % (len(dvm_info), total_tasks_count))


# ------------------------------------------------------------------------------
#
if __name__ == '__main__':

    # print(get_scheduling_rate())
    # print(get_launching_rate())
    get_utilization_per_dvm()


# ------------------------------------------------------------------------------
# OBSOLETE CODE
#
def get_scheduling_rate_obsolete(log_file):
    check_time_window = 120.  # no new scheduled tasks -> break
    exec_pending_count = 0
    starttime = endtime = 0.
    with open(log_file, encoding='utf8') as fd:
        while True:
            line = fd.readline()
            if not line:
                break

            if not starttime:
                if 'got task.' in line:  # 'AGENT_SCHEDULING_PENDING' in line
                    starttime = float(line.split(':')[0].strip())
                continue

            if 'put bulk AGENT_EXECUTING_PENDING:' in line:
                endtime = float(line.split(':')[0].strip())
                exec_pending_count += int(line.split(':')[-1].strip())

            elif '=== schedule tasks 0: False' in line:
                check_time = float(line.split(':')[0].strip())
                if (check_time - endtime) > check_time_window:
                    break

    sched_time = endtime - starttime
    sched_rate = round(exec_pending_count / sched_time, 2)
    return sched_time, exec_pending_count, sched_rate
    # submitted tasks for execution per sec
