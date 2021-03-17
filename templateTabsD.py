from dccExtended import DccExtended

class TemplateTabMaster:
    def __init__(self,cfg,tabName,idTab):
        self.cfg        = cfg
        self.tabName    = tabName
        self.idTab      = idTab
        self.dccE       = DccExtended()
