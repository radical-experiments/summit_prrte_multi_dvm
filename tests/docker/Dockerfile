# RP DOCKERFILE

ARG BASE_IMAGE=exaworks/sdk-base
FROM ${BASE_IMAGE}

RUN mkdir -p /data/db /var/log/mongodb /var/run/mongodb
ENV RADICAL_PILOT_DBURL=mongodb://localhost/rct

# RP install (temporary branch with fixed RP Scheduler)
RUN pip install git+https://github.com/radical-cybertools/radical.utils.git@fix/scheduler \
                git+https://github.com/radical-cybertools/radical.pilot.git@fix/scheduler \
                git+https://github.com/radical-cybertools/radical.analytics.git@devel

COPY tests/docker/resource_local.json tests/docker/agent_sched_exec_sa.json /root/.radical/pilot/configs/
COPY scripts/* .
