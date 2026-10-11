---
title: Outbound HTTP API
parent: Outputs
nav_order: 6
description: "Send ScoreSight's readings to your own HTTP endpoint as JSON, XML, CSV or GET query parameters."
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
3. Choose the **method**: `POST` (the default), `PUT` or `GET`.
4. Choose the **Encode** format (used for `POST` and `PUT`): *JSON (Full)* (the default), *JSON (Simple key-value)*, *XML* or *CSV*.
5. Tick **Send out API requests to external services.**

## When requests are sent

- One request per **detection cycle** (see **Detections / s**).
- With *JSON (Full)*, *XML* and *CSV*, each request contains **all** boxes, whatever their state. This differs from the vMix/UNO/OBS outputs, which send only new values.
- *JSON (Simple key-value)* and the `GET` method can't carry a state, so they contain only **good** readings (`Success` or `SameNoChange`). A box whose latest reading was rejected or empty is left out, and no request is sent in a cycle where no box has a good reading.
- **Pause outputs** pauses the requests.
- Requests are sent in the background, with a 2-second timeout to connect and another 2 seconds to answer. If your endpoint is slower than the detection rate, ScoreSight skips intermediate cycles and sends only the most recent readings, so requests never pile up. If the endpoint can't be reached, ScoreSight retries with an increasing delay (up to 5 seconds) and sends the latest readings once it is back.
- Any **2xx** status (for example `200 OK` or `204 No Content`) counts as success. Other status codes, connection errors and timeouts are written to the ScoreSight log (see [Troubleshooting](#troubleshooting)).

Because every cycle is sent, the receiver should filter on the `state` of each reading (formats that include it) and/or ignore values that haven't changed.

{: .new }
In ScoreSight 0.2.0, *JSON (Simple key-value)* and `GET` send only good readings (0.1.x also sent rejected and empty ones), and any 2xx response counts as success (0.1.x expected exactly 200).

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

This format carries no state, so it contains only the boxes with a good reading (`Success` or `SameNoChange`). If you need to tell new, unchanged, rejected and empty readings apart, use *JSON (Full)*, *XML* or *CSV*.

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

With the `GET` method, the **Encode** setting is ignored. ScoreSight appends each box with a good reading as a URL query parameter (`name=value`, URL-encoded) to your URL and sends no body. Existing query parameters in your URL are kept.

```
GET http://192.168.1.10:8091/scores?Home+Score=65&Time=4%3A27
```

Like *JSON (Simple key-value)*, this carries no state, so only good readings (`Success` or `SameNoChange`) are included, and no request is sent when there are none.

### Encoding setting

The XML body is UTF-8 without an XML declaration, and all text is escaped. If the stored encoding is blank or unknown (for example in a hand-edited settings file), ScoreSight sends *JSON (Full)* and logs a warning once.

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

1. **Read the log** (**File > View Current Log**). Output API errors start with `Output API:` and the type of the error, for example:

   ```
   ERROR - output_worker - Output API: ConnectionError: HTTPConnectionPool(host='localahost', port=8091): Max retries exceeded ... Failed to resolve 'localahost'
   ERROR - output_worker - Output API: OutputError: POST http://192.168.1.10:8091/scores returned HTTP 500: Internal Server Error
   ```

   Common causes are a typo in the host name, "Connection refused" (nothing is listening on that port) or a timeout (firewall or wrong IP address). To keep the log readable, the same output logs at most one error every 30 seconds and adds `(N more error(s) since the last report were not logged)`. When the endpoint is reachable again, the log shows `Output API: connection restored`.
2. **`Output API: Invalid URL` or `Output API: no URL set` in the log**: the URL needs a scheme and host, such as `http://host:port/path`.
3. **Wrong format**: make sure the receiver expects the chosen encoding and method.
4. **Status code errors** (`returned HTTP 4xx/5xx`): your endpoint answered with an error status. Any 2xx status is fine. Check the endpoint's own logs.
5. **Nothing arrives with *JSON (Simple key-value)* or `GET`**: these send only good readings. If every box is yellow or red, nothing is sent. Check the boxes in ScoreSight, or use *JSON (Full)* to see every reading.
6. **Firewall**: when testing across computers, allow the receiver's port on the receiving computer.
7. Test with the receiver script above to find out whether the problem is ScoreSight or your endpoint.
