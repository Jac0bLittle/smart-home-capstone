#!/usr/bin/env python3
"""Generates the minimal Node-RED flow (flows_minimal.json) for the dashboard.

The Node-RED editor fills in every widget default when this file is imported,
so the shipped flows.json is this file after one import + export.
Edit the layout here, rerun, and re-import.
"""
import json
import re
import itertools

_ids = itertools.count(1)
nodes = []


def nid():
    return f"sh{next(_ids):04d}"


def add(**n):
    n.setdefault("id", nid())
    nodes.append(n)
    return n["id"]


BROKER = add(type="mqtt-broker", name="jarvis broker", broker="localhost", port="1883",
             clientid="", autoConnect=True, usetls=False, protocolVersion="4", keepalive="30",
             cleansession=True, autoUnsubscribe=True,
             birthTopic="", closeTopic="", willTopic="")
UI = add(type="ui-base", name="Smart Home", path="/dashboard", includeClientData=True,
         acceptsClientConfig=["ui-notification", "ui-control"], showPathInSidebar=False,
         navigationStyle="default", titleBarStyle="default")
THEME = add(type="ui-theme", name="Smart Home Theme",
            colors={"surface": "#1f3b57", "primary": "#2b6cb0", "bgPage": "#f4f6f8",
                    "groupBg": "#ffffff", "groupOutline": "#d9d9e0"},
            sizes={"density": "default", "pagePadding": "12px", "groupGap": "12px",
                   "groupBorderRadius": "6px", "widgetGap": "12px"})

pages = {}
for i, (name, icon) in enumerate([("Overview", "home"), ("Climate", "thermometer"),
                                  ("Alarm", "shield-home"), ("Lighting", "lightbulb"),
                                  ("Solar", "solar-panel"), ("System", "cog")]):
    pages[name] = add(type="ui-page", name=name, ui=UI, path="/" + name.lower(), icon=icon,
                      layout="grid", theme=THEME, order=i + 1, className="", visible="true",
                      disabled="false")

_gorder = itertools.count(1)


def group(page, name, width=6):
    return add(type="ui-group", name=name, page=pages[page], width=str(width), height="1",
               order=next(_gorder), showTitle=True, className="", visible="true", disabled="false")


tabs = {}
_pos = {}


def tab(name):
    tabs[name] = add(type="tab", label=name, disabled=False, info="")
    _pos[name] = [0]
    return tabs[name]


def place(tabname, col):
    """Lay nodes out in columns so the editor view is tidy."""
    _pos[tabname][0] += 1 if col == 0 else 0
    return 150 + col * 260, 40 + _pos[tabname][0] * 60


def mqtt_in(t, topic, wires, qos="1"):
    x, y = place(t, 0)
    return add(type="mqtt in", z=tabs[t], name="", topic=topic, qos=qos, datatype="auto-detect",
               broker=BROKER, nl=False, rap=True, rh=0, inputs=0, x=x, y=y, wires=[wires])


def mqtt_out(t, topic, retain="false"):
    x, y = place(t, 2)
    return add(type="mqtt out", z=tabs[t], name="", topic=topic, qos="1", retain=retain,
               respTopic="", contentType="", userProps="", correl="", expiry="",
               broker=BROKER, x=x, y=y, wires=[])


def func(t, name, code, wires, col=1):
    x, y = place(t, col)
    return add(type="function", z=tabs[t], name=name, func=code, outputs=1, timeout=0,
               noerr=0, initialize="", finalize="", libs=[], x=x, y=y, wires=[wires])


def widget(t, wtype, grp, wires=None, col=1, **kw):
    x, y = place(t, col)
    n = dict(type=wtype, z=tabs[t], group=grp, x=x, y=y, wires=[wires or []] if wtype not in ("ui-text", "ui-gauge") else [])
    if wtype in ("ui-text", "ui-gauge", "ui-chart", "ui-table") and wires is None:
        n["wires"] = [] if wtype in ("ui-text", "ui-gauge") else [[]]
    n.update(kw)
    return add(**n)


def text(t, grp, label, order, fmt="{{msg.payload}}", wires_from=None):
    return widget(t, "ui-text", grp, label=label, order=order, width="0", height="0",
                  format=fmt, layout="row-spread", style=False, font="", fontSize=16,
                  color="#717171", wrapText=False, className="", value="payload", valueType="msg")


def show(t, topic, grp, label, order, fmt="{{msg.payload}}"):
    """Text row fed by an MQTT topic. Dashboard 2.0 ui-text shows msg.payload as is,
    so a fmt like "{{msg.payload}} mW" becomes a small function node in front of it."""
    w = text(t, grp, label, order)
    m = re.match(r"^\{\{(.*?)\}\}(.*)$", fmt)
    if fmt == "{{msg.payload}}" or not m:
        mqtt_in(t, topic, [w])
    else:
        expr = m.group(1).replace("msg.payload", "p")
        f = func(t, f"format {label}", f"const p = msg.payload;\nmsg.payload = ({expr}) + {json.dumps(m.group(2))};\nreturn msg;", [w])
        mqtt_in(t, topic, [f])
    return w


def button(t, grp, label, order, payload, out_topic, ptype="str"):
    o = mqtt_out(t, out_topic)
    return widget(t, "ui-button", grp, [o], label=label, order=order, width="0", height="0",
                  payload=payload, payloadType=ptype, topic="topic", topicType="msg")


ON_OFF = "{{msg.payload == 1 ? 'ON' : 'OFF'}}"

# ---------------- Overview ----------------
tab("Overview")
g_nodes = group("Overview", "Node status", 4)
for i, sub in enumerate(["climate", "alarm", "lighting", "solar"]):
    show("Overview", f"home/{sub}/node1/status", g_nodes, sub.capitalize(), i + 1)
show("Overview", "home/hub/jarvis/status", g_nodes, "Hub services", 5)
g_quick = group("Overview", "At a glance", 4)
show("Overview", "home/alarm/node1/state/mode", g_quick, "Alarm", 1)
button("Overview", g_quick, "Arm", 2, "armed", "home/alarm/node1/cmd/mode")
button("Overview", g_quick, "Disarm", 3, "disarmed", "home/alarm/node1/cmd/mode")
show("Overview", "home/climate/node1/tele/temp_c", g_quick, "Temperature", 4, "{{msg.payload}} °C")
show("Overview", "home/lighting/node1/state/power", g_quick, "Exterior lights", 5, ON_OFF)
show("Overview", "home/solar/node1/tele/panel_mw", g_quick, "Solar power", 6, "{{msg.payload}} mW")
g_alerts = group("Overview", "Last 5 alerts", 4)
alert_tbl = widget("Overview", "ui-table", g_alerts, col=2, label="", order=1, width="0", height="0",
                   maxrows=5, passthru=False, autocols=True, showSearch=False, deselect=True,
                   selectionType="none", columns=[], mobileBreakpoint="sm",
                   mobileBreakpointType="defaults", action="replace", className="")
keep_alerts = func("Overview", "keep last 5", """
const list = context.get('alerts') || [];
const a = msg.payload;
list.unshift({time: new Date().toLocaleTimeString(), type: a.type, message: a.message,
              sent: (a.channels || []).join('+') || 'none'});
context.set('alerts', list.slice(0, 5));
msg.payload = list.slice(0, 5);
return msg;""", [alert_tbl])
mqtt_in("Overview", "home/hub/jarvis/event/alert", [keep_alerts])

# ---------------- Climate ----------------
tab("Climate")
g_now = group("Climate", "Now", 6)
for i, (topic, title, units, lo, hi) in enumerate([("temp_c", "Temperature", "°C", 10, 40),
                                                    ("humidity_pct", "Humidity", "%RH", 0, 100)]):
    gauge = widget("Climate", "ui-gauge", g_now, label="", order=i + 1, width="3", height="3",
                   gtype="gauge-half", gstyle="needle", title=title, alwaysShowTitle=False,
                   floatingTitlePosition="top-left", units=units, icon="", prefix="", suffix="",
                   segments=[{"from": str(lo), "color": "#5cd65c"}, {"from": str(hi - (hi - lo) // 5), "color": "#ea5353"}],
                   min=lo, max=hi, sizeThickness=16, sizeGap=4, sizeKeyThickness=8,
                   styleRounded=True, styleGlow=False, className="", value="payload", valueType="msg")
    mqtt_in("Climate", f"home/climate/node1/tele/{topic}", [gauge])
show("Climate", "home/climate/node1/state/heater", g_now, "Heater", 3, ON_OFF)
show("Climate", "home/climate/node1/state/fan", g_now, "Fan", 4, "{{msg.payload}} %")
g_ctl = group("Climate", "Control", 6)
sp_out = mqtt_out("Climate", "home/climate/node1/cmd/setpoint_c")
sp = widget("Climate", "ui-slider", g_ctl, [sp_out], label="Setpoint (°C)", tooltip="", order=1,
            width="0", height="0", passthru=False, outs="end", topic="topic", topicType="msg",
            thumbLabel=True, showTicks="always", min=18, max=30, step=0.5, className="",
            iconPrepend="", iconAppend="", color="", colorTrack="", colorThumb="", showTextField=True)
mqtt_in("Climate", "home/climate/node1/state/setpoint_c", [sp])
mode_out = mqtt_out("Climate", "home/climate/node1/cmd/mode")
mode = widget("Climate", "ui-dropdown", g_ctl, [mode_out], label="Mode", tooltip="", order=2,
              width="0", height="0", passthru=False, multiple=False, chips=False, clearable=False,
              options=[{"label": "Auto", "value": "auto", "type": "str"},
                       {"label": "Manual", "value": "manual", "type": "str"},
                       {"label": "Off", "value": "off", "type": "str"}],
              payload="", topic="topic", topicType="msg", className="", typeIsComboBox=True,
              msgTrigger="onChange")
mqtt_in("Climate", "home/climate/node1/state/mode", [mode])
heat_out = mqtt_out("Climate", "home/climate/node1/cmd/heater")
widget("Climate", "ui-switch", g_ctl, [heat_out], name="", label="Heater (manual mode)", order=3,
       width="0", height="0", passthru=False, decouple=True, topic="topic", topicType="msg",
       style="", className="", layout="row-spread", clickableArea="switch",
       onvalue="1", onvalueType="num", onicon="", oncolor="", offvalue="0", offvalueType="num",
       officon="", offcolor="")
g_hist = group("Climate", "Last 24 hours", 12)
chart = widget("Climate", "ui-chart", g_hist, col=2, label="Temperature and humidity", order=1,
               chartType="line", category="topic", categoryType="msg", xAxisLabel="",
               xAxisProperty="", xAxisPropertyType="timestamp", xAxisType="time", xAxisFormat="",
               xAxisFormatType="auto", xmin="", xmax="", yAxisLabel="", yAxisProperty="payload",
               yAxisPropertyType="msg", ymin="", ymax="", bins=10, action="append",
               stackSeries=False, pointShape="false", pointRadius=4, showLegend=True,
               removeOlder="24", removeOlderUnit="3600", removeOlderPoints="", width="12", height="6",
               className="", interpolation="linear")
label_series = func("Climate", "series name", """
if (msg.topic.endsWith('temp_c')) msg.topic = 'Temperature (°C)';
else if (msg.topic.endsWith('humidity_pct')) msg.topic = 'Humidity (%RH)';
else return null;   // pressure and gas are not on this chart
return msg;""", [chart])
mqtt_in("Climate", "home/climate/node1/tele/+", [label_series])

# ---------------- Alarm ----------------
tab("Alarm")
g_st = group("Alarm", "Status", 6)
show("Alarm", "home/alarm/node1/state/mode", g_st, "Mode", 1)
show("Alarm", "home/alarm/node1/state/door", g_st, "Door", 2, "{{msg.payload == 1 ? 'OPEN' : 'closed'}}")
show("Alarm", "home/alarm/node1/state/gas", g_st, "Gas", 3, "{{msg.payload == 1 ? 'DETECTED' : 'clear'}}")
show("Alarm", "home/alarm/node1/state/buzzer", g_st, "Buzzer", 4, ON_OFF)
g_act = group("Alarm", "Actions", 6)
button("Alarm", g_act, "Arm", 1, "armed", "home/alarm/node1/cmd/mode")
button("Alarm", g_act, "Disarm", 2, "disarmed", "home/alarm/node1/cmd/mode")
button("Alarm", g_act, "Silence buzzer", 3, "1", "home/alarm/node1/cmd/silence")
button("Alarm", g_act, "Send test alert", 4, "dashboard", "home/hub/jarvis/cmd/test_alert")
g_log = group("Alarm", "Event log", 12)
ev_tbl = widget("Alarm", "ui-table", g_log, col=2, label="", order=1, width="0", height="0",
                maxrows=10, passthru=False, autocols=True, showSearch=False, deselect=True,
                selectionType="none", columns=[], mobileBreakpoint="sm",
                mobileBreakpointType="defaults", action="replace", className="")
ev = func("Alarm", "event log", """
// Live changes only: skip retained replays and the duplicate copy the broker
// sends because state/# and event/# overlap other subscriptions on this connection.
if (msg.retain) return null;
const key = msg.topic + '=' + msg.payload, now = Date.now();
const last = context.get('last') || {};
if (last.key === key && now - last.t < 500) return null;
context.set('last', {key: key, t: now});
const list = context.get('ev') || [];
list.unshift({time: new Date().toLocaleTimeString(), topic: msg.topic.split('/').slice(3).join('/'),
              value: String(msg.payload)});
context.set('ev', list.slice(0, 50));
msg.payload = list.slice(0, 50);
return msg;""", [ev_tbl])
mqtt_in("Alarm", "home/alarm/node1/event/#", [ev])
mqtt_in("Alarm", "home/alarm/node1/state/#", [ev])

# ---------------- Lighting ----------------
tab("Lighting")
g_l = group("Lighting", "Exterior lights", 6)
pw_out = mqtt_out("Lighting", "home/lighting/node1/cmd/power")
pw = widget("Lighting", "ui-switch", g_l, [pw_out], name="", label="Lights", order=1, width="0",
            height="0", passthru=False, decouple=False, topic="topic", topicType="msg", style="",
            className="", layout="row-spread", clickableArea="switch", onvalue="1", onvalueType="num",
            onicon="", oncolor="", offvalue="0", offvalueType="num", officon="", offcolor="")
mqtt_in("Lighting", "home/lighting/node1/state/power", [pw])
am_out = mqtt_out("Lighting", "home/lighting/node1/cmd/mode")
am = widget("Lighting", "ui-switch", g_l, [am_out], name="", label="Automatic (motion + dusk)", order=2,
            width="0", height="0", passthru=False, decouple=False, topic="topic", topicType="msg",
            style="", className="", layout="row-spread", clickableArea="switch", onvalue="auto",
            onvalueType="str", onicon="", oncolor="", offvalue="manual", offvalueType="str",
            officon="", offcolor="")
mqtt_in("Lighting", "home/lighting/node1/state/mode", [am])
br_out = mqtt_out("Lighting", "home/lighting/node1/cmd/brightness")
br = widget("Lighting", "ui-slider", g_l, [br_out], label="Brightness (%)", tooltip="", order=3,
            width="0", height="0", passthru=False, outs="end", topic="topic", topicType="msg",
            thumbLabel=True, showTicks="always", min=0, max=100, step=5, className="",
            iconPrepend="", iconAppend="", color="", colorTrack="", colorThumb="", showTextField=False)
mqtt_in("Lighting", "home/lighting/node1/state/brightness", [br])
co_out = mqtt_out("Lighting", "home/lighting/node1/cmd/color")
co = widget("Lighting", "ui-dropdown", g_l, [co_out], label="Color", tooltip="", order=4, width="0",
            height="0", passthru=False, multiple=False, chips=False, clearable=False,
            options=[{"label": n, "value": v, "type": "str"} for n, v in
                     [("Warm white", "#FFB46B"), ("Cool white", "#FFFFFF"), ("Red", "#FF0000"),
                      ("Green", "#00FF00"), ("Blue", "#0000FF"), ("Amber", "#FFA000")]],
            payload="", topic="topic", topicType="msg", className="", typeIsComboBox=True,
            msgTrigger="onChange")
mqtt_in("Lighting", "home/lighting/node1/state/color", [co])
g_ls = group("Lighting", "Light sensor", 6)
show("Lighting", "home/lighting/node1/tele/lux", g_ls, "Outdoor light", 1, "{{msg.payload}} lux")
th_out = mqtt_out("Lighting", "home/lighting/node1/cmd/lux_threshold")
th = widget("Lighting", "ui-slider", g_ls, [th_out], label="Dusk threshold (lux)", tooltip="", order=2,
            width="0", height="0", passthru=False, outs="end", topic="topic", topicType="msg",
            thumbLabel=True, showTicks="always", min=0, max=500, step=10, className="",
            iconPrepend="", iconAppend="", color="", colorTrack="", colorThumb="", showTextField=True)
mqtt_in("Lighting", "home/lighting/node1/state/lux_threshold", [th])

# ---------------- Solar ----------------
tab("Solar")
g_s = group("Solar", "Tracker", 6)
show("Solar", "home/solar/node1/state/mode", g_s, "Mode", 1)
show("Solar", "home/solar/node1/state/pan_deg", g_s, "Pan", 2, "{{msg.payload}}°")
show("Solar", "home/solar/node1/state/tilt_deg", g_s, "Tilt", 3, "{{msg.payload}}°")
sm_out = mqtt_out("Solar", "home/solar/node1/cmd/mode")
widget("Solar", "ui-dropdown", g_s, [sm_out], label="Set mode", tooltip="", order=4, width="0",
       height="0", passthru=False, multiple=False, chips=False, clearable=False,
       options=[{"label": "Track", "value": "track", "type": "str"},
                {"label": "Park", "value": "park", "type": "str"},
                {"label": "Manual", "value": "manual", "type": "str"}],
       payload="", topic="topic", topicType="msg", className="", typeIsComboBox=True,
       msgTrigger="onChange")
for i, axis in enumerate(["pan", "tilt"]):
    o = mqtt_out("Solar", f"home/solar/node1/cmd/{axis}_deg")
    widget("Solar", "ui-slider", g_s, [o], label=f"Manual {axis} (°)", tooltip="", order=5 + i,
           width="0", height="0", passthru=False, outs="end", topic="topic", topicType="msg",
           thumbLabel=True, showTicks="always", min=0, max=180, step=5, className="",
           iconPrepend="", iconAppend="", color="", colorTrack="", colorThumb="", showTextField=False)
g_sp = group("Solar", "Tracked vs fixed panel", 12)
schart = widget("Solar", "ui-chart", g_sp, col=2, label="Panel power (mW)", order=1, chartType="line",
                category="topic", categoryType="msg", xAxisLabel="", xAxisProperty="",
                xAxisPropertyType="timestamp", xAxisType="time", xAxisFormat="", xAxisFormatType="auto",
                xmin="", xmax="", yAxisLabel="mW", yAxisProperty="payload", yAxisPropertyType="msg",
                ymin="", ymax="", bins=10, action="append", stackSeries=False, pointShape="false",
                pointRadius=4, showLegend=True, removeOlder="12", removeOlderUnit="3600",
                removeOlderPoints="", width="12", height="6", className="", interpolation="linear")
ss = func("Solar", "series name", """
msg.topic = msg.topic.endsWith('ref_mw') ? 'Fixed panel' : 'Tracking panel';
return msg;""", [schart])
mqtt_in("Solar", "home/solar/node1/tele/panel_mw", [ss])
mqtt_in("Solar", "home/solar/node1/tele/ref_mw", [ss])

# ---------------- System ----------------
tab("System")
g_sys = group("System", "Nodes", 12)
sys_tbl = widget("System", "ui-table", g_sys, col=2, label="", order=1, width="0", height="0",
                 maxrows=0, passthru=False, autocols=True, showSearch=False, deselect=True,
                 selectionType="none", columns=[], mobileBreakpoint="sm",
                 mobileBreakpointType="defaults", action="replace", className="")
agg = func("System", "node table", """
const t = context.get('t') || {};
const [, sub, nodeId, , name] = msg.topic.split('/');
const key = sub + '/' + nodeId;
t[key] = t[key] || {node: key, status: '?', uptime_s: '', rssi_dbm: '', free_heap: ''};
if (msg.topic.endsWith('/status')) t[key].status = msg.payload;
else t[key][name] = msg.payload;
t[key].updated = new Date().toLocaleTimeString();
context.set('t', t);
msg.payload = Object.values(t);
return msg;""", [sys_tbl])
mqtt_in("System", "home/+/+/status", [agg])
mqtt_in("System", "home/+/+/tele/uptime_s", [agg])
mqtt_in("System", "home/+/+/tele/rssi_dbm", [agg])
mqtt_in("System", "home/+/+/tele/free_heap", [agg])

json.dump(nodes, open("flows_minimal.json", "w"), indent=1)
print(f"{len(nodes)} nodes written to flows_minimal.json")
