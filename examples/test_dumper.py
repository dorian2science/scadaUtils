from sylfenUtils import comUtils
import os,sys,re, pandas as pd,numpy as np
import importlib
importlib.reload(comUtils)

### load the conf
from test_conf import Conf_dummy
conf=Conf_dummy()

from sylfenUtils.comUtils import ModbusDevice
dummy_device=ModbusDevice(
    ip='localhost',
    port=conf.port_dummy,
    device_name='dummy_device',
    dfplc=conf.PLCS['dummy'],
    modbus_map=conf.dummy_modbus_map,
    bo=conf.byte_order,
    wo=conf.word_order,
    freq=conf.freq
)

### DUMPER ---------------
from sylfenUtils.comUtils import SuperDumper_daily
DEVICES = {
    'dummy_device':dummy_device,
}
log_file_name=None ## if you want either to have the information in the console use None.
dumper=SuperDumper_daily(
    DEVICES,
    conf.FOLDERPKL,
    conf.DB_PARAMETERS,
    conf.PARKING_TIME,
    dbTable=conf.DB_TABLE,
    tz_record=conf.TZ_RECORD,
    log_file=log_file_name
)

def test_dumper():
    dummy_device.connectDevice()
    ### read single register
    dummy_device.quick_modbus_single_register_decoder(10,2,'float32',unit=1);
    tags=dummy_device.dfplc.index.to_list()
    dummy_device.connectDevice()
    ### test collect
    data=dummy_device.collectData('CET',tags)## do not forget to precise the time zome
    ### test insertion
    dummy_device.insert_intodb(conf.DB_PARAMETERS,conf.DB_TABLE,'CET',tags)
    ### check that the db is full with data
    comUtils.read_db(conf.DB_PARAMETERS,conf.DB_TABLE)

dumper.start_dumping()
