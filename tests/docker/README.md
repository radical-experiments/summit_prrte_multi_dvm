# Dockerfile to test experiment setup locally

## Build RP container
```
cd summit_prrte_multi_dvm
docker build --no-cache -t rp_summit_test -f tests/docker/Dockerfile .
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
