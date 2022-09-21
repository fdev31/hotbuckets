# Intro

Tired of dealing with major & minor numbers? You like the TOML format (kind of "ini" on steroids)?
Always wanted to play with traffic shaping on linux but it turned too complex or confusing?
This alpha tool aims at simplifying the learning curve for traffic control on ip route 2.

The format started quite close to the original command-line and progressively adds more support and shorter or easier notations.

Forget about `classid`, `flowid`.
Consider `parent` sometimes handle for `complex` scenarios only!

Check the *examples* folder to dive into the syntax.

# Supported features

- hosts aliases
- network interfaces aliases
- speeds aliases
- automatic generation of major & minor mumbers (all of them!) when possible
- visual representation of the setup

## Trafic control coverage

- sfq : makes a more fair traffic
- netem : simulate network problems
- htb : control traffic rate using categories
- tbf : very basic shaping

## QDiscs

- sfq
- netem
- htb
- tbf

## Classes

- htb

## Filters (assign traffic)

- fw
- u32
  - ip (src, dst, sport, dport)
- action

# Installation

    pip install hotbuckets

You can also directly download [the file](https://github.com/fdev31/hotbuckets/raw/main/hotbuckets.py), mark it executable adn run it.

You can optionally install `graphviz` to enable the `--show` action.

# Usage

Check the [examples](https://github.com/fdev31/hotbuckets/tree/main/examples) for more usages.

It uses a TOML formated file with a list of main sections:
- speeds: aliases for network speeds to avoid repeating values
- interfaces: aliases for network interfaces if you need symbolic names
- shaper: describes tc's qdiscs
- class: describes tc's classes (only htb for now)
- match: describes tc's filter, used to send traffic to a specific class or shaper

The sub section name is used as a unique identified, eg:

    [shaper.slowtraffic]

The items "shaper" "class" and "match" must have a parent, if not, it defaults to "root".
The "dev" (network interface) attribute is inherited from the parents if not set.

Given the file:

```ini
[speeds]
full = "32mbit"
half = "15mbit"

[interfaces.nic]
dev = "wlo1"

[shaper.base]
dev = "nic"
default = "baseline"
ceil = "full"

[class.unlimited]
parent = "base"
rate = "full"

[class."baseline"]
parent = "unlimited"
rate = "half"
ceil = "full"

[shaper.fairness]
parent = "baseline"
type = "sfq"
perturb = 10

[class."web"]
parent = "unlimited"
rate = "half"
ceil = "full"

[shaper.fairness-web]
parent = "web"
type = "sfq"
perturb = 10

[match.filtHttp]
protocol = "ip"
parent = "base"
sendTo = "web"
ip = {dport="80"}

[match.filtHttps]
protocol = "ip"
parent = "base"
sendTo = "web"
ip = {dport="443"}
```

You can use the command `htb configuration.toml` to get the following output:

    #!/bin/bash
    # Cleanup:
    tc qdisc del dev wlo1 root
    set -ex
    # Rules:
    tc qdisc add dev wlo1 root handle 1: htb default 2 # base
    tc class add dev wlo1 parent 1: classid 1:1 htb rate 32mbit # unlimited
    tc class add dev wlo1 parent 1:1 classid 1:2 htb rate 15mbit ceil 32mbit # baseline
    tc class add dev wlo1 parent 1:1 classid 1:3 htb rate 15mbit ceil 32mbit # web
    tc qdisc add dev wlo1 parent 1:2 handle 2: sfq perturb 10 # fairness
    tc qdisc add dev wlo1 parent 1:3 handle 3: sfq perturb 10 # fairness-web
    tc filter add dev wlo1 protocol ip parent 1: u32 match ip dport 80 0xffff flowid 1:3 # filtHttp
    tc filter add dev wlo1 protocol ip parent 1: u32 match ip dport 443 0xffff flowid 1:3 # filtHttps


You can also use the `--show` parameter to get a representation like this:

![graph](https://github.com/fdev31/hotbuckets/raw/main/examples/graph.png)

## Misc notes

- shapers are qdiscs, the "main" type of traffic control object, some can use classes
- classes are used by some shapers to divide the traffic
- match allows sending network traffic to a specific class or shaper (qdisc)
- try to avoid using the same names in match and class, some cases are ambiguous

# TODO

- relative speeds (percents)
- templates (for repeated attributes)

