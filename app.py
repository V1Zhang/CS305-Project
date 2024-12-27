from flask import Flask, Response, request
from flask_cors import CORS
from utils.camera import Camera

app = Flask(__name__)
CORS(app)

camera = Camera()


@app.route("/")
def index():
    return "Welcome to Fitness Magic Mirror API!"


@app.route("/hello", methods=["GET", "POST"])
def hello():
    return "Hello World!"


@app.route("/hi", methods=["GET", "POST"])
def hi():
    return "Hi World!"


def get_frame(display):

    while True:
        frame = display.get_frame()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


@app.route("/get_video", methods=["GET"])
def grt_video():

    return Response(
        get_frame(camera), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/get_message", methods=["GET"])
def get_message():
    text = int(request.args.get("text"))
    if camera.get_action() != text:
        camera.set_action(text)
    message = camera.get_message()
    return message


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7777, debug=True, threaded=True)
