from flask import Flask, request, jsonify, abort
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry, multiprocess
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# In-memory store
items = []

# Metrics
HTTP_REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['method', 'route', 'code'])
HTTP_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'route', 'code'], buckets=(0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5))

# Additional metrics for richer visualization
HTTP_ERRORS = Counter('http_errors_total', 'Total HTTP error responses (>=500)', ['method', 'route', 'code'])
HTTP_SLOW = Counter('http_slow_requests_total', 'Number of requests exceeding slow threshold (seconds)', ['method', 'route'])
LAST_DURATION = Histogram('http_last_request_duration_seconds', 'Last request duration seconds', ['method', 'route'])

# Threshold (seconds) above which a request is considered "slow"
SLOW_THRESHOLD = 5.0

def with_metrics(route):
    def decorator(f):
        def wrapped(*args, **kwargs):
            import time
            # support simple simulation controls via query params for testing/visualization
            # ?delay=SECONDS to add artificial latency, ?fail=1 to force a 500
            delay = request.args.get('delay')
            if delay:
                try:
                    time.sleep(float(delay))
                except Exception:
                    pass
            if request.args.get('fail'):
                # simulate a server error
                abort(500)

            start = time.time()
            status = 200
            try:
                response = f(*args, **kwargs)
                # response can be (body, status) or a Flask Response
                if isinstance(response, tuple) and len(response) > 1 and isinstance(response[1], int):
                    status = response[1]
                elif hasattr(response, 'status_code'):
                    status = response.status_code
                return response
            except Exception as e:
                # If the exception is a Werkzeug HTTPException (abort(404), etc.)
                # capture its real status code (e.g. 404) instead of treating as 500.
                if isinstance(e, HTTPException) and getattr(e, 'code', None):
                    status = e.code
                else:
                    # mark as server error for unexpected exceptions
                    status = 500
                raise
            finally:
                duration = time.time() - start
                code = str(status)
                # core metrics
                HTTP_REQUESTS.labels(method=request.method, route=route, code=code).inc()
                HTTP_DURATION.labels(method=request.method, route=route, code=code).observe(duration)
                # extra metrics
                LAST_DURATION.labels(method=request.method, route=route).observe(duration)
                if int(code) >= 500:
                    HTTP_ERRORS.labels(method=request.method, route=route, code=code).inc()
                if duration >= SLOW_THRESHOLD:
                    HTTP_SLOW.labels(method=request.method, route=route).inc()
        wrapped.__name__ = f.__name__
        return wrapped
    return decorator

@app.route('/')
def index():
        """
        Index
        ---
        get:
            description: "Index page for the Flask CRUD app"
            responses:
                200:
                    description: OK
                    schema:
                        type: object
                        properties:
                            message:
                                type: string
                                example: Flask CRUD app with Prometheus metrics
        """
        return jsonify({'message': 'Flask CRUD app with Prometheus metrics'})

@app.route('/items', methods=['GET'])
@with_metrics('/items')
def list_items():
        """
        List items
        ---
        get:
            description: Get list of items
            responses:
                200:
                    description: A JSON array of items
                    schema:
                        type: array
                        items:
                            type: object
                            properties:
                                id:
                                    type: integer
                                data:
                                    type: object
        """
        return jsonify(items)

@app.route('/items', methods=['POST'])
@with_metrics('/items')
def create_item():
        """
        Create item
        ---
        post:
            description: Create a new item
            consumes:
                - application/json
            parameters:
                - in: body
                    name: body
                    required: false
                    schema:
                        type: object
            responses:
                201:
                    description: Created
                    schema:
                        type: object
                        properties:
                            id:
                                type: integer
                            data:
                                type: object
        """
        data = request.get_json() or {}
        item = {'id': len(items) + 1, 'data': data}
        items.append(item)
        return jsonify(item), 201

@app.route('/items/<int:item_id>', methods=['GET'])
@with_metrics('/items/<id>')
def get_item(item_id):
        """
        Get item
        ---
        get:
            description: Get an item by ID
            parameters:
                - name: item_id
                    in: path
                    type: integer
                    required: true
            responses:
                200:
                    description: The item
                    schema:
                        type: object
                        properties:
                            id:
                                type: integer
                            data:
                                type: object
                404:
                    description: Not found
        """
        for it in items:
                if it['id'] == item_id:
                        return jsonify(it)
        abort(404)

@app.route('/items/<int:item_id>', methods=['PUT'])
@with_metrics('/items/<id>')
def update_item(item_id):
        """
        Update item
        ---
        put:
            description: Update an item by ID
            parameters:
                - name: item_id
                    in: path
                    type: integer
                    required: true
                - in: body
                    name: body
                    required: false
                    schema:
                        type: object
            responses:
                200:
                    description: Updated item
                404:
                    description: Not found
        """
        data = request.get_json() or {}
        for it in items:
                if it['id'] == item_id:
                        it['data'] = data
                        return jsonify(it)
        abort(404)

@app.route('/items/<int:item_id>', methods=['DELETE'])
@with_metrics('/items/<id>')
def delete_item(item_id):
        """
        Delete item
        ---
        delete:
            description: Delete an item by ID
            parameters:
                - name: item_id
                    in: path
                    type: integer
                    required: true
            responses:
                204:
                    description: Deleted
                404:
                    description: Not found
        """
        global items
        for it in items:
                if it['id'] == item_id:
                        items = [x for x in items if x['id'] != item_id]
                        return '', 204
        abort(404)

# Expose metrics at /metrics using WSGI app
metrics_app = make_wsgi_app()
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/metrics': metrics_app})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
