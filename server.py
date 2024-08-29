from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/', methods=["GET", "POST"])
def index():
    app.logger.debug(request.headers)
    app.logger.debug(request.args)
    app.logger.info(json.dumps(request.json, indent=4, ensure_ascii=False))
    return {'status': 'Success'}

if __name__ == '__main__':

    app.run(port=8000, debug=True)