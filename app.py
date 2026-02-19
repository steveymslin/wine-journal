import os, json, base64, uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import anthropic
import urllib.request
import urllib.error

app = Flask(__name__, static_folder='static')

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

def supabase_request(method, path, data=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('apikey', SUPABASE_KEY)
    req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Prefer', 'return=representation')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/wines', methods=['GET'])
def get_wines():
    try:
        wines = supabase_request('GET', 'wines?order=created_at.desc')
        return jsonify(wines)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/wines', methods=['POST'])
def add_wine():
    try:
        wine = request.json
        wine['id'] = str(uuid.uuid4())
        wine.setdefault('created_at', datetime.utcnow().isoformat())
        result = supabase_request('POST', 'wines', wine)
        return jsonify(result[0] if isinstance(result, list) else result), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/wines/<wine_id>', methods=['DELETE'])
def delete_wine(wine_id):
    try:
        supabase_request('DELETE', f'wines?id=eq.{wine_id}')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_label():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    img_bytes = file.read()
    b64 = base64.standard_b64encode(img_bytes).decode()
    mime = file.content_type or 'image/jpeg'

    api_key = ANTHROPIC_API_KEY
    if not api_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY not configured on server'}), 400

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=500,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}},
                {'type': 'text', 'text': (
                    'You are a wine expert. Carefully read this wine label.\n'
                    'Return ONLY valid JSON, no markdown, no explanation:\n'
                    '{"name":"wine name","producer":"producer or domaine","grape":"grape variety",'
                    '"vintage":"year or empty","region":"region or appellation","country":"country"}\n'
                    'Use empty string for any field not visible on the label.'
                )}
            ]
        }]
    )

    text = msg.content[0].text.strip()
    start, end = text.find('{'), text.rfind('}') + 1
    if start >= 0 and end > start:
        return jsonify(json.loads(text[start:end]))
    return jsonify({'error': 'Could not read label', 'raw': text}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'\n🍷  Wine Journal running at http://localhost:{port}\n')
    app.run(debug=False, host='0.0.0.0', port=port)
