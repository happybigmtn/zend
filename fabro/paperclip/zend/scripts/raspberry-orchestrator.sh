#!/usr/bin/env bash
set -euo pipefail
cd '/home/r/coding/zend'
'/home/r/.cache/codex/targets/019d029d-2246-7c53-9655-32024c2c3d01/debug/raspberry' autodev --manifest '/home/r/coding/zend/fabro/programs/zend.yaml' --fabro-bin '/home/r/.cache/codex/targets/019d029d-2246-7c53-9655-32024c2c3d01/debug/fabro' --max-cycles 1 --poll-interval-ms 1 --evolve-every-seconds 0
