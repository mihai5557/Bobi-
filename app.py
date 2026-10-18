from flask import Flask, request, jsonify, send_from_directory, send_file
import yt_dlp, os, time

app = Flask(__name__, static_folder='static')
# В облаке папку music нужно создавать в /tmp
os.makedirs('/tmp/music', exist_ok=True)

search_cache = {}
CACHE_TIME = 600 

@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q: return jsonify([])

    if q in search_cache and time.time() - search_cache[q]['time'] < CACHE_TIME:
        return jsonify(search_cache[q]['data'])

    opts = {'quiet': True, 'extract_flat': True, 'playlistend': 15, 'socket_timeout': 5}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f'scsearch15:{q}', download=False)
        
        res = []
        for e in info.get('entries', []):
            if not e: continue
            thumb = e['thumbnails'][-1]['url'] if e.get('thumbnails') else ''
            res.append({
                'id': str(e['id']), 'title': e['title'], 'url': e['url'], 
                'thumb': thumb, 'artist': e.get('uploader', 'SoundCloud')
            })
        
        search_cache[q] = {'time': time.time(), 'data': res}
        return jsonify(res)
    except Exception as ex: return jsonify({'error': str(ex)})

@app.route('/stream_url')
def stream_url():
    url = request.args.get('url')
    if not url: return jsonify({'error': 'no url'})
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            best_url = info.get('url')
            for f in info.get('formats', []):
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    best_url = f['url']
            return jsonify({'stream_url': best_url})
    except Exception as e: return jsonify({'error': str(e)})

@app.route('/download', methods=['POST'])
def download():
    d = request.json
    vid = str(d['id'])
    for f in os.listdir('/tmp/music'):
        if f.startswith(vid + '.'): return jsonify({'file': f})
            
    opts = {'format': 'bestaudio[ext=m4a]/bestaudio', 'outtmpl': f'/tmp/music/{vid}.%(ext)s', 'quiet': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([d['url']])
        for f in os.listdir('/tmp/music'):
            if f.startswith(vid + '.'): return jsonify({'file': f})
        return jsonify({'error': 'Файл не создался'})
    except Exception as ex: return jsonify({'error': str(ex)})

@app.route('/play/<f>')
def play(f):
    p = f'/tmp/music/{f}'
    return send_file(p, conditional=True) if os.path.exists(p) else ("Not found", 404)

if __name__ == '__main__':
    # Это нужно, чтобы Render правильно запустил сервер
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
