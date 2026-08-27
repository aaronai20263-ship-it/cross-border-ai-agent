from backend.server import init_db, ThreadingHTTPServer, Handler, os

if __name__ == '__main__':
    init_db()
    port = int(os.getenv('PORT', '8000'))
    print(f'玉石 AI 智能顾问: http://localhost:{port}')
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
