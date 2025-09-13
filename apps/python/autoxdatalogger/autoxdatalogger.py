import ac

from data import DataStorage


# globals
telemetry_data = DataStorage()

def acMain(ac_version):
    appWindow = ac.newApp("AutoX Data Logger")
    ac.setSize(appWindow, 200, 200)
    return "AutoX Data Logger"

def acUpdate(dT):
    telemetry_data.update_data(dT)

def acShutdown():
    telemetry_data.parse_data()
    ac.log("saving data ... ")
    telemetry_data.write_data()
