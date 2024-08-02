#!/bin/sh

export $(cat .env | xargs)

if [ "$(expr $(date +%s) - $(cat lastRun.epoch))" -lt "$(expr $CF_UPDATER_INTERVAL \* 2)" ]; then 
    exit 0; 
else
    exit 1;
fi