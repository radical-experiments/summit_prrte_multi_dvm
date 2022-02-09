#!/usr/bin/env python3

__author__    = 'RADICAL-Cybertools Team'
__email__     = 'info@radical-cybertools.org'
__copyright__ = 'Copyright 2022, The RADICAL-Cybertools Team'
__license__   = 'MIT'

import glob
import os

import statistics as st

import matplotlib        as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import radical.analytics as ra
import radical.utils     as ru

COLUMN_WIDTH = 212
PAGE_WIDTH   = 516

plt.style.use(ra.get_mplstyle('radical_mpl'))
mpl.rcParams['text.usetex'] = False
mpl.rcParams['font.serif']  = ['Nimbus Roman Becker No9L']
mpl.rcParams['font.family'] = 'serif'


class Plotter:

    def __init__(self, input_dir, plots_dir, sessions, save=False):

        self.input_dir = input_dir
        self.plots_dir = plots_dir
        self.sessions  = sessions
        self.save      = save
        self.data      = {}

    def load_sessions(self, s_keys=None):
        s_keys = s_keys or list(self.sessions.keys())

        for k in s_keys:

            if k not in self.sessions:
                continue

            session = ra.Session(
                '%s/%s' % (self.input_dir, self.sessions[k]['sid']),
                'radical.pilot')

            self.sessions[k].update({
                'session' : session,
                's_pilots': session.filter(etype='pilot', inplace=False),
                's_tasks' : session.filter(etype='task', inplace=False)})
            self.sessions[k].update({
                'pid'     : self.sessions[k]['s_pilots'].list('uid')[0]})

    def set_prrte_placement_times(self, s_keys=None, with_comments=False):
        s_keys = s_keys or list(self.sessions.keys())
        self.data.clear()

        def _zero_file(_path):
            return not os.path.isfile(_path) or not os.path.getsize(_path)

        comments = ''
        for k in s_keys:

            if k not in self.sessions:
                continue
            sid = self.sessions[k]['sid']

            # set pilot sandbox name as "<sid>.pilot"
            s_path = '%s/%s.pilot/task.*' % (self.input_dir, sid)
            for t_sandbox in glob.glob(s_path):

                if not os.path.isdir(t_sandbox):
                    continue

                f_path = '%s/%s' % (t_sandbox, os.path.basename(t_sandbox))

                # get only tasks that were executed
                f_err_path, f_out_path = '%s.err' % f_path, '%s.out' % f_path
                if _zero_file(f_err_path) or _zero_file(f_out_path):
                    continue

                # check all tasks

                exec_start = exec_stop = app_start = 0.
                with open('%s.prof' % f_path, encoding='utf8') as fd:
                    for line in fd.readlines():
                        if 'task_exec_start' in line:
                            exec_start = float(line.split(',')[0])
                        elif 'app_start' in line:
                            app_start = float(line.split(',')[0])
                        elif 'task_exec_stop' in line:
                            exec_stop = float(line.split(',')[0])

                if not exec_start:
                    continue

                if not app_start:
                    if not exec_stop:
                        continue
                    # adjust task placement duration (subtract sleep duration)
                    with open('%s.sh' % f_path, encoding='utf8') as fd:
                        for line in fd.readlines():
                            if line.startswith('prun'):
                                app_start = exec_stop - int(line.split('"')[3])
                                break

                self.data.setdefault(k, []).append((exec_start,
                                                    app_start - exec_start))

            self.data[k].sort()
            if with_comments:
                d = [x[1] for x in self.data[k]]
                mu_placements = st.mean(d)
                v = (round(mu_placements, 2),
                     round(st.pstdev(d, mu_placements), 2),
                     round(min(d), 2),
                     round(max(d), 2))
                comments += '%s - (mean, std, min, max): %s\n' % (k, str(v))

        if with_comments:
            print(comments)

    def plot_prrte_placement_times(self, upper_threshold=None):
        fig, ax = plt.subplots(figsize=ra.get_plotsize(COLUMN_WIDTH))

        for k, d in self.data.items():
            if upper_threshold:
                d = [x for x in d if x[1] <= upper_threshold]
            _x, _y = zip(*d)
            ax.plot(list(range(1, len(_x) + 1)),
                    _y,
                    label='%(d_nodes)s, %(d_dvms)s' % self.sessions[k])

        #ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
        ax.legend()

        ax.xaxis.set_major_locator(mticker.MaxNLocator(4))

        ax.set_ylabel('Time for task setup by PRRTE (s)')
        ax.set_xlabel('Tasks (ordered by start execution time)')
        plt.tight_layout()
        plt.show()
        if self.save:
            plot_name = 'prrte-placement-times.png'
            fig.savefig(os.path.join(self.plots_dir, plot_name))

    def plot_prrte_placement_time_distr(self, x_label):
        fig, ax = plt.subplots(figsize=ra.get_plotsize(COLUMN_WIDTH))

        plot_data   = []
        plot_xticks = []
        for idx, (k, d) in enumerate(self.data.items()):
            plot_data.append([x[1] for x in d])
            plot_xticks.append((idx + 1, self.sessions[k]['d_dvms']))

        ax.boxplot(plot_data, sym='')
        ax.set_ylabel('Time for task setup by PRRTE (s)')
        ax.set_xlabel(x_label)

        plt.xticks(*zip(*plot_xticks))
        plt.tight_layout()
        plt.show()
        if self.save:
            plot_name = 'prrte-placement-time-distr.png'
            fig.savefig(os.path.join(self.plots_dir, plot_name))

    def plot_concurrency(self, s_keys, x_limits=None):

        s_to_be_loaded = []
        for s_key in s_keys:
            if s_key not in self.sessions:
                return
            elif not self.sessions[s_key].get('session'):
                s_to_be_loaded.append(s_key)

        if s_to_be_loaded:
            self.load_sessions(s_keys=s_to_be_loaded)

        events = {'Task scheduling': [{ru.STATE: 'AGENT_SCHEDULING'},
                                      {ru.EVENT: 'schedule_ok'}],
                  'Task execution' : [{ru.EVENT: 'exec_start'},
                                      {ru.EVENT: 'exec_stop'}]}

        n_subplots = len(s_keys)
        fig, axarr = plt.subplots(1, n_subplots, figsize=(
            ra.get_plotsize(PAGE_WIDTH, subplots=(1, n_subplots))))

        sub_label = 'a'
        for idx, k in enumerate(s_keys):

            if n_subplots > 1:
                ax = axarr[idx]
                ax.set_xlabel(
                    '(%s) %s' % (sub_label, self.sessions[k]['d_dvm_nodes']),
                    labelpad=10)
            else:
                ax = axarr

            p_starttime = self.sessions[k]['s_pilots'].\
                timestamps(event={ru.EVENT: 'bootstrap_0_start'})[0]

            time_series = {e_name: self.sessions[k]['session'].
                           concurrency(event=events[e_name])
                           for e_name in events}

            for e_name in time_series:
                ax.plot(
                    [e[0] - p_starttime for e in time_series[e_name]],
                    [e[1] for e in time_series[e_name]],
                    label=ra.to_latex(e_name))

            if x_limits and isinstance(x_limits, (list, tuple)):
                ax.set_xlim(x_limits)

            sub_label = chr(ord(sub_label) + 1)

        fig.legend(['Task scheduling', 'Task execution'],
                   loc='upper center',
                   bbox_to_anchor=(0.5, 1.02),
                   ncol=2)
        fig.text(0.0, 0.5, 'Number of tasks', va='center', rotation='vertical')
        fig.text(0.5, 0.05, 'Time (s)', ha='center')

        plt.tight_layout()
        plt.show()
        if self.save:
            plot_name = 'concurrency_%s.png' % '_'.join(s_keys)
            fig.savefig(os.path.join(self.plots_dir, plot_name))

    def plot_utilization(self, s_key, x_limits=None):

        if s_key not in self.sessions:
            return
        elif not self.sessions[s_key].get('session'):
            self.load_sessions(s_keys=[s_key])

        sid = self.sessions[s_key]['sid']
        pid = self.sessions[s_key]['pid']

        metrics = [
            ['Bootstrap', ['boot', 'setup_1'], '#c6dbef'],
            ['Warmup', ['warm'], '#f0f0f0'],
            ['Schedule', ['exec_queue', 'exec_prep', 'unschedule'], '#c994c7'],
            ['Exec RP', ['exec_rp', 'exec_sh', 'term_sh', 'term_rp'], '#fdbb84'],
            ['Exec Cmd', ['exec_cmd'], '#e31a1c'],
            ['Cooldown', ['drain'], '#addd8e']
        ]

        exp = ra.Experiment(
            ['%s/%s' % (self.input_dir, self.sessions[s_key]['sid'])],
            stype='radical.pilot')
        # get the start time of each pilot
        p_zeros = ra.get_pilots_zeros(exp)

        fig, axarr = plt.subplots(1, 2, figsize=(
            ra.get_plotsize(PAGE_WIDTH, subplots=(1, 2))))

        sub_label = 'a'
        legend = None
        for idx, rtype in enumerate(['cpu', 'gpu']):

            provided, consumed, stats_abs, stats_rel, info = exp.utilization(
                metrics=metrics, rtype=rtype)

            # generate the subplot with labels
            legend, patches, x, y = ra.get_plot_utilization(
                metrics, consumed, p_zeros[sid][pid], sid)

            # place all the patches, one for each metric, on the axes
            for patch in patches:
                axarr[idx].add_patch(patch)

            if x_limits and isinstance(x_limits, (list, tuple)):
                axarr[idx].set_xlim(x_limits)
            else:
                axarr[idx].set_xlim([x['min'], x['max']])
            axarr[idx].set_ylim([y['min'], y['max']])
            axarr[idx].yaxis.set_major_locator(mticker.MaxNLocator(5))
            axarr[idx].xaxis.set_major_locator(mticker.MaxNLocator(5))

            if rtype == 'cpu':
                # Specific to Summit when using SMT=4 (default)
                axarr[idx].yaxis.set_major_formatter(
                    mticker.FuncFormatter(lambda z, pos: int(z / 4)))

            axarr[idx].set_xlabel('(%s)' % sub_label, labelpad=10)
            sub_label = chr(ord(sub_label) + 1)
            if rtype == 'cpu':
                axarr[idx].set_ylabel('Number of CPU cores')
            elif rtype == 'gpu':
                axarr[idx].set_ylabel('Number of GPUs')
            axarr[idx].set_title(' ')  # placeholder

        fig.legend(legend, [m[0] for m in metrics],
                   loc='upper center',
                   bbox_to_anchor=(0.5, 1.03),
                   ncol=len(metrics))
        fig.text(0.5, 0.05, 'Time (s)', ha='center')

        plt.tight_layout()
        plt.show()
        if self.save:
            plot_name = 'utilization_%s.png' % s_key
            fig.savefig(os.path.join(self.plots_dir, plot_name))

