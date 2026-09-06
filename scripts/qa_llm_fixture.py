"""Disposable local SSE fixture for billing browser acceptance. Never a real provider."""
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        self.rfile.read(int(self.headers['Content-Length']))
        draft={'draft':{'material':'BF33','targets':{'depth_um':{'value':10,'tolerance':100,'operator':'eq','unit':'um'}}},'explanation':'测试目标已提取，请核对表单。'}
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        event={'choices':[{'delta':{'content':json.dumps(draft)},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':20,'prompt_tokens_details':{'cached_tokens':30}}}
        self.wfile.write(('data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n').encode())
HTTPServer(('0.0.0.0',9001),Handler).serve_forever()
