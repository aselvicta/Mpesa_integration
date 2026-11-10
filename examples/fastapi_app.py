"""Minimal FastAPI integration.

    pip install "mpesa-tz[dotenv]" fastapi uvicorn
    uvicorn examples.fastapi_app:app --reload
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from mpesa_tz import MpesaAPIError, MpesaClient, MpesaError, callback_ack, parse_callback

app = FastAPI()
client = MpesaClient.from_env()


class PayIn(BaseModel):
    phone: str
    amount: float
    reference: str


@app.post("/pay")
async def pay(body: PayIn):
    try:
        # the client is synchronous and blocks until the customer answers
        result = await run_in_threadpool(client.stk_push, body.phone, body.amount, body.reference)
    except MpesaAPIError as exc:
        raise HTTPException(status_code=402, detail={"code": exc.code, "message": exc.description})
    except MpesaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.to_dict()


@app.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    result = parse_callback(await request.body())
    return callback_ack(result)
