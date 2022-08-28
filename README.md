# SylfenUtils V

This package contains utilities for :
- comUtils : to standardize the dumping of data from different devices(Modbus,Meteo,OPCUA) with a Streamer, SuperDumper_daily and VisualisationMaster_daily
- Simulators : to simulate the flow of data from devices(servers) from comUtils
- utilsD : convenient plotly,pandas extensions to work faster
- versionManagers : to deal with historical data folders and to make them compatible with the daily visualisation master.

## Dashboard
for your dashboard application to work with the standard dashboard template you need :
- instanciate an Dashboard application as in the example bellow:

```python
from sylfenUtils import dashboard
dash=dashboard.Dashboard(cfg,LOG_DIR,root_folder)
```
cfg is a standard from ComUtils VisualisationMaster_daily object from comUtils.

It is needed to specify your root_folder where the static and templates folder are. Make symbolic link of the folder *lib* of your sylfenUtils distribution from <your_dist_folder>/sylfenUtils/static/lib in your static folder :

```shell
cd <your_root_folder>
mkdir static
cd static
ln -s <your_dist_folder>/sylfenUtils/static/lib
```     

You also need of valid path for the log directory where the log of the app are going to be stored.

When that is done you can just run your application :
```python
dash.app.run(host='0.0.0.0',port=25000)
```
