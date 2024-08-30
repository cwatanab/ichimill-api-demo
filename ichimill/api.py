import requests
import json
import datetime
import os
import socketio
import urllib
from loguru import logger
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field, field_serializer

URL = "https://rtk.multignss-smarttracking.com/"

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


class RequestModel(BaseModel):
    access_id: str = Field(os.environ["ACCESS_ID"])
    api_key: str = Field(os.environ["API_KEY"], min_length=32, max_length=32)


class TrackingDataRequest(RequestModel):
    model_config = ConfigDict(use_enum_values=True)
    device: Optional[List[str]] = None
    from_dt: datetime.datetime = Field(datetime.datetime.now().replace(hour=0, minute=0, second=0), alias='from')
    to_dt: datetime.datetime = Field(datetime.datetime.now().replace(hour=23, minute=59, second=59), alias='to')
    data_type: Optional[DataType] = None
    callback: Optional[str] = None
    data_format: Optional[DataFormat] = DataFormat.CSV

    @field_serializer("from_dt")
    def serialize_from_dt(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @field_serializer("to_dt")    
    def serialize_to_dt(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @field_serializer("device")    
    def serialize_devices(self, devices: List) -> str:
        return (",").join(devices)


class RequestDataDownloadFileURLRequest(RequestModel):
    request_id: int


class SendCommandRequest(RequestModel):
    model_config = ConfigDict(use_enum_values=True)    
    device: Optional[List[str]] = None
    command: Command = None
    set_value: Optional[Any] = None
    callback: str = None

    @field_serializer("device")    
    def serialize_devices(self, devices: List) -> str:
        return (",").join(devices)


class ReatimeTrackingRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)    
    api: str = Action.REALTIME_TRACKING,
    id: str = Field(os.environ["ACCESS_ID"])
    key: str = Field(os.environ["API_KEY"])
    device: Optional[List[str]] = None

    @field_serializer("device")    
    def serialize_devices(self, devices: List) -> str:
        return (",").join(devices)


class Client(object):

    def __init__(self, url=URL, verbose=True):
        self.session = requests.Session()
        self.url = url
        self.verbose = verbose


    def __send(self, action: Command=None, params: RequestModel=RequestModel()):
        logger.debug(f"{self.url}/rtk/api/{action.value}")
        response = self.session.post(f"{self.url}/rtk/api/{action.value}", params=params.model_dump(exclude_none=True, by_alias=True))
        response.raise_for_status()
        return response.json()


    def get_traking_data(self, devices=[], data_type=None, data_format=None, from_dt=None, to_dt=None, callback_url=None):
        """ 測位データ一括取得 """
        req = TrackingDataRequest(
            device=devices,
            from_dt=from_dt,
            to_dt=to_dt,
            data_type=data_type,
            calllback=callback_url,
            data_format=data_format,
        )
        return self.__send(Action.GET_TRACKING_DATA, req)


    def request_data_download_file_URL(self, request_id=None, should_download=False):
        """ ダウンロードURL取得 """
        req = RequestDataDownloadFileURLRequest(
            request_id=request_id,
        )
        response = self.__send(Action.REQUEST_DATA_DOWNLOAD_FILE_URL, req)

        if should_download:
            dowload_url = response["download_url"]
            with open(os.path.basename(dowload_url), mode="wb") as f:
                f.write(self.session.get(dowload_url).content)

        return response


    def send_command(self, devices=[], command=Command.SETTING, value=None, callback_url=None):
        """ コマンド送信 """
        req = SendCommandRequest(
           device=devices,
           command=command,
           set_value=value,
           callback=callback_url,
        )
        return self.__send(Action.SEND_COMMAND, req)


    def get_device_list(self):
        """ 端末リスト取得 """
        return self.__send(Action.GET_DEVICE_LIST)


    def realtime_tracking(self, devices=[], callback_func=None):
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

        req = ReatimeTrackingRequest(device=devices)
        query = urllib.parse.urlencode((req.model_dump(exclude_none=True)))
        try:
            sio.connect(f"{self.url}?{query}", namespaces=["/"], transports="websocket", socketio_path="/v2/socket.io")
            sio.wait()
        except KeyboardInterrupt:
            sio.disconnect()
