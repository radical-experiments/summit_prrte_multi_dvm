#!/bin/sh

module load python/3.7-anaconda3
eval "$(conda shell.posix hook)"
conda activate /ccs/home/$USER/.conda/envs/rp

export RADICAL_PILOT_DBURL=""
export RADICAL_LOG_LVL=DEBUG
export RADICAL_PROFILE=TRUE
