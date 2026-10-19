from flask import Flask, request, jsonify, send_from_directory, send_file, make_response
from pathlib import Path
import yt_dlp, os, time

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(BASE_DIR / 'static'))

MUSIC_DIR = Path('/tmp/music')
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

search_cache = {}
CACHE_TIME = 600 

# ЭТА ФУНКЦИЯ ЗАПРЕЩАЕТ ТЕЛЕФОНУ КЭШИРОВАТЬ САЙТ
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

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
            res.append({'id': str(e['id']), 'title': e['title'], 'url': e['url'], 'thumb': thumb, 'artist': e.get('uploader', 'SoundCloud')})
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
    for f in os.listdir(MUSIC_DIR):
        if f.startswith(vid + '.'): return jsonify({'file': f})
    opts = {'format': 'bestaudio[ext=m4a]/bestaudio', 'outtmpl': str(MUSIC_DIR / f'{vid}.%(ext)s'), 'quiet': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([d['url']])
        for f in os.listdir(MUSIC_DIR):
            if f.startswith(vid + '.'): return jsonify({'file': f})
        return jsonify({'error': 'Файл не создался'})
    except Exception as ex: return jsonify({'error': str(ex)})

@app.route('/play/<f>')
def play(f):
    p = MUSIC_DIR / f
    return send_file(p, conditional=True) if p.exists() else ("Not found", 404)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
