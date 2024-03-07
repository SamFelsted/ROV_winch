from ROVwinch import ROVwinch
import time
import argparse
import traceback
import const

# parse arguements
argParser = argparse.ArgumentParser()
argParser.add_argument("-m", "--mode", help=" mode of operation. Options: debug, deploy", default='deploy')
args = argParser.parse_args()

while True:
    ROVwinchObject = ROVwinch(args.mode)
    try:
        ROVwinchObject.control_winch()
    except Exception:
        print("critical failure")
        ROVwinchObject.turnOffWinchSystem()
        print(traceback.format_exc())
        time.sleep(const.ROVconst.failureSleep)
    except KeyboardInterrupt:
        ROVwinchObject.turnOffWinchSystem()
        exit()
