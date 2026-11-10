"""Minimal Flask integration.

    pip install "mpesa-tz[dotenv]" flask
    flask --app examples/flask_app.py run
"""

from flask import Flask, jsonify, request

from mpesa_tz import MpesaAPIError, MpesaClient, MpesaError, callback_ack, parse_callback

app = Flask(__name__)
client = MpesaClient.from_env()


@app.post("/pay")
def pay():
    data = request.get_json(force=True)
    try:
        result = client.stk_push(data["phone"], data["amount"], data["reference"])
    except MpesaAPIError as exc:
        return jsonify(ok=False, code=exc.code, message=exc.description), 402
    except MpesaError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    return jsonify(ok=True, **result.to_dict())


@app.post("/mpesa/callback")
def mpesa_callback():
    result = parse_callback(request.get_data())
    # TODO: update your order using result.third_party_conversation_id
    return jsonify(callback_ack(result))
