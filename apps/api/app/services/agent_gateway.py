"""One metered gateway for all external LLM traffic; credentials never enter results."""
import hashlib
import json
import time
import httpx
from fastapi import HTTPException
from app.services import agent_billing as billing
from app.services import agent_model_config as models


def invoke(owner,purpose,key,message_payload,model_id=None,platform=False):
    billing.recover()
    model=models.resolve(model_id,platform)
    if not model:return {'disabled':True}
    fingerprint=hashlib.sha256(json.dumps({'payload':message_payload,'model_id':model_id},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    input_bound=len(json.dumps(message_payload,ensure_ascii=False).encode())+128
    call=billing.begin(owner,purpose,key,fingerprint,model,input_bound,platform)
    if call.get('replay'):
        if call.get('result'):return {'replay':json.loads(call['result']),'call_id':call['id']}
        raise HTTPException(409,'该操作已结束但没有成功结果，请使用新的操作标识重试')
    call_id=call['id'];budget=call['output_budget']
    headers={}
    payload={'model':model['model'],'messages':message_payload,'stream':True}
    if model['protocol']=='ollama':
        payload.update({'format':'json','options':{'num_predict':budget}});endpoint='/api/chat'
    else:
        payload.update({'max_tokens':budget,'stream_options':{'include_usage':True}});endpoint='/chat/completions'
    chunks=[];usage=None;started=time.monotonic();completed=False;output_bytes=0
    try:
        if model['secret']:headers['Authorization']='Bearer '+models.cipher().decrypt(model['secret'].encode()).decode()
        with httpx.stream('POST',model['base_url']+endpoint,json=payload,headers=headers,timeout=model['timeout']) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if time.monotonic()-started>model['timeout']:raise ValueError('调用超时')
                if not line or line.startswith(':'):continue
                if line.startswith('data:'):line=line[5:].strip()
                if line=='[DONE]':completed=True;break
                try:part=json.loads(line)
                except json.JSONDecodeError:continue
                candidate=billing.normalize_usage(part,model['protocol'])
                if candidate is not None:usage=candidate
                if model['protocol']=='ollama':
                    fragment=(part.get('message') or {}).get('content','');completed=bool(part.get('done'))
                else:
                    choice=(part.get('choices') or [{}])[0]
                    fragment=(choice.get('delta') or choice.get('message') or {}).get('content','') or ''
                    if choice.get('finish_reason') in ('length','content_filter'):raise ValueError('输出中断')
                    completed=completed or choice.get('finish_reason')=='stop'
                chunks.append(fragment)
                output_bytes+=len(fragment.encode())
                if output_bytes>budget*16:raise ValueError('输出超出预算')
                if usage and (usage['output']>budget or usage['cached']+usage['uncached']>input_bound):raise ValueError('供应商报告用量超出预留范围')
        billing.received(call_id,usage)
        if not completed or not ''.join(chunks).strip():raise ValueError('上游未返回完整结果')
        return {'text':''.join(chunks),'call_id':call_id}
    except Exception:
        billing.received(call_id,usage)
        billing.finish(call_id,False,reason='模型服务失败、输出不完整或预算中断')
        raise HTTPException(502,'模型调用未完成，本次不扣 credit；可选择本地模式')
