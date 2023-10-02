# ScadaUtils V1.0

## DESCRIPTION

This package contains utilities for :
- comUtils : to standardize the dumping of data from different devices(Modbus,Meteo,OPCUA) with a Streamer, SuperDumper_daily and VisualisationMaster_daily
- Simulators : to simulate the flow of data from devices(servers) from comUtils
- utilsD : convenient plotly,pandas extensions to work faster
- versionManagers : to deal with historical data folders and to make them compatible with the daily visualisation master.

## DASHBOARD
for your dashboard application to work with the standard dashboard template you need :
- instanciate an Dashboard application as in the example bellow:

```python
from sylfenUtils import dashboard
dash=dashboard.Dashboard(cfg,LOG_DIR,root_folder)
```
cfg is a standard from ComUtils VisualisationMaster_daily object from comUtils.

## TUTORIAL
There is a jupyter-notebook available [here]() to learn how to dump realtime data from different modbus,opcua devices, and how to read them in realtime. A dashboard can also be used

## pre-requisites

### postgresSQL
- postgressql server should be active running on port 5432(user:postgres,password:sylfenbdd) containing a **jules** database with a **realtimedata** table(default settings).
- do not forget to cofnigure pg_hba.conf correctly.
- you change password of user postgres with :
```shell
alter user <postgres> password '<newpassword>';
```  

## DEPLOYMENT AND PRODUCTION
Create a file  **<myproject>.service** :

```shell
[Unit]
Description=dumping data from <my_project>
After=network.target

[Service]
User=<user>
Group=<group_user>
WorkingDirectory=<your_path_to_job>/job/
Environment="PATH=<your_virtual_env_path>/bin"
ExecStart=<your_virtual_env_path>/bin/python <your_job>.py

[Install]
WantedBy=multi-user.target
```

- Make a symbolic link of this file (or copy it) into `systemd` folder:
```
cd /etc/systemd/system/
ln -s <your_service_path>
```

REMARKS:

- of course the dumper can be manually started with `python job/<your_job>.py`.
- systemctl command
    - start : `systemctl start <your_job>.service`
    - status : `systemctl status <your_job>.service`
    - enable(start at boot): `systemctl enable <your_job>.service`
    - stop : `systemctl stop <your_job>.service`
## Serving dashboard

To serve the dashboard(from your virtual environment) just :
`python dashboard/dashboard_<your_project>.py`

### Dashbaord in production environmment ==> GUNICORN
To serve the dashboard in a production environment(more reliable) you need to start it with gunicorn. The best is to create a file **<your_dashboard>.service** with following content:

```shell
[Unit]
Description=Gunicorn instance to serve small power dashboard
After=network.target

[Service]
User=<username>## the user that runs the dashboard
Group=<group>## the group that runs the dashboard
WorkingDirectory=<path>### path of the dashboard application
Environment="PATH=<path_to_venv>"## the python environment used
ExecStart=<path_gunicorn> -b localhost:<port_dashboard> -w 4 dashboard_<your_project>:app ## precise the full path where to find gunicorn in your venv and the port of the dashboard. You can also change -w which is the number of clients served simultaneously.

[Install]
WantedBy=multi-user.target
```
- Make a symbolic link of this file (or copy it) into `systemd` folder:
```
cd /etc/systemd/system/
ln -s <your_service_path><your_project>.service
```

You can start <your_project> service (this is to be done only once).

```
sudo systemctl start <your_project>
```

If you get this error `Unit <your_project>.service could not be found.` do :`systemctl daemon-reload`

Enable the <your_project> dashboard service so that it automatically starts at boot:
```
sudo systemctl enable <your_project>
```
Check status, enabled status, and log activity with respectively:
- ```sudo systemctl status <your_project>```
- ```systemctl list-unit-files```
- ```journalctl | grep <your_project>```

If there are not any big error but the dashboard is not accessible, it means there is an error in the dashboard_<your_project>.py somewhere. Try to run in with flask : app.run(), check access and then with gunicorn ==> `<your_env>/gunicorn -b localhost:<port> dashboard_<your_project>:app`

### Link a domain name to the website ==> NGINX
If you want to redirect the name of the url using your domain name you have to do a redirection of the port using nginx. Create a file <url_app>.conf virtual host file with following content:

```shell
server {
    listen 80;
    server_name <domain name><your_project>.sylfen.com <domain name>;

    location / {
        proxy_pass      http://127.0.0.1:<port_dashboard>;
    }
}
```

- Make a symbolic link of this file (or copy it) into `sites-available` and `sites-enabled` folders:
```
ln -s <your_<your_project>.conf_file> /etc/nginx/sites-available
ln -s <your_<your_project>.conf_file> /etc/nginx/sites-enabled
```

REMARK :
- On a local network a switch can only redirect the port 80(default port for HTTP) and/or the port 443(default port for HTTPS) to one device on the network. This means that if the port is already forwarded to a machine different from yours, your website won't be accessible.
- if you still want to make test on your reverse proxy, you can force the redirection by editing `/etc/hosts` by adding a line  ==>     127.0.0.1   <your_domain_name>. Your browser will directly associate the domain_name to your machine and won't search on the internet.

### update your configuration
To take the modification of your configuration into account :  

```
sudo nginx -s reload

```
This will reload all the configuration of the websites in `sites-available`.



### GOOD PRACTICES :
#### make tests on remote machine

In order no to corrupt and create bugs to a deployed version while trying to make some tests on remote machine, a good way is :
- to create another user
- give him access to the data but make sure it can't modify them. Datafolder should be 775 permissions.
- clone the git project in a folder  
- create a virtual environmment(as always) and install the library. You are ready to make tests safely!!!

#### easy procedure to update the production environment

Once you are done with you your tests and your are sure that the version is stable and not creating bugs you are ready for release it for users. Then
- update(stabilize) the version of sylfenUtils and that of <your_project> with the sylfenUtils dependency.
- git push both
- git pull in the production folder
- install with pip in your .env environment virtual the new version and uninstall if necessary the sylfenUtils dependency before new installation.
- restart <your_project>.service to see the effect : `systemctl restart <your_project>.service`

```
cd <your_project>
git pull
source .env/bin/activate
pip uninstall sylfenUtils
pip install .
systemctl restart <your_project>.service
```
