from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from aicore_llm import AICoreClient

# 初始化 AI 客户端（只启动一次）
client = AICoreClient.from_service_key_file("./service_key.json")

# 前端聊天页面（纯HTML）
html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SAP AI 聊天</title>
    <style>
        body{max-width:700px;margin:20px auto;background:#f5f5f5}
        .chat{height:600px;overflow-y:auto;background:white;padding:20px;border-radius:10px}
        .msg{margin:10px 0;padding:10px 14px;border-radius:10px;max-width:70%}
        .user{background:#009efb;color:white;margin-left:auto}
        .ai{background:#e5e5ea;color:#111}
        .input{display:flex;margin-top:10px}
        input{flex:1;padding:12px;border-radius:20px;border:1px solid #ddd}
        button{padding:12px 20px;background:#009efb;color:white;border:none;border-radius:20px;margin-left:10px}
    </style>
</head>
<body>
    <div class="chat" id="box"></div>
    <div class="input">
        <input id="msg" placeholder="输入消息...">
        <button onclick="send()">发送</button>
    </div>

    <script>
        async function send() {
            let m = document.getElementById("msg").value.trim();
            if(!m) return;
            
            addMsg(m, "user");
            document.getElementById("msg").value = "";
            
            let res = await fetch("/api", {
                method:"POST",
                body: m
            });
            let reply = await res.text();
            addMsg(reply, "ai");
        }

        function addMsg(text, cls) {
            let d = document.createElement("div");
            d.className = "msg " + cls;
            d.innerText = text;
            document.getElementById("box").appendChild(d);
            document.getElementById("box").scrollTop = 99999;
        }
    </script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        msg = self.rfile.read(length).decode("utf-8")
        
        # 调用你的 AI
        reply = client.chat(msg)
        
        self.send_response(200)
        self.send_header("Content-type", "text/plain;charset=utf-8")
        self.end_headers()
        self.wfile.write(reply.encode("utf-8"))

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 5000), Handler)
    print("聊天服务已启动 → http://127.0.0.1:5000")
    server.serve_forever()
    app.run(host='0.0.0.0', port=5000, debug=True)