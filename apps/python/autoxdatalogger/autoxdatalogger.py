import ac

from data import DataStorage


# globals
telemetry_data = DataStorage()

def acMain(ac_version):
    app_window = ac.newApp("AXDL")
    ac.setSize(app_window, 100, 100)
    ac.setTitle(app_window, "")
    ac.drawBorder(app_window, 0)
    ac.setBackgroundOpacity(app_window, 0)
    ac.setBackgroundTexture(app_window, "apps/python/autoxdatalogger/img/appicon.png")
    return "AXDL"

def acUpdate(dT):
    telemetry_data.update_data(dT)

def acShutdown():
    telemetry_data.parse_data()
    ac.log("saving data ... ")
    telemetry_data.write_data()
