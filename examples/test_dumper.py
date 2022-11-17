from sylfenUtils.comUtils import ModbusDevice
import os,pandas as pd
from test_confGenerator import conf as dummy_conf
####################
# SUGGESTION MODIF #
####################
##### AUTOMATIC CREATION OF DEVICES WITH DEVICES TABLE ######
dummy_device=ModbusDevice(ip='localhost',port=3503,device_name='dummy_device',
    dfplc=dummy_conf.dummy_df_plc,modbus_map=dummy_conf.dummy_modbus_map,bo='big',wo='big',freq=2)

##### start simulator
from sylfenUtils.Simulators import SimulatorModeBus
dummy_simulator=SimulatorModeBus(port=dummy_device.port,modbus_map=dummy_device.modbus_map,bo=dummy_device.byte_order,wo=dummy_device.word_order)
dummy_simulator.start()

def test_collect_insert():
    dummy_device.connectDevice()
    dummy_device.quick_modbus_single_register_decoder(10,2,'float32',unit=1);
    dummy_device.quick_modbus_single_register_decoder(10,2,'float32',unit=1);
    tags=dummy_device.dfplc.index.to_list()
    dummy_device.connectDevice()
    data=dummy_device.collectData('CET',tags)## do not forget to precise the time zome
    dummy_device.insert_intodb(dummy_conf.DB_PARAMETERS,dummy_conf.DB_TABLE,'CET',tags)
    comUtils.read_db(dummy_conf.DB_PARAMETERS,dummy_conf.DB_TABLE)

from sylfenUtils.comUtils import SuperDumper_daily
DEVICES = {
    'dummy_device':dummy_device,
}
log_file_name=os.path.join(dummy_conf.LOG_FOLDER,'dumper.log') ## give a name to your logger.
log_file_name=None ## if you want either to have the information in the console use None.

dumper=SuperDumper_daily(DEVICES,dummy_conf.FOLDERPKL,dummy_conf.DB_PARAMETERS,dummy_conf.PARKING_TIME,
    dbTable=dummy_conf.DB_TABLE,tz_record=dummy_conf.TZ_RECORD,log_file=log_file_name)

####################
# SUGGESTION MODIF #
####################
###### REPLACE BY FOLLOWING #### =======>>> dumper=SuperDumper_daily(conf)
dumper.park_database()
dumper.start_dumping()
