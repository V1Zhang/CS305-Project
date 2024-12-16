from flask import Flask, request, jsonify, make_response, redirect, url_for
from flask_cors import CORS



app = Flask(__name__)
app.config.from_object(__name__)

# enable CORS 跨源HTTP请求控制
CORS(app)

message = ""


@app.route('/')
def hello_world():
    return "Hello World!"


@app.route('/vueflask', methods=['POST', 'GET'])
def vueflask():
    response = jsonify({"message": "Success!"})
    response.headers.set('Access-Control-Allow-Origin', '*')
    if request.method == 'POST': # 如果是POST请求
        data = request.json
    
        action_id = data.get('actionId')
        if action_id == 1:
            text = Foream_Plank_Calculate(joints)
        else:
            error = 'Invalid action ID'
        return jsonify({'text': text})
    else:
        return response
    

    





if __name__ == '__main__':
    app.run(debug=True)