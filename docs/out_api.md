---
title: Outbound HTTP API
parent: Outputs
nav_order: 6
description: "Send every ScoreSight reading to your own HTTP endpoint as JSON, XML, CSV or GET query parameters."
---

# Outbound HTTP API
{: .no_toc }

The **API** tab sends the readings to a URL of your choice on every detection cycle. Use it to feed your own server, a cloud function, a database, or automation tools such as Node-RED, n8n or Home Assistant webhooks.

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Setup

![The API tab](image-29.png)

1. Open the **API** tab.
2. Enter the **URL** of your endpoint, including the scheme and host, for example `http://192.168.1.10:8091/scores`.
3. Choose the **method**: `POST`, `PUT` or `GET`.
4. Choose the **Encode** format (used for `POST` and `PUT`): *JSON (Full)*, *JSON (Simple key-value)*, *XML* or *CSV*.
5. Tick **Send out API requests to external services.**

## When requests are sent

- One request per **detection cycle** (see **Detections / s**). Each request contains **all** boxes, whatever their state. This differs from the vMix/UNO/OBS outputs, which send only new values.
- **Stop Updates** pauses the requests.
- Requests are sent in the background with a timeout. If your endpoint is slower than the detection rate, ScoreSight skips intermediate cycles and sends the most recent readings, so requests never pile up.
- Respond with HTTP **200**. Other status codes, connection errors and timeouts are written to the ScoreSight log.

Because every cycle is sent, the receiver should filter on the `state` of each reading (formats that include it) and/or ignore values that haven't changed.

## Payload formats

The examples show two boxes. `rect` / `x`, `y`, `width`, `height` give the box position in pixels.

### JSON (Full)

`Content-Type: application/json`

```json
[
  {"name": "Home Score", "text": "65", "state": "SameNoChange",
   "rect": {"x": 525.9, "y": 638.4, "width": 214.6, "height": 175.3}},
  {"name": "Time", "text": "4:27", "state": "Success",
   "rect": {"x": 843.6, "y": 663.0, "width": 359.1, "height": 207.2}}
]
```

`state` is one of `Success`, `SameNoChange`, `FailedFilter` or `Empty` (see [States](http_server.md#states)).

### JSON (Simple key-value)

`Content-Type: application/json`

```json
{"Home Score": "65", "Time": "4:27"}
```

This format carries no state. If you need to tell new, unchanged, rejected and empty readings apart, use *JSON (Full)*, *XML* or *CSV*.

### XML

`Content-Type: application/xml`

```xml
<root>
  <result name="Home Score" result="65" result_state="SameNoChange" x="525.9" y="638.4" width="214.6" height="175.3" />
  <result name="Time" result="4:27" result_state="Success" x="843.6" y="663.0" width="359.1" height="207.2" />
</root>
```

### CSV

`Content-Type: text/csv`

```csv
Name,Text,State,X,Y,Width,Height
Home Score,65,SameNoChange,525.9,638.4,214.6,175.3
Time,4:27,Success,843.6,663.0,359.1,207.2
```

### GET (query parameters)

With the `GET` method, the **Encode** setting is ignored. ScoreSight appends each box as a URL query parameter (`name=value`, URL-encoded) to your URL and sends no body. Existing query parameters in your URL are kept.

```
GET http://192.168.1.10:8091/scores?Home+Score=65&Time=4%3A27
```

Like *JSON (Simple key-value)*, this carries no state.

## Authentication

ScoreSight cannot add custom HTTP headers. If your endpoint needs a key, put it in the URL, for example `https://example.com/hook?token=SECRET`, or run a small relay on your network that adds the header. Always use `https://` for endpoints outside your local network. The URL (including any token) is stored in plain text in the ScoreSight settings file.

## Test receiver (Python)

This script prints whatever ScoreSight sends. It needs only the Python standard library:

```python
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8") if length else ""
        print(f"{self.command} {self.path}  [{self.headers.get('Content-Type')}]")
        if body:
            print(body)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    do_GET = do_POST = do_PUT = _handle

    def log_message(self, *args):
        pass  # keep the console readable


if __name__ == "__main__":
    port = 8091
    print(f"Listening on http://localhost:{port}")
    HTTPServer(("", port), Handler).serve_forever()
```

1. Save it as `scoresight_receiver.py` and run `python scoresight_receiver.py`.
2. In ScoreSight, set the URL to `http://localhost:8091`, then choose a method and encoding.
3. Tick **Send out API requests to external services.** The requests appear in the console.

## Troubleshooting

1. **Read the log** (**File > View Current Log**). Errors look like this:

   ```
   ERROR - api_output - Error sending data to output API: http://localahost:8091, HTTPConnectionPool(host='localahost', port=8091): Max retries exceeded ... Failed to resolve 'localahost'
   ```

   Common causes are a typo in the host name, "Connection refused" (nothing is listening on that port) or a timeout (firewall or wrong IP address).
2. **"Invalid URL" in the log**: the URL needs a scheme and host, such as `http://host:port/path`.
3. **Wrong format**: make sure the receiver expects the chosen encoding and method.
4. **Status code errors**: your endpoint returned something other than 200. Check the endpoint's own logs.
5. **Firewall**: when testing across computers, allow the receiver's port on the receiving computer.
6. Test with the receiver script above to find out whether the problem is ScoreSight or your endpoint.
