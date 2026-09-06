from __future__ import annotations

import hashlib
import base64
import binascii
import math
import os
from pathlib import Path
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from pydantic import BaseModel, Field
from app.services import agent_store as store
from app.services.agent_decision import decide, dataset, validate_task
from app.services.agent_models import REGISTRY, groups
from app.services.agent_knowledge import extract, search, orchestrate, document_payload
from app.services.data_loader import QUALITY_COLUMNS, PARAMETER_COLUMNS
from app.settings import get_settings
from app.services.agent_billing import finish as finish_call

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/formulas")
def formulas(user=Depends(store.current_user)):
    return store.records("public", "formula")


@router.post("/formulas")
def propose_formula(body: dict, user=Depends(store.administrator)):
    from app.services.agent_formulas import validate
    validate(body)
    return {"id": store.append("public", "formula", {**body, "status": "pending", "proposed_by": user["id"]})}


@router.post("/formulas/{entity}/approve")
def approve_formula(entity: str, user=Depends(store.administrator)):
    body = store.get_record("public", "formula", entity)
    store.append("public", "formula", {**body, "status": "approved", "reviewed_by": user["id"]}, entity, "revise")
    return {"ok": True}


class Credentials(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=256)


class Registration(BaseModel):
    username: str = Field(min_length=1,max_length=80)
    email: str = Field(max_length=254)
    password: str = Field(min_length=12,max_length=256)


class Verification(BaseModel):
    token: str = Field(min_length=20,max_length=200)


class ImageAttachment(BaseModel):
    name: str = Field(min_length=1,max_length=200)
    media_type: Literal["image/jpeg","image/png","image/gif","image/webp"]
    data: str = Field(min_length=1,max_length=14_000_000)


class Message(BaseModel):
    message: str = Field(default="", max_length=6000)
    task: dict[str, Any] = Field(default_factory=dict)
    model_id: str | None = None
    request_key: str | None = Field(default=None,max_length=100)
    images: list[ImageAttachment] = Field(default_factory=list,max_length=4)


def image_parts(images: list[ImageAttachment]):
    parts=[];total=0
    signatures={
        "image/jpeg":lambda raw:raw.startswith(b"\xff\xd8\xff"),
        "image/png":lambda raw:raw.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif":lambda raw:raw.startswith((b"GIF87a",b"GIF89a")),
        "image/webp":lambda raw:len(raw)>=12 and raw.startswith(b"RIFF") and raw[8:12]==b"WEBP",
    }
    for image in images:
        try:raw=base64.b64decode(image.data,validate=True)
        except (binascii.Error,ValueError):raise HTTPException(422,"图片数据不是有效的 Base64")
        if not raw or len(raw)>10*1024*1024:raise HTTPException(413,"单张图片不能超过 10 MB")
        total+=len(raw)
        if total>20*1024*1024:raise HTTPException(413,"图片总大小不能超过 20 MB")
        if not signatures[image.media_type](raw):raise HTTPException(422,"图片内容与声明格式不一致")
        parts.append({"type":"image_url","image_url":{"url":f"data:{image.media_type};base64,{image.data}"}})
    return parts


@router.post("/interpret")
def interpret(body: Message, user=Depends(store.current_user)):
    if not body.message.strip() and not body.images:
        raise HTTPException(422, "请先描述加工目标或上传图片")
    result = orchestrate(body.message, {}, [], purpose="interpret",owner=user['id'],request_key=body.request_key,model_id=body.model_id,images=image_parts(body.images))
    if 'operation_result' in result:return result['operation_result']
    draft = result.get("draft")
    if not isinstance(draft, dict):
        result["draft"] = {}
    if result.get('call_id'):finish_call(result['call_id'],True,result)
    # Drafts cannot enter recommendation directly; the client reviews the normal validated form.
    return result


@router.post("/formulas/extract")
def extract_relation(body: Message, user=Depends(store.administrator)):
    material = body.task.get("material")
    if material not in set(dataset(user["id"]).material):
        raise HTTPException(422, "请选择有数据支持的材料")
    citations = search("public", body.message)
    result = orchestrate(body.message, {"fields": PARAMETER_COLUMNS, "materials": [material]}, citations, purpose="relations",owner=user["id"],request_key=body.request_key,model_id=body.model_id,platform=True,images=image_parts(body.images))
    if "operation_result" in result:return result["operation_result"]
    try:
        proposal = result.get("proposal")
        if isinstance(proposal, dict):
            from app.services.agent_formulas import validate
            validate(proposal)
            sources = {c["document_id"]+" | "+c["location"] for c in citations}
            if proposal.get("source") not in sources or proposal.get("materials") != [material]:
                raise HTTPException(422, "提案来源或适用材料无法核对，未保存")
            result["id"] = store.append("public", "formula", {**proposal, "status": "pending", "proposed_by": user["id"], "evidence": citations})
        result["citations"] = citations
        if result.get("call_id"):finish_call(result["call_id"],True,result)
        return result
    except Exception:
        if result.get("call_id"):finish_call(result["call_id"],False,reason="知识关系未通过验证")
        raise


@router.post("/login")
def login(body: Credentials, response: Response):
    token, user = store.login(body.username, body.password)
    response.set_cookie("laser_session", token, httponly=True, samesite="strict", secure=os.getenv("LASER_COOKIE_SECURE", "false").lower() == "true", max_age=43200, path="/")
    return user


@router.post("/register")
def register(body: Registration):
    from app.services.email_registration import register as create_registration
    return create_registration(body.username,body.email,body.password)


@router.post("/register/verify")
def verify_registration(body: Verification):
    from app.services.email_registration import verify
    return verify(body.token)


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("laser_session", "")
    with store.database() as conn:
        conn.execute("DELETE FROM sessions WHERE token=?", (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie("laser_session", path="/")
    return {"ok": True}


@router.get("/me")
def me(user=Depends(store.current_user)):
    return user


@router.get("/materials")
def materials(user=Depends(store.current_user)):
    frame = dataset(user["id"])
    return [{"name": str(name), "metrics": [c for c in QUALITY_COLUMNS if group[c].notna().any()]} for name, group in frame.groupby("material")]


@router.get("/algorithms")
def algorithms(user=Depends(store.current_user)):
    return [{"id": key, "name": item[0], "category": item[1]} for key, item in REGISTRY.items()]


@router.get("/conversations")
def conversations(user=Depends(store.current_user)):
    return store.records(user["id"], "conversation")


@router.post("/conversations")
def new_conversation(user=Depends(store.current_user)):
    return {"id": store.append(user["id"], "conversation", {"title": "新的加工任务", "messages": []})}


@router.get("/conversations/{entity}")
def conversation(entity: str, user=Depends(store.current_user)):
    return store.get_record(user["id"], "conversation", entity)


@router.post("/conversations/{entity}/messages")
def message(entity: str, body: Message, user=Depends(store.current_user)):
    prior = store.get_record(user["id"], "conversation", entity)
    task = body.task
    frame = dataset(user["id"])
    validate_task(task, frame)
    applicable = frame.loc[frame.material == task["material"]]
    citations = search(user["id"], body.message+" "+str(task.get("material", "")))
    selection_context = {**task, "data_conditions": {"samples": len(applicable), "parameter_groups": len(set(groups(applicable))), "observed_responses": {c: int(applicable[c].notna().sum()) for c in task["targets"]}, "recorded_parameters": [c for c in PARAMETER_COLUMNS if applicable[c].notna().any()]}}
    result = decide(user['id'],task,history_only=True)
    provider = {"status":"disabled","message":"历史优先／本地确定性推荐，不产生模型费用","candidates":[]}
    if result is None:
        provider = orchestrate(body.message,selection_context,citations,owner=user['id'],request_key=body.request_key,model_id=body.model_id,images=image_parts(body.images))
        if 'operation_result' in provider:return provider['operation_result']
    try:
        if result is None:result=decide(user['id'],task,provider.get('candidates'))
        result.update({"conversation_id":entity,"citations":citations,"provider":provider,"call_id":provider.get('call_id')})
        recommendation_id=store.append(user['id'],'recommendation',result)
        result['id']=recommendation_id
        prior['title']=task['material']+' · 加工参数'
        prior['messages']=[*prior['messages'],{'text':body.message,'result':result}]
        store.append(user['id'],'conversation',prior,entity,'revise')
        if provider.get('call_id'):finish_call(provider['call_id'],True,result)
        return result
    except Exception:
        if provider.get('call_id'):finish_call(provider['call_id'],False,reason='参数推荐未完成')
        raise


@router.get("/recommendations/{entity}")
def recommendation(entity: str, user=Depends(store.current_user)):
    return store.get_record(user["id"], "recommendation", entity)


def valid_feedback(body):
    if not isinstance(body.get("material"), str) or not body.get("material") or not isinstance(body.get("parameters"), dict) or not body.get("parameters") or not isinstance(body.get("quality"), dict) or not body.get("quality"):
        raise HTTPException(422, "需填写材料、实际加工参数和实测质量")
    for field, allowed in (("parameters", PARAMETER_COLUMNS), ("quality", QUALITY_COLUMNS)):
        for key, value in body[field].items():
            if key not in allowed or isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or (value < 0 and key != "defocus_amount_mm"):
                raise HTTPException(422, "参数或实测值无效")


@router.get("/feedback")
def feedback_list(trash: bool = False, user=Depends(store.current_user)):
    return store.records(user["id"], "feedback", trash)


@router.post("/feedback")
def feedback(body: dict, user=Depends(store.current_user)):
    recommendation_id = body.get("recommendation_id")
    if recommendation_id:
        rec = store.get_record(user["id"], "recommendation", recommendation_id)
        body = {**body, "material": rec["task"]["material"], "parameters": body.get("parameters", rec["parameters"])}
    valid_feedback(body)
    return {"id": store.append(user["id"], "feedback", body), "data_version": store.version(user["id"])}


@router.get("/feedback/{entity}/history")
def feedback_history(entity: str, user=Depends(store.current_user)):
    import json
    with store.database() as conn:
        rows = conn.execute("SELECT seq,action,payload,created FROM events WHERE owner=? AND kind='feedback' AND entity=? ORDER BY seq", (user["id"], entity)).fetchall()
    if not rows:
        raise HTTPException(404, "记录不存在")
    return [{"version": r["seq"], "action": r["action"], "created": r["created"], "data": json.loads(r["payload"])} for r in rows]


@router.put("/feedback/{entity}")
def revise_feedback(entity: str, body: dict, user=Depends(store.current_user)):
    prior = store.get_record(user["id"], "feedback", entity)
    revised = {**prior, **body}
    # Ownership and recommendation linkage cannot be reassigned through an edit.
    revised["recommendation_id"] = prior.get("recommendation_id")
    if revised["recommendation_id"]:
        revised["material"] = prior["material"]
    valid_feedback(revised)
    store.append(user["id"], "feedback", revised, entity, "revise")
    return {"ok": True, "data_version": store.version(user["id"])}


@router.delete("/feedback/{entity}")
def delete_feedback(entity: str, user=Depends(store.current_user)):
    store.append(user["id"], "feedback", {}, entity, "delete")
    return {"ok": True, "data_version": store.version(user["id"])}


@router.post("/feedback/{entity}/restore")
def restore_feedback(entity: str, user=Depends(store.current_user)):
    store.append(user["id"], "feedback", {}, entity, "restore")
    return {"ok": True, "data_version": store.version(user["id"])}


@router.get("/knowledge")
def knowledge(user=Depends(store.current_user)):
    return [{k: v for k, v in doc.items() if k not in {"chunks", "content_hex"}} | {"scope": scope} for scope in ("public", user["id"]) for doc in store.records(scope, "knowledge")]


@router.post("/knowledge")
async def upload(file: UploadFile = File(...), user=Depends(store.current_user)):
    content = await file.read(15*1024*1024+1)
    name = Path((file.filename or "document.txt").replace("\\", "/")).name
    payload = document_payload(user["id"], name, content)
    return {"id": store.append(user["id"], "knowledge", payload), "chunks": len(payload["chunks"])}


@router.get("/knowledge/{entity}/download")
def download(entity: str, user=Depends(store.current_user)):
    try:
        doc = store.get_record(user["id"], "knowledge", entity)
        owner = user["id"]
    except HTTPException:
        doc = store.get_record("public", "knowledge", entity)
        owner = "public"
    content = (get_settings().experiments_dir / "agent" / "blobs" / owner / doc["blob"]).read_bytes() if "blob" in doc else bytes.fromhex(doc["content_hex"])
    return Response(content, media_type="application/octet-stream", headers={"Content-Disposition": "attachment"})


@router.delete("/knowledge/{entity}")
def delete_knowledge(entity: str, user=Depends(store.current_user)):
    store.append(user["id"], "knowledge", {}, entity, "delete")
    return {"ok": True}


@router.post("/knowledge/import-public")
def import_public(user=Depends(store.administrator)):
    root = get_settings().project_root / "docs" / "literature"
    existing = {doc["name"] for doc in store.records("public", "knowledge")}
    imported, failed = [], []
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".pdf", ".md", ".txt", ".docx"} or path.name in existing:
            continue
        try:
            content = path.read_bytes()
            store.append("public", "knowledge", document_payload("public", path.name, content))
            imported.append(path.name)
        except HTTPException as exc:
            failed.append({"name": path.name, "reason": exc.detail})
    return {"imported": imported, "failed": failed}


@router.get("/legacy-feedback")
def legacy(user=Depends(store.administrator)):
    import json
    paths = [get_settings().feedback_jsonl, get_settings().data_dir / "user_experiments.jsonl"]
    claimed = {r["legacy_id"] for r in store.records("public", "claim")}
    result = []
    for path in paths:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    key = hashlib.sha256((path.name+line).encode()).hexdigest()
                    if key not in claimed:
                        result.append({"legacy_id": key, "payload": json.loads(line)})
    return result


@router.post("/legacy-feedback/{entity}/claim")
def claim(entity: str, body: dict, user=Depends(store.administrator)):
    item = next((r for r in legacy(user) if r["legacy_id"] == entity), None)
    if item is None:
        raise HTTPException(404, "待认领记录不存在")
    with store.database() as conn:
        owner = conn.execute("SELECT id FROM users WHERE username=?", (body.get("username"),)).fetchone()
    if not owner:
        raise HTTPException(404, "用户不存在")
    raw = item["payload"]
    payload = {"material": raw.get("material") or raw.get("task", {}).get("material"), "parameters": raw.get("selected_parameters") or {c: raw[c] for c in PARAMETER_COLUMNS if raw.get(c) is not None}, "quality": raw.get("measured_quality") or {c: raw[c] for c in QUALITY_COLUMNS if raw.get(c) is not None}, "legacy_id": entity}
    valid_feedback(payload)
    store.append(owner["id"], "feedback", payload, entity=entity)
    store.append("public", "claim", {"legacy_id": entity, "owner": owner["id"]}, entity=entity)
    return {"ok": True}
