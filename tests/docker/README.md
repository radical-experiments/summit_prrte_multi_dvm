# Dockerfile to test experiment setup locally

## Build RP container
```
cd summit_prrte_multi_dvm
docker build --no-cache -t rp_summit_test -f tests/docker/Dockerfile .
```
RCT stack (called with `radical-stack`) is the following
```
  radical.analytics    : 1.6.7-v0.1.6.7-51-g2255eae@devel
  radical.gtod         : 1.6.7
  radical.pilot        : 1.9.0-v1.9.0-5-g634350f8b@fix-scheduler
  radical.saga         : 1.8.0
  radical.utils        : 1.8.2-v1.8.2-9-g95aa13c@fix-scheduler
```

## Run RP container
```
docker run --rm -it --oom-kill-disable --memory="10g" --memory-swap="-1" rp_summit_test bash
```
Initiate MongoDB
```
mongod --fork --logpath /tmp/mongodb.log
```
Run RP application
```
# 256 nodes, local run
python run_rp.py --local --nbases 1 --runtime 60
```
Create plots with RA
```
python run_ra.py --sid <sid>
```
