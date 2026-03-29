import os, json, base64
from flask import Flask, request, jsonify, send_from_directory
import anthropic

app = Flask(**name**, static_folder=‘static’)
ANTHROPIC_API_KEY = os.environ.get(‘ANTHROPIC_API_KEY’, ‘’)

@app.route(’/’)
def index():
return send_from_directory(‘static’, ‘index.html’)

@app.route(’/sw.js’)
def service_worker():
resp = send_from_directory(‘static’, ‘sw.js’)
resp.headers[‘Service-Worker-Allowed’] = ‘/’
resp.headers[‘Cache-Control’] = ‘no-cache’
return resp

@app.route(’/manifest.json’)
def manifest():
return send_from_directory(‘static’, ‘manifest.json’)

@app.route(’/icon-192.png’)
def icon192():
return send_from_directory(‘static’, ‘icon-192.png’)

@app.route(’/icon-512.png’)
def icon512():
return send_from_directory(‘static’, ‘icon-512.png’)

@app.route(’/api/health’)
def health():
return jsonify({“status”: “ok”, “anthropic_key”: bool(ANTHROPIC_API_KEY)})

@app.route(’/api/analyze’, methods=[‘POST’])
def analyze_label():
if request.is_json:
data = request.get_json()
if data.get(‘wset_mode’):
if not ANTHROPIC_API_KEY:
return jsonify({‘error’: ‘ANTHROPIC_API_KEY not configured’}), 400
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
msg = client.messages.create(
model=‘claude-opus-4-5’, max_tokens=800,
messages=[{‘role’: ‘user’, ‘content’: data.get(‘prompt’, ‘’)}]
)
return jsonify({‘tasting_note’: msg.content[0].text.strip()})

```
if 'image' not in request.files:
    return jsonify({'error': 'No image provided'}), 400

file = request.files['image']
b64 = base64.standard_b64encode(file.read()).decode()
mime = file.content_type or 'image/jpeg'

if not ANTHROPIC_API_KEY:
    return jsonify({'error': 'ANTHROPIC_API_KEY not configured'}), 400

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
msg = client.messages.create(
    model='claude-opus-4-5', max_tokens=600,
    messages=[{'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}},
        {'type': 'text', 'text': (
            'You are a wine expert. Carefully read this wine label.\n'
            'Return ONLY valid JSON, no markdown, no explanation:\n'
            '{"name":"wine name","producer":"producer or domaine",'
            '"grape":"grape variety or blend","vintage":"year or empty",'
            '"country":"country e.g. France",'
            '"major_region":"top-level wine region in English e.g. Bordeaux, Burgundy, Champagne, Tuscany, Southwest France, Rioja, Rhone Valley",'
            '"subregion":"sub-region within major region e.g. Medoc, Cote de Nuits, Pyrenees. Use empty string if unclear.",'
            '"appellation":"the specific AOC/appellation name on the label e.g. Pauillac, Saint-Estephe, Gevrey-Chambertin, Jurancon Sec, Barolo. Usually the most prominent geographic name shown on the label.",'
            '"style":"one of: Red, White, Sparkling, Fortified, Rose"}\n'
            'Use empty string for any field not visible.'
        )}
    ]}]
)
text = msg.content[0].text.strip()
start, end = text.find('{'), text.rfind('}') + 1
if start >= 0 and end > start:
    return jsonify(json.loads(text[start:end]))
return jsonify({'error': 'Could not parse label', 'raw': text}), 500
```

@app.route(’/api/pronounce’, methods=[‘POST’])
def pronounce():
if not ANTHROPIC_API_KEY:
return jsonify({‘error’: ‘ANTHROPIC_API_KEY not configured’}), 400

```
data = request.get_json()
wine_desc = data.get('wine', '')
if not wine_desc:
    return jsonify({'error': 'No wine provided'}), 400

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

prompt = (
    f"You are a wine pronunciation expert. For this wine: {wine_desc}\n\n"
    "Provide the pronunciation guide. Return ONLY valid JSON, no markdown:\n"
    '{"phonetic":"phonetic spelling using simple English sounds e.g. zhev-RAY shahm-behr-TAN",'
    '"syllables":"syllable breakdown with stress in CAPS e.g. zhev-RAY · shahm-behr-TAN",'
    '"guide":"2-3 sentences: language of origin, how to say each key word, any tricky sounds",'
    '"tip":"one short practical tip for ordering this wine confidently in a restaurant"}'
    "\nKeep it practical and concise. Use simple phonetics an English speaker can read."
)

try:
    msg = client.messages.create(
        model='claude-sonnet-4-5',
        max_tokens=400,
        messages=[{'role': 'user', 'content': prompt}]
    )
    text = msg.content[0].text.strip()
    start, end = text.find('{'), text.rfind('}') + 1
    if start >= 0 and end > start:
        import json
        return jsonify({'result': json.loads(text[start:end])})
    return jsonify({'error': 'Could not parse response'}), 500
except Exception as e:
    return jsonify({'error': str(e)}), 500
```

@app.route(’/api/price-check’, methods=[‘POST’])
def price_check():
if not ANTHROPIC_API_KEY:
return jsonify({‘error’: ‘ANTHROPIC_API_KEY not configured’}), 400
data = request.get_json()
wine_desc = data.get(‘wine’, ‘’)
if not wine_desc:
return jsonify({‘error’: ‘No wine description’}), 400

```
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
prompt = (f"What is the current retail price for: {wine_desc}? "
          f"Reply: PRICE_RANGE: $XX - $XX USD | TYPICAL_PRICE: $XX USD. Brief only.")
try:
    msg = client.messages.create(
        model='claude-sonnet-4-5', max_tokens=400,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{'role': 'user', 'content': prompt}]
    )
    parts = [b.text for b in msg.content if hasattr(b, 'text') and b.text]
    result = ' '.join(parts).strip()
    if result:
        return jsonify({'result': result})
    raise Exception("Empty")
except Exception:
    try:
        msg = client.messages.create(
            model='claude-sonnet-4-5', max_tokens=300,
            messages=[{'role': 'user', 'content': prompt + " Best estimate from training."}]
        )
        return jsonify({'result': msg.content[0].text.strip() + ' (estimated)'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

if **name** == ‘**main**’:
port = int(os.environ.get(‘PORT’, 5000))
app.run(debug=False, host=‘0.0.0.0’, port=port)
