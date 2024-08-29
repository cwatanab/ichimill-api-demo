import requests
import json
import datetime
import os
from enum import Enum
import dotenv
import socketio
import urllib
from loguru import logger
dotenv.load_dotenv(verbose=True)


class Action(Enum):
    GET_TRACKING_DATA = "getTrackingData"
    REQUEST_DATA_DOWNLOAD_FILE_URL = "requestDataDownloadFileURL"
    GET_DEVICE_LIST = "getDeviceList"
    SEND_COMMAND = "sendCommand"
    REALTIME_TRACKING = "realTimeTracking"


class DataType(Enum):
    FIX_ONLY = 0
    ALL = 1


class DataFormat(Enum):
    XML = 0
    CSV = 1


class Command(Enum):
    GPSSLEEPTIME = "gpssleeptime"
    SENSOR = "sensor"
    SETTING = "setting"
    GETGPS = "getgps"


class IchimillAPI(object):


    def __init__(self, url="https://rtk.multignss-smarttracking.com/", access_id=None, api_key=None, verbose=True):
        self.session = requests.Session()
        self.url = url
        self.access_id = access_id or os.environ["ACCESS_ID"]
        self.api_key = api_key or os.environ["API_KEY"]
        self.verbose = verbose


    def __send(self, action=None, params={}):
        params["access_id"] = self.access_id
        params["api_key"] = self.api_key
        logger.debug(f"{self.url}/{action.value}")
        logger.debug(params)
        response = self.session.post(f"{self.url}/rtk/api/{action.value}", params=params)
        response.raise_for_status()
        return response.json()


    def get_traking_data(self, devices=[], data_type=DataType.ALL, data_format=DataFormat.CSV,
            from_dt=datetime.datetime.now().replace(hour=0, minute=0, second=0), 
            to_dt=datetime.datetime.now().replace(hour=23, minute=59, second=59),
            callback_url=None,
        ):
        """ 測位データ一括取得 """
        params = {
            "device": (",").join(devices),
            "from": from_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "to": to_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "data_type": data_type.value,
            "calllback": callback_url,
            "data_format": data_format.value,
        }
        return self.__send(Action.GET_TRACKING_DATA, params)


    def request_data_download_file_URL(self, request_id=None, should_download=False):
        """ ダウンロードURL取得 """
        params = {
            "request_id": request_id,
        }
        response = self.__send(Action.REQUEST_DATA_DOWNLOAD_FILE_URL, params)

        if should_download:
            dowload_url = response["download_url"]
            with open(os.path.basename(dowload_url), mode="wb") as f:
                f.write(self.session.get(dowload_url).content)

        return response


    def send_command(self, devices=[], command=Command.SETTING, value=None, callback_url=None):
        """ コマンド送信 """
        params = {
            "device": (",").join(devices),
            "command": command.value,
            "setValue": value,
            "callback": callback_url,
        }
        return self.__send(Action.SEND_COMMAND, params)


    def get_device_list(self):
        """ 端末リスト取得 """
        return self.__send(Action.GET_DEVICE_LIST)


    def realtime_tracking(self, device=None, callback_func=None):
        """ 測位データリアルタイム取得 """
        sio = socketio.Client(
            reconnection=True, 
            reconnection_attempts=0, 
            reconnection_delay=2,
            reconnection_delay_max=30,
            logger=self.verbose,
            engineio_logger=self.verbose
        )
        @sio.event
        def multignss_tracking(data):
            json_data = json.loads(data)
            callback_func(json_data)
            # logger.debug(json.dumps(json_data, indent=2, ensure_ascii=False))

        params = {
            "api": Action.REALTIME_TRACKING.value,
            "id": self.access_id,
            "key": self.api_key,
            "device": device,
        }
        try:
            sio.connect(f"{self.url}?{urllib.parse.urlencode(params)}", namespaces=["/"], transports="websocket", socketio_path="/v2/socket.io")
            sio.wait()
        except KeyboardInterrupt:
            sio.disconnect()


if __name__ == "__main__":

    ichimill = IchimillAPI()
    
    #r = ichimill.get_traking_data(devices=["lc8034"], callback_url="https://323a-111-102-203-201.ngrok-free.app")
    #logger.info(json.dumps(r, indent=4, ensure_ascii=False))

    r = ichimill.request_data_download_file_URL(request_id=91763)
    logger.info(json.dumps(r, indent=4, ensure_ascii=False))

    # r = ichimill.get_device_list()
    # logger.info(json.dumps(r, indent=4, ensure_ascii=False))

    # r = ichimill.send_command(devices=["lc8034"], command=Command.GETGPS, callback_url="https://323a-111-102-203-201.ngrok-free.app")
    # logger.info(json.dumps(r, indent=4, ensure_ascii=False))

    # ichimill.realtime_tracking(device="lc8034", callback_func=lambda x: logger.debug(x))
