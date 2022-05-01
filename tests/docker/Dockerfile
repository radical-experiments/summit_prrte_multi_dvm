# RP DOCKERFILE

ARG BASE_IMAGE=exaworks/sdk-base
FROM ${BASE_IMAGE}

RUN mkdir -p /data/db /var/log/mongodb /var/run/mongodb
ENV RADICAL_PILOT_DBURL=mongodb://localhost/rct

# RP stack used for experiments
RUN pip install 'pymongo<4' \
                 radical.gtod==1.6.7 \
                 git+https://github.com/radical-cybertools/radical.utils.git@95aa13ce3ff3e58d0e0764d5a5614e369d6a4c5b \
                 radical.saga==1.8.0 \
                 git+https://github.com/radical-cybertools/radical.pilot.git@634350f8b43bc89bd615c59da99237907b770992 \
                 git+https://github.com/radical-cybertools/radical.analytics.git@2255eae25e2d7cc970fa1a25bcc5b62c4c70905c

# RP stack with the latest releases
#   RUN pip install radical.pilot radical.analytics

COPY tests/docker/resource_local.json tests/docker/agent_sched_exec_sa.json /root/.radical/pilot/configs/
COPY scripts/* .
