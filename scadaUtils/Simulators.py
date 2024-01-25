# #######################
# #      SIMULATORS     #
# #######################
import opcua
import numpy as np
import threading,time

class Simulator():
    ''' for inheritance a simulator should have:
    - inheritance of a Device children class
    - a function "serve" that starts the serveer
    - a function "writeInRegisters" to feed the data.
    - a function "shutdown_server" to shutdown the server.
    '''
    def __init__(self,simulator_name,speedflowdata=500,volatilitySimu=5):
        '''
        - speedflowdata : single data trigger event in ms
        - volatilitySimu : how much random variation (absolute units)
        '''
        self.simulator_name = simulator_name
        self.volatilitySimu = volatilitySimu
        self.speedflowdata = speedflowdata
        # self.server_thread = threading.Thread(target=self.serve)
        # self.server_thread.daemon = True
        self.feed = True
        self.stopfeed = threading.Event()
        self.feedingThread = threading.Thread(target=self.feedingLoop)
        # self.feedingThread.daemon = True

    def stop(self):
        self.stopfeed.set()
        self.shutdown_server()
        print("Server stopped")

    def start(self):
        print("Start server...")
        # self.server_thread.start()
        # self.serve()
        print("Server",self.simulator_name,"is online")
        self.feedingLoop()
        # self.feedingThread.start()
        # print("Server simulator is feeding")

    def stopFeeding(self):
        self.feed=False

    def startFeeding(self):
        self.feed=True

    def feedingLoop(self):
        while not self.stopfeed.isSet():
            if self.feed:
                start=time.time()
                self.writeInRegisters()
                # print('fed in {:.2f} milliseconds'.format((time.time()-start)*1000))
                time.sleep(self.speedflowdata/1000 + np.random.randint(0,1)/1000)

    def is_serving(self):
        return self.server_thread.is_alive()

from pymodbus.server.sync import ModbusTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian
class SimulatorModeBus(Simulator):
    def __init__(self,modbus_map,bo,wo,*args,port=502,**kwargs):
        '''
        - bo,wo : byteorder : 'big' or 'little'
        '''
        Simulator.__init__(self,*args,**kwargs)
        self.bo = bo
        self.wo = wo
        self.port = port
        self.modbus_map = modbus_map
        # initialize server with random values
        self.modbus_map['value'] = self.modbus_map[['minimum','maximum']].apply(lambda x:x[0] + np.random.randint(0,x[1]-x[0]),axis=1)
        self.modbus_map['precision'] = 0.1
        self.modbus_map['FREQUENCE_ECHANTILLONNAGE']=1
        self.all_slaves = list(self.modbus_map['slave_unit'].unique())
        # Create an instance of ModbusServer
        slaves={}
        for k in self.all_slaves:
            slaves[k]  = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [k]*128))
            self.context = ModbusServerContext(slaves=slaves, single=False)
        self.server = ModbusTcpServer(self.context, address=("", int(self.port)))
        self.server_thread = threading.Thread(target=self.serve)
        self.server_thread.daemon = True
        self._feedingClient = ModbusClient(host='localhost',port=int(self.port))
        self._feedingClient.connect()

    def start(self):
        print("Start server...")
        self.server_thread.start()
        print("Server",self.simulator_name,"is online")
        self.feedingThread.start()
        print("Server simulator",self.simulator_name, "is feeding")

    def writeInRegisters(self):
        for tag,d in self.modbus_map.T.to_dict().items():
            value = d['value'] + np.random.randn()*d['value']*self.volatilitySimu/100
            self.modbus_map.loc[tag,'value'] = value

            if self.bo.lower()=='little' and self.wo.lower()=='big':
                builder = BinaryPayloadBuilder(byteorder=Endian.Little, wordorder=Endian.Big)
            elif self.bo.lower()=='big' and self.wo.lower()=='big':
                builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
            elif self.bo.lower()=='little' and self.wo.lower()=='little':
                builder = BinaryPayloadBuilder(byteorder=Endian.Little, wordorder=Endian.Little)
            elif self.bo.lower()=='big' and self.wo.lower()=='little':
                builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Little)

            if d['type']=='float32':
                builder.add_32bit_float(value)
            else:
                value=int(value)
            if d['type']=='uint16':
                builder.add_16bit_uint(value)
            if d['type']=='uint8':
                builder.add_8bit_int(value)
            if d['type']=='uint32':
                builder.add_32bit_uint(value)
            if d['type']=='int32':
                builder.add_32bit_int(value)
            payload = builder.build()
            # print(value)
            self._feedingClient.write_registers(d['intaddress'], payload, skip_encode=True, unit=d['slave_unit'])

    def serve(self):
        self.server.serve_forever()

    def shutdown_server(self):
        self.server.shutdown()
        print("Server simulator is shutdown")

class SimulatorOPCUA(Simulator):
    '''
    dfPLC should have columns index as tags, DATATYPE
    '''
    def __init__(self,endpointUrl,dfPLC,nameSpace,*args,**kwargs):
        start=time.time()
        Simulator.__init__(self,*args,**kwargs)
        time.time()-start
        self.server=opcua.Server()
        self.endpointUrl=endpointUrl
        self.nameSpace=nameSpace
        self.server.set_endpoint(endpointUrl)
        self.server.register_namespace('room1')
        self.dfPLC=dfPLC
        self.dfPLC.MIN=dfPLC.MIN.fillna(-20000)
        self.dfPLC.MAX=dfPLC.MAX.fillna(20000)
        self.nodeValues = {}
        self.nodeVariables = {}
        self.createNodes()

    def serve(self):
        try:
            print("start server")
            self.server.start()
            print("server Online")
        finally:
            self.shutdown_server()

    def shutdown_server(self):
        self.server.stop()
        print("server Offline")

    def createRandomInitalTagValues(self):
        valueInit={}
        for tag in list(self.dfPLC.index.unique()):
            tagvar=self.dfPLC.loc[tag]
            if tagvar.DATATYPE=='STRING(40)':
                valueInit[tag] = 'STRINGTEST'
            else:
                valueInit[tag] = np.random.randint(tagvar.MIN,tagvar.MAX)
        return valueInit

    def createNodes(self):
        objects =self.server.get_objects_node()
        beckhoff=objects.add_object(self.nameSpace,'beckhof')
        valueInits = self.createRandomInitalTagValues()
        for tag,val in valueInits.items():
            self.nodeValues[tag]    = val
            self.nodeVariables[tag] = beckhoff.add_variable(self.nameSpace+tag,tag,val)

    def writeInRegisters(self):
        for tag,var in self.nodeVariables.items():
            tagvar=self.dfPLC.loc[tag]
            if tagvar.DATATYPE=='REAL':
                newValue = self.nodeValues[tag] + self.volatilitySimu*np.random.randn()*tagvar.PRECISION
                self.nodeVariables[tag].set_value(newValue)
            else:
                newValue = np.random.randint(0,2)
                self.nodeVariables[tag].set_value(newValue)
            self.nodeValues[tag] = newValue
        # tagTest = 'SEH1.STB_STK_03.HER_01_CL01.In.HR26'
        # tagTest = 'SEH1.GWPBH_PMP_05.HO00'
        tagTest = 'SEH1.STB_GFC_00_PT_01_HC21'
        # tagTest = 'SEH1.STB_STK_01.SN'
        # tagTest = 'SEH1.HPB_STG_01a_HER_03_JT_01.JTVAR_HC20'
        print(tagTest + ': ',self.nodeVariables[tagTest].get_value())

class SuperSimulator():
    def __init__(self,conf):
        DEVICES = {}
        devicesInfo=conf.df_devices.copy()
        devicesInfo.columns=[k.lower() for k in devicesInfo.columns]
        for device_name in devicesInfo[devicesInfo['protocole']=='modbus'].index:
            d_info=devicesInfo.loc[device_name]
            DEVICES[device_name]=SimulatorModeBus(
                simulator_name=device_name,
                port=d_info['port'],
                modbus_map=conf.modbus_maps[device_name],
                bo=d_info['byte_order'],
                wo=d_info['word_order'],
            )
        self.devices=DEVICES
    def start_device(self,device_name):
        self.devices[device_name].start()

    def start_all_devices(self):
        for d in self.devices.keys():
            self.start_device(d)
