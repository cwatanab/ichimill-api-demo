import dotenv
import json
dotenv.load_dotenv(verbose=True)
from loguru import logger

import ichimill


if __name__ == "__main__":

    client = ichimill.Client()
    
    devices = ["lc8034"]
    
    #r = client.get_traking_data(devices=devices, callback_url="https://323a-111-102-203-201.ngrok-free.app")
    #logger.info(json.dumps(r, indent=4, ensure_ascii=False))

    #r = client.request_data_download_file_URL(request_id=91810)
    #logger.info(json.dumps(r, indent=4, ensure_ascii=False))

    #r = client.get_device_list()
    #logger.info(json.dumps(r, indent=4, ensure_ascii=False))

    #r = client.send_command(devices=devices, command=ichimill.Command.GETGPS, callback_url="https://323a-111-102-203-201.ngrok-free.app")
    #logger.info(json.dumps(r, indent=4, ensure_ascii=False))

    client.realtime_tracking(devices=devices, callback_func=lambda x: logger.debug(x))
