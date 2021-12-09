#!/usr/bin/env python3

__author__    = 'RADICAL-Cybertools Team'
__email__     = 'info@radical-cybertools.org'
__copyright__ = 'Copyright 2021, The RADICAL-Cybertools Team'
__license__   = 'MIT'

"""
Minimal RP application to check DVM startup with many nodes 
(DVM count should be updated within resource config).
"""

import radical.pilot as rp

SMT_LEVEL        = 4
N_CORES_PER_NODE = 42
N_CPUS_PER_NODE  = N_CORES_PER_NODE * SMT_LEVEL
N_NODES          = 256

PILOT_DESCRIPTION = {
    'resource'     : 'ornl.summit_prte',
    'project'      : 'CHM155_003',
    'queue'        : 'debug',
    'cores'        : N_CPUS_PER_NODE * N_NODES,
    'runtime'      : 10,
    'access_schema': 'local'
}


def main():

    # run RP
    session = rp.Session()
    try:
        pmgr = rp.PilotManager(session=session)
        tmgr = rp.TaskManager(session=session)
        tmgr.add_pilots(
            pmgr.submit_pilots(rp.PilotDescription(PILOT_DESCRIPTION)))
        # only one task to have some payload
        tmgr.submit_tasks(
            rp.TaskDescription({'cpu_processes': 1,
                                'cpu_threads'  : 1,
                                'executable'   : '/usr/bin/date'}))
        tmgr.wait_tasks()
    finally:
        session.close(download=True)


if __name__ == '__main__':
    main()
