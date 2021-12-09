#!/bin/sh

nohup python run_rp.py --nbases 1 --nagents 0 --runtime 75 > OUTPUT 2>&1 </dev/null &
