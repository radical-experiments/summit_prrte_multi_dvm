
import glob
import os

# current - 6426.77; extrapolated exec_stop: 8890.28
# s_key = n1024_dvm8_r2


class Plotter:

    def __init__(self, input_dir, plots_dir, sessions, save=False):

        self.input_dir = input_dir
        self.plots_dir = plots_dir
        self.sessions  = sessions
        self.save      = save
        self.data      = {}

    def get_extrapolated_exec_stop_time(self, s_key):

        def _zero_file(_path):
            return not os.path.isfile(_path) or not os.path.getsize(_path)

        exec_stop_times = []
        count = 0
        sid = self.sessions[s_key]['sid']

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

            app_start = exec_stop = 0.
            with open('%s.prof' % f_path, encoding='utf8') as fd:
                for line in fd.readlines():
                    if 'app_start' in line:
                        app_start = float(line.split(',')[0])
                    elif 'task_exec_stop' in line:
                        exec_stop = float(line.split(',')[0])

            if exec_stop:
                exec_stop_times.append(exec_stop)
                continue
            elif not app_start:
                continue

            with open('%s.sh' % f_path, encoding='utf8') as fd:
                for line in fd.readlines():
                    if line.startswith('prun'):
                        exec_stop = app_start + int(line.split('"')[3])
                        print(exec_stop - 1645116655.9211390)
                        count += 1
                        break

            if exec_stop: #and exec_stop < 1645121155.921139:
                exec_stop_times.append(exec_stop)

        return max(exec_stop_times), count


if __name__ == '__main__':
    sessions = {
        'n1024_dvm8_r2': {
            'sid': 'rp.session.login3.matitov.019040.0000',
            'd_full': '1024 nodes + 4 nodes for sub-agents, 8 DVMs',
            'd_nodes': '1024 nodes',
            'd_dvms': '8 DVMs',
            'd_dvm_nodes': '128 nodes per DVM'}
    }
    p = Plotter(input_dir='../../data/workspace',
                plots_dir='../../plots',
                sessions=sessions, save=True)

    print(p.get_extrapolated_exec_stop_time(s_key='n1024_dvm8_r2'))
