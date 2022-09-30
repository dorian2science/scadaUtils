#!/usr/bin/env python
# coding: utf-8
from sylfenUtils import comUtils
import os,sys,re, pandas as pd,numpy as np
import importlib
importlib.reload(comUtils)

### load the conf
from test_conf import Conf_dummy
conf=Conf_dummy()

from sylfenUtils.Simulators import SimulatorModeBus
dummy_simulator=SimulatorModeBus(
    port=conf.port_dummy,
    modbus_map=conf.dummy_modbus_map,
    bo=conf.byte_order,
    wo=conf.word_order
)

dummy_simulator.start()
