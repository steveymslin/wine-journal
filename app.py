import os, json, base64, uuid, io
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response
import anthropic
import urllib.request
import urllib.error
import urllib.parse

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
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            return json.loads(body) if body.strip() else []
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        raise Exception(f"Supabase error {e.code}: {err_body}")

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/wines', methods=['GET'])
def get_wines():
    try:
        search = request.args.get('q', '').strip()
        if search:
            enc = urllib.parse.quote(search)
            path = f'wines?or=(name.ilike.*{enc}*,producer.ilike.*{enc}*,major_region.ilike.*{enc}*,country.ilike.*{enc}*,appellation.ilike.*{enc}*,grape.ilike.*{enc}*)&order=created_at.desc'
        else:
            path = 'wines?order=created_at.desc'
        wines = supabase_request('GET', path)
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

@app.route('/api/wines/<wine_id>', methods=['PUT'])
def update_wine(wine_id):
    try:
        data = request.json
        data.pop('id', None)
        data.pop('created_at', None)
        result = supabase_request('PATCH', f'wines?id=eq.{wine_id}', data)
        return jsonify(result[0] if isinstance(result, list) and result else data)
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
    # Handle WSET tasting note generation (JSON body, no image)
    if request.is_json:
        data = request.get_json()
        if data.get('wset_mode'):
            if not ANTHROPIC_API_KEY:
                return jsonify({'error': 'ANTHROPIC_API_KEY not configured'}), 400
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            msg = client.messages.create(
                model='claude-opus-4-5',
                max_tokens=800,
                messages=[{'role': 'user', 'content': data.get('prompt', '')}]
            )
            note = msg.content[0].text.strip()
            return jsonify({'tasting_note': note})

    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    img_bytes = file.read()
    b64 = base64.standard_b64encode(img_bytes).decode()
    mime = file.content_type or 'image/jpeg'

    if not ANTHROPIC_API_KEY:
        return jsonify({'error': 'ANTHROPIC_API_KEY not configured'}), 400

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=600,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}},
                {'type': 'text', 'text': (
                    'You are a wine expert. Carefully read this wine label.\n'
                    'Return ONLY valid JSON, no markdown, no explanation:\n'
                    '{"name":"wine name","producer":"producer or domaine",'
                    '"grape":"grape variety or blend","vintage":"year or empty",'
                    '"country":"country e.g. France",'
                    '"major_region":"major wine region e.g. Bordeaux, Burgundy, Champagne, Tuscany",'
                    '"subregion":"sub-region e.g. Medoc, Cote de Nuits",'
                    '"appellation":"specific appellation e.g. Pauillac, Gevrey-Chambertin, Maranges",'
                    '"style":"one of: Red, White, Sparkling, Fortified, Rose"}\n'
                    'Use empty string for any field not visible.'
                )}
            ]
        }]
    )

    text = msg.content[0].text.strip()
    start, end = text.find('{'), text.rfind('}') + 1
    if start >= 0 and end > start:
        return jsonify(json.loads(text[start:end]))
    return jsonify({'error': 'Could not parse label', 'raw': text}), 500


@app.route('/api/price-check', methods=['POST'])
def price_check():
    if not ANTHROPIC_API_KEY:
        return jsonify({'error': 'ANTHROPIC_API_KEY not configured'}), 400

    data = request.get_json()
    wine_desc = data.get('wine', '')

    if not wine_desc:
        return jsonify({'error': 'No wine description provided'}), 400

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_prompt = (
        f"What is the current retail price for this wine: {wine_desc}? "
        f"Reply in this exact format: PRICE_RANGE: $XX - $XX USD | TYPICAL_PRICE: $XX USD. "
        f"Keep it brief, just the prices."
    )

    try:
        # web_search_20250305 is server-side: Anthropic handles search internally.
        # Just call once and the model returns text after searching.
        msg = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=400,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{'role': 'user', 'content': user_prompt}]
        )
        # Extract all text blocks from response
        text_parts = [b.text for b in msg.content if hasattr(b, 'text') and b.text]
        result = ' '.join(text_parts).strip()
        if result:
            return jsonify({'result': result})
        raise Exception("Empty response")

    except Exception as e:
        # Fallback: use training knowledge without web search
        try:
            msg = client.messages.create(
                model='claude-sonnet-4-5',
                max_tokens=300,
                messages=[{'role': 'user', 'content': user_prompt + " Use your best estimate from training data."}]
            )
            result = msg.content[0].text.strip()
            return jsonify({'result': result + ' (estimated)'})
        except Exception as e2:
            return jsonify({'error': str(e2)}), 500

@app.route('/api/export', methods=['GET'])
def export_excel():
    try:
        import csv, io
        wines = supabase_request('GET', 'wines?order=created_at.desc')
        output = io.StringIO()
        fields = ['name','producer','grape','vintage','style','country','major_region','subregion','appellation','price','score','date','comment']
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for w in wines:
            writer.writerow({f: w.get(f,'') for f in fields})
        csv_bytes = output.getvalue().encode('utf-8-sig')
        return Response(
            csv_bytes,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=wine_journal.csv'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'\n🍷  Wine Journal running at http://localhost:{port}\n')
    app.run(debug=False, host='0.0.0.0', port=port)
