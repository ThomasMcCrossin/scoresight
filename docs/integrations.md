---
title: Works With…
parent: Outputs
nav_order: 8
description: "Which broadcast and streaming products ScoreSight works with (vMix, OBS, overlays.uno, Wirecast, NewBlue Captivate, Ross XPression, SuiteCG, TriCaster, Epiphan Pearl, CasparCG, Singular.live, Chyron PRIME and more), and how to set each one up."
---

# Works With…
{: .no_toc }

ScoreSight's readings can reach most broadcast graphics and streaming products through one of its [outputs](outputs.md): a built-in integration, the [text files](text-files.md), the [HTTP server](http_server.md) that products poll, or the [outbound HTTP API](out_api.md) that pushes to products. This page lists 21 products, says how well each works today, and has short setup guides.

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

{: .important }
**Untested** means the setup follows the product's documentation but the ScoreSight project hasn't tried it on that product yet. If you try one, please tell us how it went (or what had to change) in a [GitHub issue](https://github.com/royshil/scoresight/issues/new/choose), so we can mark it tested.

{: .note }
**Products that can show a web page** (OBS, vMix, Wirecast, CasparCG, TriCaster Live Link, Magewell Director, Epiphan Pearl and others) can also use ScoreSight's own [browser overlays](overlays.md): a transparent scorebug, lower third, clock or field, or your own HTML, updated live as values change.

## At a glance

| Product | Status | How | Guide |
|---|---|---|---|
| **vMix** | Works | Built-in vMix output (Web API `SetText`). Untested alternative: a Data Source on `/xml?pivot&all`, `/csv?pivot&all` or `/json?array` | [vMix](vmix.md) |
| **OBS Studio** | Works | Built-in OBS output (WebSocket); or a Browser Source on `/scoresight`, or *Text (Read from file)* | [OBS Studio](obs.md) |
| **overlays.uno** | Works | Built-in UNO output | [Overlays.uno](uno.md) |
| **Wirecast** | Works, untested | Text sources reading the per-field `.txt` files; or a Web Page source | [Wirecast](#wirecast) |
| **NewBlue Captivate** | Works, untested | Outbound API push to Captivate's Simple Variable Update; or Captivate's JSON/XML reader polling ScoreSight | [NewBlue Captivate](#newblue-captivate) |
| **Ross XPression** | Works, untested (needs the DataLinq option) | DataLinq RSS/HTTP source polling `/csv?pivot&all`; or a Text source on `results.csv` | [Ross XPression](#ross-xpression) |
| **SuiteCG** | Works, untested (0.7.136 or later) | Data Automation polling `/json?pivot&all`, or reading `results.json` / `results.txt` | [SuiteCG](#suitecg) |
| **TriCaster** (Vizrt) | Works, untested | Outbound API preset **TriCaster DataLink**; or a Live Link web buffer | [TriCaster](#tricaster) |
| **Epiphan Pearl** | Works, untested | Outbound API preset **Epiphan Pearl** (custom variables) | [Epiphan Pearl](#epiphan-pearl) |
| **Magewell Director** | Partly, untested | A Webpage GFX showing an HTML page; the built-in scoreboards only for scores | [Magewell Director](#magewell-director) |
| **CasparCG** | Partly, untested | An HTML template that polls `/json?pivot&all` | [CasparCG](#casparcg) |
| **Singular.live** | Partly, untested | Outbound API to a Data Stream, plus a composition script | [Singular.live](#singularlive) |
| **Viz Flowics** | Partly, untested | Outbound API to a JSON HTTP Push input; or the Data Bridge polling ScoreSight | [Viz Flowics](#viz-flowics) |
| **Chyron PRIME** | Partly, untested | A Data object polling `/json?pivot&all`, with a timer that runs Update | [Chyron PRIME](#chyron-prime) |
| **Vizrt** (Viz Engine, Trio, Pilot) | Partly, untested | A Vizrt Datacenter REST dataset polling `/json?pivot&all` (needs a Datacenter licence); or through Viz Flowics | [Vizrt Datacenter REST](https://documentation.vizrt.com/datacenter-user-guide/2.5/Rest_Webserver_Dataset.html) |
| **ClassX LiveBoard** | Partly, untested | A DataSource on `results.csv` or `/csv?pivot&all` with auto-update | [LiveBoard](https://www.for-a.com/products/liveboard/) |
| **wTVision** | Partly, untested | Studio CG data sources on the files or `/xml?pivot&all` (usually set up by wTVision) | [Studio CG](https://www.wtvision.com/files/studio_en.pdf) |
| **Live Score** (live-score-app.com) | Not yet | Needs a TCP output, which ScoreSight doesn't have yet | [Live Score](https://www.live-score-app.com/) |
| **MagicSoft CG** | Not yet | Needs a TCP socket output, which ScoreSight doesn't have yet | [MagicSoft CG](https://magicsoft.tv/cg.html) |
| **Grafster** (Converge Horizons) | Not yet | Its data feed protocol isn't published | [Grafster](https://convergetech.com/Products/Grafster/grafster.html) |
| **RT Software Swift** | Not yet | Needs a Swift Web API (WebSocket) output | [Swift API](https://rtsw.co.uk/all-products/api-control/) |

**Which output for which kind of product:**

| The product can... | ScoreSight output | Shape |
|---|---|---|
| poll a URL for JSON, XML or CSV | [HTTP server](http_server.md) | `/json?pivot&all` (one object), `/json?array` (an array of one row), `/xml?pivot&all`, `/csv?pivot&all` (a header and one row) |
| read a file | [Text files](text-files.md) | `<Box Name>.txt` (one value), `results.csv`, `results.xml`, `results.json` (one object), `results.txt` (`key=value` lines) |
| receive HTTP requests | [Outbound HTTP API](out_api.md) | One request per cycle or per field, JSON/XML/CSV or GET, with headers, a rate limit and presets |
| show a web page | [HTTP server](http_server.md) | The demo page `/scoresight`, or your own page polling `/json?pivot&all` |

{: .tip }
Use the `&all` variants for programs that bind to a column or a key: every field is always there, with its last good value. The plain `?pivot` leaves out a field whose reading was rejected for a moment, and some programs blank the field or lose the column then.

## Wirecast

**Works, untested.** Wirecast's Text source can keep reading a text file, so it shows the per-field `.txt` files of the Text files output. Wirecast has no API to set text, so this (or a web page) is the way in.

1. In ScoreSight, select **Text files** in the Outputs list, choose a folder, keep **Append** on *Don't append results*, and set **Save / s** to 5–10.
2. In Wirecast, add a **Text** source to a shot layer, set **Mode** to **File**, pick for example `Home Score.txt` in that folder, and tick **Keep reading text file continuously**.
3. Style it (font, size, colour, alignment) and position it. Repeat for `Away Score.txt`, `Time.txt`, `Period.txt` and so on. Put a background image under the text layers to build a scorebug shot.

Alternative: a **Web Page** source with the URL `http://<scoresight-ip>:18099/scoresight` (the demo page) or your own page that polls `/json?pivot&all`, with **Transparent Background** ticked.

Notes: each field needs its own Text source. The text changes at the **Save / s** rate plus Wirecast's own file polling (expect up to about a second). Wirecast's built-in Scoreboard source can't take data. Vendor docs: [Wirecast User Guide](https://www.telestream.net/pdfs/user-guides/wirecast/Wirecast-16-User-Guide-Windows.pdf) (Text source, Web Page source).

## NewBlue Captivate

**Works, untested.** Two ways: ScoreSight pushes the values to Captivate (push), or Captivate reads them from ScoreSight (pull). In both, name the graphic's text variables exactly like the ScoreSight fields (`Home Score`, `Away Score`, `Time`...).

**Push** (Captivate Broadcast; whether the Sport edition accepts it is unverified):

1. In Captivate's Designer, make the graphic's text layers variables named like the ScoreSight fields, and keep the changes.
2. In ScoreSight, select **HTTP API** in the Outputs list and set:
   - **URL**: `http://<captivate-ip>:9022/api/action/still/title/<Title%20Name>` (the title's name, percent-encoded; `update` instead of `still` animates the change; `/input/<input name>` instead of `/title/...` targets every title on an input);
   - method **POST**, **Encode** *JSON (Simple key-value)*;
   - **Send**: tick **Only changes**, so Captivate gets a request only when a value changed (leave **Fields** on *All in one request*).
3. Tick **Send out API requests to external services.** and allow TCP port 9022 through the Captivate computer's firewall.

To test without ScoreSight: `curl -H "Content-Type: application/json" --data "{\"Home Score\":\"21\"}" "http://<captivate-ip>:9022/api/action/still/title/<Title%20Name>"`.

**Pull** (Sport and Broadcast):

1. Select the graphic, then **Select a data controller** > **General** > **JSON** > **New Input**.
2. Enter `http://<scoresight-ip>:18099/json?pivot&all` (or use the XML reader with `http://<scoresight-ip>:18099/xml?pivot&all`, whose element names have no spaces: `HomeScore`).
3. Open **Link Data** and drag each variable onto its text object.

Notes: Captivate's documentation mentions network and FTP addresses for the readers; whether it accepts a plain `http://` address, and how often it reads it, isn't documented. Vendor docs: [Simple Variable Update over HTTP](https://developers.newbluefx.com/captivate-api/advanced-api-reference/tcp-udp-and-http-connections), [Connect JSON feed data to a graphic layer](https://newbluefx.zendesk.com/hc/en-us/articles/17148309903899-Connect-JSON-feed-data-to-a-graphic-layer).

## Ross XPression

**Works, untested.** Needs XPression's **DataLinq** option and a running DataLinq Server (DataLinq also works in the XPression Trial Edition).

1. In ScoreSight, give the fields their final names and note the computer's IP address. The HTTP server listens on port 18099.
2. In **XPression DataLinq Server**, choose **Add New** > **RSS / HTTP DataLinq Source**:
   - method GET, URL `http://<scoresight-ip>:18099/csv?pivot&all`, **Format** *Text*;
   - **Delimiter** *Comma*, tick **Text File has Header Row**;
   - **Update Interval** 250–500 ms, **Mode** *Static URL*.
3. Name the source (for example *ScoreSight*) and use **Browse** to check that it shows one row with a column per field.
4. In XPression, for each text object: **Object Inspector** > **Data Source** > **DataLinq** > **Set**, tick **Enabled**, pick the ScoreSight source, browse to the column (for example *Home Score*) in row 1, and tick **Live Update**.

`&all` keeps every column in the data, with its last good value, so a column never disappears while a reading is rejected. Instead of CSV you can use `/json?pivot&all` with **Format** *JSON*, or `/xml?pivot&all` with *XML*.

File alternative: tick **Save .csv file** in the Text files output and add a **Text DataLinq Source** on `results.csv` (header row ticked, poll every 1 s, tick **Allow reading of files that are currently being written**). Its first column is `Timestamp`.

Notes: XPression updates as often as it polls; ScoreSight can't trigger takes or animations. Vendor docs: [XPression User Guide 12.6](https://documentation.rossvideo.com/files/Manuals/CG%20and%20Graphics/XPression/User%20Guides/XPression%20User%20Guide%20%283500DR-001-12.6%29.pdf) (DataLinq sources), [DataLinq and Scoreboard Sources](https://documentation.rossvideo.com/files/Manuals/CG%20and%20Graphics/XPression/Application%20Notes/XPression%20DataLinq%20and%20Scoreboard%20Sources%20%283500DR-550-01%20Rev%203%29.pdf).

## SuiteCG

**Works, untested.** SuiteCG's **Data Automation** (version 0.7.134 and later) reads basic XML, JSON, CSV and `key=value` TXT data from a file or over HTTP.

1. Install SuiteCG **0.7.136 or later**: it fixes a crash on data keys with a space, such as `Home Score`. (If your copy is licensed, deactivate the licence before upgrading, as SuiteCG asks.)
2. In ScoreSight, check in a browser that `http://<scoresight-ip>:18099/json?pivot&all` shows the values.
3. In Data Automation, add a JSON source over HTTP with that URL. Or, from a file: tick **Save .json file** (or **Save key=value .txt file**) in the Text files output and point SuiteCG at `results.json` (or `results.txt`) in the output folder. On an older SuiteCG, use `http://<scoresight-ip>:18099/xml?pivot&all`, whose element names have no spaces.
4. Map the keys: *Time* to the game clock, *Home Score* and *Away Score* to the score counters, *Period* to the period counter, possession or bonus to toggles. Export the mapping profile to reuse it.
5. Check that SuiteCG accepts ScoreSight's clock text (`4:30`, `04:30` or `45.3`); if not, change the box's [Format](box-settings.md#format).

Notes: SuiteCG automates clocks, counters, toggles and basic team details; macros and animations stay manual. Its polling interval and accepted JSON shapes aren't documented. Vendor notes: [Data Automation (0.7.134)](https://suitecg.com/2026/08/10/changelog-0-7-134/), [0.7.136](https://suitecg.com/2026/08/18/changelog-0-7-136/), [TXT as key=value](https://suitecg.com/2024/09/03/coming-soon-external-data-football-updates/).

## TriCaster

**Works, untested.** TriCaster's **DataLink** keys show live values in title pages (also while they are on air): ScoreSight sets one key per field over TriCaster's HTTP API.

1. In ScoreSight, select **HTTP API** in the Outputs list and pick **TriCaster DataLink** in **Preset**. The URL becomes:

   ```
   http://admin:admin@TRICASTER-IP/v1/datalink?key={field}&value={value}
   ```

2. Replace `TRICASTER-IP` with the TriCaster's IP address, and `admin:admin` with its login if you changed it. (ScoreSight uses Basic or Digest authentication, whichever the TriCaster asks for.)
3. Tick **Send out API requests to external services.** ScoreSight now sends `GET /v1/datalink?key=Home%20Score&value=21` and so on: one request per changed field, at most 10 per second.
4. In a TriCaster title, type `%` in a text line and pick the key: **each field is a DataLink key named exactly like the field**, so `%Home Score%` shows the Home Score field and `%Time%` the clock. The HTTP API page lists the keys (*DataLink keys: %Home Score%, %Time%...*). A fallback for an empty key: `%{Home Score, "0"}%`.

To check: open `http://TRICASTER-IP/v1/datalink` in a browser; it lists the DataLink keys and their values.

Unverified: whether DataLink accepts keys with spaces over HTTP. If `%Home Score%` stays empty, tick **Letters, digits and _ only** on the HTTP API page and use `%home_score%`. The highest update rate TriCaster accepts for titles on air isn't documented: lower **Rate** if updates lag.

Alternative without DataLink: a **Live Link** web buffer (one of the first 10 buffers, newer TriCaster software) showing `http://<scoresight-ip>:18099/scoresight` or your own overlay page, keyed with a DSK.

Vendor docs: [TriCaster Automation and Integration Guide](https://downloads.newtek.com/LiveProductionSystems/VMC1/Automation%20and%20Integration%20Guide.pdf) (DataLink, HTTP commands, password protection), [Live Link](https://downloads.newtek.com/LiveProductionSystems/TCMiniGo/VizTCMini.pdf).

## Epiphan Pearl

**Works, untested.** Pearl's custom system variables show live values in a layout's text: ScoreSight sets them over Pearl's HTTP API.

1. In ScoreSight, select **HTTP API** in the Outputs list and pick **Epiphan Pearl** in **Preset**. The URL becomes:

   ```
   http://admin:PASSWORD@PEARL-IP/admin/set_variables.cgi
   ```

2. Replace `PEARL-IP` with the Pearl's IP address and `PASSWORD` with its admin password. Use `http://` (Pearl doesn't accept https for these commands).
3. Tick **Send out API requests to external services.** ScoreSight sends `GET /admin/set_variables.cgi?home_score=21&away_score=14&...`: only the changed fields, up to 6 per request and at most 5 requests per second (Pearl's documented limits), and every value again every 10 seconds, because Pearl forgets its variables when it restarts.
4. **The variable names**: Pearl allows only letters, digits and `_`, so each field is sent with a safe name: *Home Score* becomes `home_score`, *Away Score* `away_score`, *Time* `time`. The HTTP API page lists them (*Pearl variables: %(home_score), %(away_score)...*).
5. In Pearl's Admin panel, open the channel's **Layouts**, add a **Text** item and type for example `%(home_score)` (or `%(home_score) - %(away_score)`). A monospace font keeps the digits from jumping. Save: the text updates on every channel that uses the variable.

To check: open `http://PEARL-IP/admin/get_variables.cgi` in a browser; it lists the variables.

Unverified: whether Pearl wants Basic or Digest authentication for these commands (ScoreSight uses Digest if Pearl asks for it), and what Pearl does above its limits.

Vendor docs: [Controlling Pearl with HTTP commands](https://www.epiphan.com/userguides/pearl-api/Content/integrate/thirdPartyConfig/man_br_3rdParty_controlling_with_http.htm), [Custom system variables in text overlays](https://www.epiphan.com/userguides/pearl-2/Content/capture/customSystemVarsTxtOverlay.htm).

## Magewell Director

**Partly, untested.** Director's **Webpage GFX** shows a web page over the video, with a transparent background.

1. Put the Director and the ScoreSight computer on the same network, and allow TCP port 18099 on the ScoreSight computer.
2. On the Director, tap **GFX** > **Create New** > **Webpage**, enter `http://<scoresight-ip>:18099/scoresight` (the demo page) or the address of your own overlay page that polls `http://<scoresight-ip>:18099/json?pivot&all`, and tap **Go**.
3. In the GFX editor, set **CSS** to **Transparent CSS**, size and position it, save, and apply it in the show.

The Director's built-in scoreboards have an HTTP API with one call per field. With a URL with `{field}` and `{value}`, the outbound API can drive the **scores** (untested): name two custom boxes `setScoreOfHome` and `setScoreOfGuest`, and set the URL to `http://<director-ip>:8080/V1.0/gfx/scoreboard/{field}?score={value}` with **Only changes** ticked. Every other field is sent the same way too (and fails), so this suits a setup with just the two scores. The clock and the period take other parameters, which this doesn't cover.

Notes: ScoreSight doesn't serve custom pages, so your own overlay page has to be hosted elsewhere, over `http://` (an `https://` page can't read `http://` data). Vendor docs: [Director API](https://www.magewell.com/api-docs/director-api), [Director user manual](https://www.magewell.com/files/documents/User_Manual/User_Manual_for_Director_en_US.pdf).

## CasparCG

**Partly, untested.** CasparCG has no file or HTTP data source, but its HTML templates can fetch the values from ScoreSight.

Quick test: from the CasparCG client (or a telnet session to port 5250), send `PLAY 1-20 [HTML] "http://<scoresight-ip>:18099/scoresight"` to show the demo page; `CLEAR 1-20` removes it.

For a real scorebug, save a template like this as `scoresight.html` in CasparCG's templates folder, and adjust the address and the field names:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  html, body { margin: 0; background: transparent; overflow: hidden; }
  .bug { position: absolute; left: 80px; top: 60px; display: flex; gap: 20px;
         font: bold 48px Arial, sans-serif; color: white; opacity: 0; transition: opacity .3s; }
  .bug.on { opacity: 1; }
</style>
</head>
<body>
<div class="bug" id="bug">
  <span data-field="Home Score">0</span>
  <span data-field="Time">00:00</span>
  <span data-field="Away Score">0</span>
</div>
<script>
  const SCORESIGHT = "http://192.168.1.20:18099";  // the ScoreSight computer
  async function poll() {
    try {
      const data = await (await fetch(SCORESIGHT + "/json?pivot&all")).json();
      document.querySelectorAll("[data-field]").forEach(el => {
        const value = data[el.dataset.field];
        if (value) el.textContent = value;  // keep the last value until there is one
      });
    } catch (e) { /* ScoreSight not reachable: try again */ }
  }
  setInterval(poll, 200);
  // CasparCG calls these
  function play() { document.getElementById("bug").classList.add("on"); }
  function stop() { document.getElementById("bug").classList.remove("on"); }
  function update(data) {}
</script>
</body>
</html>
```

Play it with `CG 1-20 ADD 1 "scoresight" 1` (or a Template item in the CasparCG client), and take it off with `CG 1-20 STOP 1`.

Notes: the template polls, so a value shows up to 200 ms after ScoreSight reads it. Whether a template loaded from CasparCG's templates folder may fetch from another computer depends on CasparCG's browser settings and hasn't been tested; if it can't, host the page on a web server and play it with `PLAY 1-20 [HTML] "http://..."`. Vendor docs: [HTML templates](https://casparcg.com/docs/wiki/media/html-templates), [AMCP protocol](https://casparcg.com/docs/wiki/protocols/amcp-protocol).

## Singular.live

**Partly, untested.** Singular **Data Streams** take any JSON over HTTP, without call limits, and a composition script puts the values into the graphic. (For overlays.uno, which runs on Singular, use the built-in [UNO output](uno.md).)

1. In the Singular Dashboard, open **Data Stream Manager** > **New** and copy the private and public tokens. (Data Streams need a Pro plan or the free trial.)
2. In ScoreSight, select **HTTP API** and set **URL** `https://datastream.singular.live/datastreams/<PRIVATE TOKEN>`, method **PUT**, **Encode** *JSON (Simple key-value)*, and tick **Only changes**. Tick **Send out API requests to external services.**
3. In Composer, give each value a text control node, and add a composition script along these lines:

   ```js
   // init
   const sc = comp.find("<Sub-composition name>")[0];
   ds = context.utils.createDataStream("<PUBLIC TOKEN>", (status, msg) => {
     if (status !== "message") return;
     console.log(msg);  // check the shape first
     const data = (msg && msg.payload) || msg;  // the values, wrapped or not
     const update = {};
     if (data["Home Score"] !== undefined) update["HomeScore"] = data["Home Score"];
     if (data["Time"] !== undefined) update["Clock"] = data["Time"];
     sc.updateContent(update);  // control node IDs on the left
   });
   // close
   ds.close();
   ```

4. Check the stream's status in the Data Stream Manager, and watch the Composer preview.

Notes: the requests carry only fields with a good reading, so update only the keys that are present. Vendor docs: [Data Stream API](https://developer.singular.live/data-stream-api/introduction.md).

## Viz Flowics

**Partly, untested.** A Flowics **JSON HTTP Push** data input takes JSON over HTTP.

1. In Flowics, **Settings** > **Data Connectors - Inputs** > **Add** > **JSON HTTP Push - Content**. Paste a sample with your exact field names, for example `{"Home Score":"0","Away Score":"0","Time":"00:00","Period":"1"}`, generate the schema (keep every type *String*) and copy the push URL.
2. In the Graphics Editor, add a Data Connector for that input and bind text elements to its fields. Publish.
3. In ScoreSight, select **HTTP API** and set **URL** to the push URL, method **POST**, **Encode** *JSON (Simple key-value)*, and tick **Only changes** (keep **Fields** on *All in one request*). Tick **Send out API requests to external services.**

Alternative (Basic plan or higher, Windows): Flowics **Data Bridge** on the ScoreSight computer polling `http://127.0.0.1:18099/json?pivot&all` every second.

Notes: Flowics doesn't document push rate limits, or whether a payload replaces or merges with the previous one; renaming a field breaks the binding. Vendor docs: [JSON HTTP Push](https://support.flowics.com/en/articles/8873416-working-with-data-connectors-json-http-push), [Data Bridge](https://support.flowics.com/data-bridge/working-with-data-bridge).

## Chyron PRIME

**Partly, untested.** A PRIME scene's **Data** object reads JSON, XML or CSV, and pushes it to its bindings on an **Update** command.

1. In the PRIME scene, add a **Data** object (scene toolbox, Resources).
2. Set **Source** to *JSON* with the URL `http://<scoresight-ip>:18099/json?pivot&all` and a short download interval. (Or **Source** *Web* with `/xml?pivot&all`.)
3. In the binding section, drag each text object's **Text** property onto its field (*Home Score* and so on).
4. The Data object updates its bindings only on an Update command: set its **Timer Interval** (for example 0.5 s) with **Timer Elapsed** = *Update*, and start the timer in the scene's in-animation (keyframe **Command** = *Start Timer*). Or wire the **Data Changed** event to an Update.

Notes: the scene designer has to set up the timer; the shortest download interval isn't documented. Vendor docs: [PRIME Data object](https://help.chyron.com/hc/en-us/article_attachments/28076292820244).

## Products ScoreSight can't reach yet

- **Live Score** (live-score-app.com) and **MagicSoft CG** accept values over a TCP socket, which ScoreSight can't send yet. A generic TCP output is being considered.
- **Grafster**: its data feed protocol isn't published.
- **RT Software Swift**: its control API runs over a WebSocket; ScoreSight would need a dedicated output.
- **Vizrt** engines, **ClassX LiveBoard** and **wTVision** systems can be set up to poll ScoreSight's HTTP server or read its files (see the table above), but this depends on their licences and set-up, and hasn't been tried.

Want one of these, or another product? Open a [GitHub issue](https://github.com/royshil/scoresight/issues/new/choose) with what the product can receive.
