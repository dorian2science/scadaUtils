def test_ads_client():
    beck=comUtils.ADS_Client(device_name='ads_top',ip=conf.ip_beckhoff,dfplc=conf.beckhoff_plc)
    beck._get_machine_ip()
    beck._initialize_route()
