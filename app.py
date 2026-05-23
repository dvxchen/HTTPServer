from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "OK"

if __name__ == '__main__':
    # 必须绑定 0.0.0.0，且 debug=False
    app.run(host='0.0.0.0', port=5000, debug=False)
