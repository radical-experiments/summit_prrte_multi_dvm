#!/usr/bin/env python3

__author__    = 'RADICAL-Cybertools Team'
__email__     = 'info@radical-cybertools.org'
__copyright__ = 'Copyright 2021, The RADICAL-Cybertools Team'
__license__   = 'MIT'

import argparse
import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import radical.analytics as ra
import radical.utils     as ru

WORK_DIR = os.path.dirname(__file__)


def concurrency_plot(sid_path, plot_name_base):

    session = ra.Session(sid_path, 'radical.pilot')

    events = {'Task scheduling': [{ru.STATE: 'AGENT_SCHEDULING'},
                                  {ru.EVENT: 'schedule_ok'}],
              'Task execution' : [{ru.EVENT: 'exec_start'},
                                  {ru.EVENT: 'exec_stop'}]}

    time_series = {e: session.concurrency(event=events[e]) for e in events}
    fig, ax = plt.subplots(figsize=(ra.get_plotsize(500)))
    for name in time_series:
        zero = min([e[0] for e in time_series[name]])
        ax.plot([e[0] - zero for e in time_series[name]],
                [e[1] for e in time_series[name]],
                label=ra.to_latex(name))

    ax.legend(ncol=2, loc='upper left', bbox_to_anchor=(-0.15, 1.15))
    ax.set_ylabel('Number of tasks')
    ax.set_xlabel('Time (s)')

    fig.savefig(os.path.join(WORK_DIR, '%s.concurrency.png' % plot_name_base))


def utilization_plot(sid_path, plot_name_base, rtype=None):

    rtype = rtype or 'cpu'
    sid = os.path.basename(sid_path)

    s = {'s': ra.Session(sid_path, 'radical.pilot')}

    s.update({'p'      : s['s'].filter(etype='pilot', inplace=False),
              't'      : s['s'].filter(etype='task', inplace=False)})
    s.update({'pid'    : s['p'].list('uid')[0]})
    s.update({'n_tasks': len(s['t'].get()),
              'n_cores': s['p'].get(uid=s['pid'])[0].description['cores'],
              'n_gpus' : s['p'].get(uid=s['pid'])[0].description['gpus'],
              'cores_per_node': s['p'].get(uid=s['pid'])[0].
                  cfg['resource_details']['rm_info']['cores_per_node']})
    s.update({'n_nodes': int(s['n_cores'] / s['cores_per_node'])})

    metrics = [
        ['Bootstrap', ['boot', 'setup_1'], '#c6dbef'],
        ['Warmup',    ['warm'], '#f0f0f0'],
        ['Schedule',  ['exec_queue', 'exec_prep', 'unschedule'], '#c994c7'],
        ['Exec RP',   ['exec_rp', 'exec_sh', 'term_sh', 'term_rp'], '#fdbb84'],
        ['Exec Cmd',  ['exec_cmd'], '#e31a1c'],
        ['Cooldown',  ['drain'], '#addd8e']
    ]

    exp = ra.Experiment([sid_path], stype='radical.pilot')
    provided, consumed, stats_abs, stats_rel, info = exp.utilization(
        metrics=metrics, rtype=rtype)

    # get the start time of each pilot
    p_zeros = ra.get_pilots_zeros(exp)
    fig, ax = plt.subplots(figsize=(ra.get_plotsize(500)))

    # generate the subplot with labels
    legend, patches, x, y = ra.get_plot_utilization(
        metrics, consumed, p_zeros[sid][s['pid']], sid)

    # place all the patches, one for each metric, on the axes
    for patch in patches:
        ax.add_patch(patch)

    ax.set_title(
        '%s Tasks - %s Nodes' % (s['n_tasks'], s['n_nodes']))
    ax.set_xlim([x['min'], x['max']])
    ax.set_ylim([y['min'], y['max']])
    ax.yaxis.set_major_locator(mticker.MaxNLocator(5))
    ax.xaxis.set_major_locator(mticker.MaxNLocator(5))

    if rtype == 'cpu':
        # Specific to Summit when using SMT=4 (default)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda z, pos: int(z / 4)))

    ax.legend(legend, [m[0] for m in metrics],
              loc='upper center', bbox_to_anchor=(0.45, 1.175), ncol=6)
    if rtype == 'cpu':
        ax.set_ylabel('Number of CPU cores')
    elif rtype == 'gpu':
        ax.set_ylabel('Number of GPUs')
    ax.set_xlabel('Time (s)')

    # save plot to PNG file
    fig.savefig(os.path.join(
        WORK_DIR, '%s.%s.utilization.png' % (plot_name_base, rtype)))


def main():

    # input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sid', help='Session ID', required=True)
    opts = parser.parse_args()

    sid_path = os.path.join(WORK_DIR, opts.sid)
    plot_name_base = '.'.join(opts.sid.rsplit('.', 2)[1:])

    # run RA
    concurrency_plot(sid_path, plot_name_base)
    utilization_plot(sid_path, plot_name_base, 'cpu')
    utilization_plot(sid_path, plot_name_base, 'gpu')


if __name__ == '__main__':
    main()
