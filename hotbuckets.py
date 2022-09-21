#!/bin/env python
import argparse
from collections import defaultdict

import tomli


# utils
def findIt(func, it):
    return next(filter(lambda x: x, map(func, it)))


def fixHandles(txt):
    if callable(txt):
        txt = txt()
    return "h" + txt.replace(":", "_")


def commentify(txt):
    ret = []
    for i, line in enumerate(txt.split("\n")):
        if i == 0:
            ret.append(line)
        else:
            ret.append("#   %s" % line)
    return "\n".join(ret)


# worker code
class D:
    "Main storage for rules & classes"

    def __init__(self):
        self.nodes = {}
        self.nodeOpts = {}
        self.linkOpts = {}
        self.links = defaultdict(lambda: [])

    def view(self):
        # Text output
        for node, v in self.nodes.items():
            gr and gr.node(fixHandles(node), label=v if v else node, **self.nodeOpts[node])
        for node, v in self.links.items():
            for c in v:
                gr and gr.edge(fixHandles(c), fixHandles(node), **self.linkOpts[(node, c)])
        # Graphical output + dump the graphviz.file
        gr and gr.render()
        gr and gr.view()

    def node(self, name, label="", **opts):
        self.nodes[name] = label
        self.nodeOpts[name] = opts

    def edge(self, name, name2, **opts):
        self.linkOpts[(name, name2)] = opts
        self.links[name].append(name2)


def TcClassRule(name, data):
    ret = [TC, "class", "add"]
    handleDev(ret, data, validParents["class"])
    dad = data.get("parent", "root")
    p = findIt(lambda x: flows[x].get(dad), flows.keys())
    ret.extend(["parent", p])
    thisId = len(flows["classes"]) + 1
    flows["classes"][name] = "%s:%s" % (p.split(":")[0], thisId)
    g.edge(flows["classes"][name], p)
    ret.extend(["classid", flows["classes"][name]])
    t = data.get("type", "htb")
    ret.append(t)
    if t == "htb":
        handleCommonTypes(ret, data, "burst")
        rate = handleCommonTypes(ret, data, "rate", isSpeed=True, mandatory=True)
        ceil = handleCommonTypes(ret, data, "ceil", isSpeed=True)
        args = args = {"color": "orange"} if name in defaults else {}
        g.node(
            flows["classes"][name],
            label=f"{t} class {name} ({flows['classes'][name]})\nrate={rate}/{ceil}",
            **args,
        )
    loglines.append(ret + ["# " + name])


def TcFilterRule(name, data):
    ret = [TC, "filter", "add"]
    handleDev(ret, data, validParents["class"])
    handleCommonTypes(ret, data, "protocol")

    pname = data.get("parent")
    if pname:
        ret.extend(["parent", lambda: flows["shapers"][pname]])

    handleCommonTypes(ret, data, "prio")

    ret.append(data.get("type", "u32"))

    extra = ""
    if handleCommonTypes(ret, data, "handle"):
        extra += " (%s)" % data["handle"]

    if "ip" in data:
        for k, v in data["ip"].items():
            ret.extend(["match", "ip"])

            if "hosts" in doc and v in doc["hosts"]:
                v = doc["hosts"][v]["ip"]
            if k in ("src", "dst", "sport", "dport"):
                extra += "\n%s=%s" % (k, v)
            ret.extend([k, str(v)])
            if k.endswith("port"):
                ret.append("0xffff")
    filters = data["sendTo"]
    for flowType in ("classes", "shapers"):
        if filters in flows[flowType]:
            flowid = flows[flowType][filters]
            break

    g.node(name, label="%s%s" % (name, extra), shape="plain", fontsize="8")
    g.edge(flowid, name, arrowhead="dot")
    ret.extend(["flowid", flowid])
    handleCommonTypes(ret, data, "action")
    loglines.append(ret + ["# " + name])


def TcShapeRule(name, data):
    ret = [TC, "qdisc", "add"]
    handleDev(ret, data, validParents["shaper"])

    dad = data.get("parent", "root")
    if dad == "root":
        ret.append("root")
    else:
        p = findIt(lambda x: flows[x].get(dad), flows.keys())
        ret.extend(["parent", p])

    t = data.get("type", "htb")
    thisId = len(flows["shapers"]) + 1
    flows["shapers"][name] = "%d:" % (thisId)
    ret.extend(["handle", flows["shapers"][name]])
    if dad != "root":
        g.edge(flows["shapers"][name], p)

    ret.append(t)
    extra = []
    if t == "sfq":
        if "perturb" not in data:
            data["perturb"] = "10"
        _quantum = handleCommonTypes(ret, data, "quantum")
        perturb = handleCommonTypes(ret, data, "perturb")
        extra.append("perturb: %s" % perturb)
    elif t == "netem":
        delay = handleCommonTypes(ret, data, "delay")
        loss = handleCommonTypes(ret, data, "loss")
        dup = handleCommonTypes(ret, data, "duplicate")
        corrupt = handleCommonTypes(ret, data, "corrupt")
        handleCommonTypes(ret, data, "reorder")
        if delay:
            extra.append("delay: %s" % delay)
        if loss:
            extra.append("loss: %s" % loss)
        if dup:
            extra.append("dups: %s" % dup)
        if corrupt:
            extra.append("corrupt: %s" % corrupt)
    elif t in ("htb", "tbf"):
        lat = handleCommonTypes(ret, data, "latency")
        bur = handleCommonTypes(ret, data, "burst")
        rat = handleCommonTypes(ret, data, "rate", isSpeed=True)
        if lat:
            extra.append("latency: %s" % lat)
        if bur:
            extra.append("burst: %s" % bur)
        if rat:
            extra.append("rate : %s" % rat)

    extra = "\n".join(extra)
    g.node(
        flows["shapers"][name],
        label=f"Queue[{t}] {name} ({flows['shapers'][name]})\n{extra}",
    )

    if "default" in data:
        defaults.add(data["default"])
        ret.extend(["default", lambda: flows["classes"][data["default"]].split(":")[1]])
    loglines.append(ret + ["# " + name])


def parseSection(section, handler):
    error = False
    if section not in doc:
        return
    for name, data in doc[section].items():
        if name in _parsed[section]:
            continue
        try:
            handler(name, data)
            _parsed[section].add(name)
        except Exception as e:
            if not error:
                t = type(e).__name__
                if t == "KeyError":
                    error = f'Error in {section}.{name}, couldn\'t find "{e.args[0]}"'
                else:
                    error = "%s : %s" % (t, ", ".join(e.args))
    return error


def main():
    def handleOrClassId(txt):
        try:
            i = txt.index("handle")
        except ValueError:
            try:
                i = txt.index("classid")
            except ValueError:
                return (999, 999)

        try:
            ma, mi = txt[i + 1].split(":")
        except ValueError:  # Expecting just a major number: eg fw filter
            ma = txt[i + 1]
            mi = 0

        return int(ma or 0), int(mi or 0)

    for n in range(10):
        s = parseSection("shaper", TcShapeRule)
        c = parseSection("class", TcClassRule)
        m = parseSection("match", TcFilterRule)
        if not any([s, c, m]):
            break

    if any([s, c, m]):
        print("Couldn't fully parse the file :(")
        print(s or c or m)
        raise SystemExit(1)
    print("#!/bin/bash")
    print("# Cleanup:")
    for nic in allNICS:
        print("%s qdisc del dev %s root" % (TC, nic))
    print("set -ex")
    print("# Rules:")

    for line in sorted(loglines, key=handleOrClassId):
        print(" ".join(x() if callable(x) else x for x in line))
    g.view()


# args
parser = argparse.ArgumentParser(description="Generate TC rules from a TOML description")
parser.add_argument(
    "--show",
    default=False,
    help="display a graphical representation using graphviz",
    action="store_true",
)
parser.add_argument(
    "config",
    help="TOML file containing all the rules",
    type=argparse.FileType("rb"),
    metavar="TOML FILE",
)
args = parser.parse_args()

# init digraph
try:
    if not args.show:
        raise ImportError()
    from graphviz import Digraph

    gr = Digraph("TC")
except ImportError as e:
    gr = None

g = D()
doc = tomli.load(args.config)

validParents = {  # registers valid parent types for each type
    "shaper": ("class", "class"),
    "class": ("class", "shaper"),
    "filter": ("shaper",),
}

TC = doc.get("tc", "tc")

flows = {  # flows as found in the config
    "shapers": {},
    "classes": {},
}

allNICS = set()  # list of NICs found in the config
defaults = set()  # set of default entries
loglines = []  # list of log lines (final output)
_parsed = {"shaper": set(), "class": set(), "match": set()}


def getNIC(uid):
    r = _getNIC(uid)
    allNICS.add(r)
    return r


def _getNIC(uid):
    try:
        return doc["interfaces"][uid]["dev"]
    except KeyError:
        return uid


def _findDev(r, d, curType):
    if "dev" in d:
        return getNIC(d["dev"])
    else:
        parentTypes = validParents[curType]
        for ptype in parentTypes:
            p = d.get("parent")
            if p and doc[ptype].get(p):
                v = _findDev(r, doc[ptype].get(p), ptype)
                if v:
                    return v


def handleDev(r, d, parentTypes=("class",)):
    if "dev" in d:
        r.extend(["dev", getNIC(d["dev"])])
    else:
        if len(parentTypes) == 1:
            r.extend(["dev", lambda: _findDev(r, d, parentTypes[0])])
        else:
            r.extend(["dev", lambda: findIt(lambda x: _findDev(r, d, x), parentTypes)])


def handleCommonTypes(r, d, k, isSpeed=False, mandatory=False):
    if k in d:
        v = str(d[k])
        if isSpeed:
            if isinstance(d[k], int):
                v = "%s%s" % (d[k], doc["unit"])
            elif "speeds" in doc:
                if d[k] in doc["speeds"]:
                    v = doc["speeds"][d[k]]
        r.extend([k, v])
        return v
    if mandatory:
        raise ValueError(f"No {k} given for {r}")


if __name__ == "__main__":
    main()
