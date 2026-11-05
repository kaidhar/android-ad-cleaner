#!/usr/bin/env python3
"""Turn off promotional notifications and keep the useful ones. For Android phones with English menus.

  python tool/promo.py scan                     read only: lists promotional channels and saves a list file
  python tool/promo.py off LIST                 preview: shows what would change, changes nothing
  python tool/promo.py off LIST --yes           turns those channels off
  python tool/promo.py off LIST --only photos --yes     just the ones matching a word, to try it out
  python tool/promo.py undo LIST --yes          turns them back on
  python tool/promo.py phone                    preview: shows this phone's own ad switches, if it has a script
  python tool/promo.py phone --yes              turns those off
  python tool/promo.py cleanup                  removes the small helper this leaves on the phone. Run it when you're done

Add -s SERIAL before the command if more than one phone is connected.
The list is a plain text file. Lines starting with # are skipped: delete the # to include one, add a # to spare one.
"""
import os, re, subprocess, sys, tempfile, time

for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adb_link
from chan_fast import FG_SERVICE_MARKS, ShellPhone, load, parse, truncated
from channel_policy import protected_channel
import promo_policy as policy

ROOT = os.path.dirname(HERE)

# chan_fast does the careful part: it opens each channel's page, finds the one right switch, reads the state back and
# undoes anything it didn't mean to change. It talks in Chinese, so its lines are put into English here.
SAYS = [
    (r"^拨了 (\d+) 个，(\d+) 秒$", r"Changed \1 in \2 seconds."),
    (r"^营销渠道仍开着: (\d+) 个$", r"Still on: \1"),
    (r"^未恢复的渠道: (\d+) 个$", r"Not restored: \1"),
    (r"^正在连接手机读屏服务……$", "Connecting to the phone..."),
    (r"^要处理 (\d+) 个渠道，.*$", r"\1 to change. Each takes a few seconds."),
    (r"^再试一次刚才没确认的 (\d+) 个渠道$", r"Trying the \1 I couldn't confirm once more."),
    (r"^  关  (.*)$", r"  off   \1"),
    (r"^  关 (.*)$", r"  off   \1"),
    (r"^  · (.*)：核对 (\d+) 项，调整 (\d+) 项$", r"  \1: checked \2, changed \3"),
    (r"^  · 弹窗点了「(.*)」$", r"  closed a pop-up (\1)"),
    (r"^  ✗ 底部没有「(.*)」标签$", r"  ✗ no \1 tab at the bottom"),
    (r"^机型脚本跑完：关了 (\d+) 个，(\d+) 秒$", r"Finished: turned off \1 in \2 seconds."),
    (r"^  开  (.*)$", r"  on    \1"),
    (r"^  仍开着：(.*)$", r"  still on: \1"),
    (r"^  · 未操作 (.*?)（.*$", r"  skipped: \1 (the channel is gone, or the whole app is already off)"),
    (r"^  · 系统锁定.*?  (.*)$", r"  skipped: \1 (the system locks this one)"),
    (r"^  · 应用通知已整体关闭.*?  (.*)$", r"  skipped: \1 (the whole app is already off)"),
    (r"^  · 受保护，未改动 (.*?)（.*$", r"  left alone: \1 (protected)"),
    (r"^  ✗ 手机一直锁屏.*$", "  Stopped: the phone stayed locked. Unlock it and run this again."),
    (r"^  ✗ 手机锁屏了，停在「(.*?)」，剩下 (\d+) 项.*$", r"  Stopped at \1: the phone locked, \2 left. Unlock it and run this again."),
    (r"^  ! 插电常亮没有设上.*$", "  Couldn't keep the screen on. Turn on Stay awake in Developer options."),
    (r"^  ✗ (.*?)  (\S.*)$", r"  couldn't change: \2 (\1)"),
]


def english(line):
    for pat, rep in SAYS:
        if re.match(pat, line):
            return re.sub(pat, rep, line)
    return line


def pick_serial(given):
    """The one connected phone, or the one named with -s."""
    if given:
        return given
    adb = adb_link.adb_path()
    if not adb:
        sys.exit("Can't find adb. Install Android platform-tools. See README.md.")
    out = adb_link.invoke(adb, "devices")
    phones, waiting = [], []
    for line in out.splitlines()[1:]:
        bits = line.split()
        if len(bits) >= 2:
            (phones if bits[1] == "device" else waiting).append(bits[0])
    if waiting and not phones:
        sys.exit("The phone is connected but hasn't allowed this computer. Unlock it and tap Allow on the USB debugging prompt.")
    if not phones:
        sys.exit("No phone found. Connect it with a data cable and turn on USB debugging. See README.md.")
    if len(phones) > 1:
        sys.exit("More than one device connected. Pick one: python tool/promo.py -s SERIAL scan\n  " + "\n  ".join(phones))
    return phones[0]


def phone_line(reader):
    def prop(k):
        try:
            return reader.shell(f"getprop {k}").output.strip()
        except RuntimeError:
            return ""
    os_name = prop("ro.vivo.os.build.display.id") or prop("ro.build.version.incremental")
    return " ".join(x for x in (prop("ro.product.brand"), prop("ro.product.model"), "·", os_name, "· Android", prop("ro.build.version.release")) if x)


def scan(serial):
    reader = ShellPhone(serial)
    locked, foreground = set(), set()
    channels, app_off = parse(reader, locked, foreground)
    live = {k: v for k, v in channels.items() if v[1] != 0 and not v[2] and not app_off.get(k[0])}
    groups = {policy.OFF: [], policy.ASK: []}
    for (pk, cid), (name, _, _) in sorted(live.items()):
        if (pk, cid) in locked or (pk, cid) in foreground or truncated(cid) or protected_channel(name, cid):
            continue
        verdict = policy.classify(name, cid, pk)
        if verdict != policy.KEEP:
            groups[verdict].append((pk, cid, f"{policy.app_name(pk)}: {name}"))
    backups = os.path.join(ROOT, "backups")
    os.makedirs(backups, exist_ok=True)
    path = os.path.join(backups, time.strftime("promo-list-%Y%m%d-%H%M%S.tsv"))
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Lines starting with # are skipped. Delete the # to include a channel, add one to spare it.\n")
        f.write("# Everything below was on when this list was made, so undo turns exactly these back on.\n\n# --- Turn off\n")
        for row in groups[policy.OFF]:
            f.write("\t".join(row) + "\n")
        f.write("\n# --- Your call: could be ads, could be useful. Delete the # to turn one off.\n")
        for row in groups[policy.ASK]:
            f.write("# " + "\t".join(row) + "\n")
    print(phone_line(reader))
    print(f"{len({k[0] for k in live})} apps with notifications on, {len(live)} channels. Nothing was changed.\n")
    print(f"TURN OFF ({len(groups[policy.OFF])}): these look like ads")
    for _, _, label in groups[policy.OFF]:
        print(f"  {label}")
    print(f"\nYOUR CALL ({len(groups[policy.ASK])}): could be either, left on unless you choose")
    for _, _, label in groups[policy.ASK]:
        print(f"  {label}")
    kept = len(live) - len(groups[policy.OFF]) - len(groups[policy.ASK])
    print(f"\nLEFT ALONE: the other {kept}, like orders, OTPs, payments, calls and chats.")
    print(f"\nList saved to {os.path.relpath(path, ROOT)}")
    print("Check it, then preview:  python tool/promo.py off " + os.path.relpath(path, ROOT).replace(os.sep, "/"))


def run_engine(serial, action, items):
    """Hands a list to chan_fast and prints what it says in English."""
    hide = re.compile(r"^营销渠道仍开着") if action == "on" else None     # on an undo, "still on" is the goal, not a problem
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
        for row in items:
            f.write("\t".join(row) + "\n")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.Popen([sys.executable, os.path.join(HERE, "chan_fast.py"), "-s", serial, action, f.name],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            if not (hide and hide.match(line)):
                print(english(line), flush=True)
        return proc.wait()
    finally:
        os.unlink(f.name)


def change(serial, action, path, only, yes):
    if not os.path.exists(path):
        sys.exit(f"Can't find {path}. Run: python tool/promo.py scan")
    items = load(path)
    if only:
        word = only.lower()
        items = [i for i in items if word in " ".join(i).lower()]
    if not items:
        sys.exit("Nothing to do: no channels in that list" + (f" match '{only}'." if only else "."))
    reader = ShellPhone(serial)
    channels, app_off = parse(reader)
    verb = "turn off" if action == "off" else "turn back on"
    print(f"This will {verb} {len(items)}:")
    for pk, cid, label in items:
        print(f"  {label}" + ("" if (pk, cid) in channels else "  (not on this phone)"))
    if not yes:
        print("\nPreview only, nothing changed. Add --yes to do it.")
        return 0
    print()
    code = run_engine(serial, action, items)
    print("\nDone. Undo any time:  python tool/promo.py undo " + path.replace(os.sep, "/") if code == 0 and action == "off"
          else ("\nDone." if code == 0 else "\nFinished with problems, see above. Anything that changed can be undone with: undo"))
    return code


def phone_script(serial):
    """Path of a script recorded on exactly this model and OS, or None. A near match isn't good enough here."""
    import run as upstream
    info = upstream.info(serial)
    path, borrowed = upstream.recipe_for(info["model"], info["brand"], info)
    if not path or borrowed or not upstream.build_ok(info, upstream.recipe_meta(path)["build"]):
        return None, info
    return path, info


def phone_switches(serial, yes):
    path, info = phone_script(serial)
    if not path:
        print(f"No script for {info['brand']} {info['model']} on this OS version yet, so nothing to do here.")
        print("Promotional notifications still work on any phone: python tool/promo.py scan")
        return 0
    with open(path, encoding="utf-8") as f:
        steps = re.findall(r'^@step\("(.+?)"\)', f.read(), flags=re.M)
    print(f"{info['brand']} {info['model']} has a script. It checks: " + ", ".join(steps) + ".", flush=True)
    if not yes:
        print("Preview only, nothing changed. Add --yes to do it. You can turn any of these back on in the phone's settings.")
        return 0
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "fast.py"), "-s", serial, "run", path],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
    problems = 0
    for line in proc.stdout:
        line = english(line.rstrip("\r\n"))
        problems += "✗" in line                # a step can fail while the run as a whole exits 0
        print(line, flush=True)
    code = proc.wait()
    if code or problems:
        print("\nFinished with problems, see above. Run it again, or change the setting by hand in the phone's settings.")
        return code or 1
    print("\nDone.")
    return 0


def cleanup(serial):
    reader = ShellPhone(serial)
    reader.shell("rm -rf /data/local/tmp/u2.jar /data/local/tmp/u2 /data/local/tmp/aac-labels.dex")
    left = reader.shell("ls /data/local/tmp").output.split()
    print("Removed the helper from the phone." if "u2.jar" not in left else "The helper is still there, try again.")
    print("When you're finished, turn off USB debugging: Settings, System management, Developer options.")
    return 0


def main(argv):
    serial = None
    if argv[:1] == ["-s"]:
        if len(argv) < 2:
            sys.exit(__doc__)
        serial, argv = argv[1], argv[2:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    yes = "--yes" in rest
    rest = [a for a in rest if a != "--yes"]
    only = None
    if "--only" in rest:
        i = rest.index("--only")
        if i + 1 >= len(rest):
            sys.exit("--only needs a word, like --only photos")
        only = rest[i + 1]
        del rest[i:i + 2]
    if cmd == "scan":
        scan(pick_serial(serial))
        return 0
    if cmd == "phone":
        return phone_switches(pick_serial(serial), yes)
    if cmd == "cleanup":
        return cleanup(pick_serial(serial))
    if cmd in ("off", "undo"):
        if not rest:
            sys.exit(f"Which list? python tool/promo.py {cmd} backups/promo-list-....tsv")
        return change(pick_serial(serial), "off" if cmd == "off" else "on", rest[0], only, yes)
    sys.exit(__doc__)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (RuntimeError, adb_link.DeviceLost) as e:
        sys.exit(f"Stopped: {e}")
