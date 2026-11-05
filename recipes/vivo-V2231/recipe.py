# vivo V27 (V2231), Funtouch OS 15 / Android 15, India build. English menus.
# Recorded 2026-11-05 on PD2269F_EX_A_15.2.26.1.W30.
#
# Notes from the real phone:
# 1. V-Appstore's settings gear has no label, so it's tapped by position on the Manage tab.
# 2. vivo nests two Switch nodes in a row. The outer one reports checked=false whatever the state, so fast.switches()
#    reads the inner one.
# 3. V-Appstore sometimes opens on a full-screen "Apps Selected for You" page instead of its tabs, with apps already
#    ticked and a Get button that would install them. store_manage_tab() leaves through "Homepage". It must never tap Get.
# 4. Only "Notifications" goes off on the alerts page. Its subtitle is "Receive timely notifications of exciting apps or
#    activities". Update reminders and the storage alerts stay, because they aren't ads.
#
# Not covered, because they weren't reachable on the phone this was recorded on (don't guess at them):
#   com.vivo.browser, com.vivo.magazine (lock screen posters), com.vivo.weather: disabled on that phone.
#   com.bbk.theme, com.vivo.game, com.vivo.imanager: stop at an agreement first, and this never agrees for you.
#   V-Appstore's home screen promos: there's no switch for them.
BUILD = "PD2269F_EX_A_15"
MODELS = ["V2231"]
import time

ONLY = globals().get("ONLY") or []
GEAR = (0.903, 0.0767)      # the unlabelled settings icon on V-Appstore's Manage tab, as a share of the screen


def step(name):
    def deco(f):
        if (not ONLY or name in ONLY) and p.locked():
            print(f"\n== {name}: the phone is locked, stopping"); return f
        if not ONLY or name in ONLY:
            print(f"\n== {name}"); p.miss = 0
            t = time.time()
            try:
                f()
            except Exception as e:
                print(f"  ✗ {e}")
            print(f"  ({time.time()-t:.0f} s)")
        return f
    return deco


@step("Personalized recommendations")
def _():
    p.d.shell("am start -f 0x10008000 -a android.settings.SETTINGS"); time.sleep(1.2)
    if p.entry("Privacy") and p.entry("Personalized recommendations"):
        p.off(only=["Personalized recommendations"], page="Settings: recommendations")


def store_manage_tab():
    """Gets to the Manage tab, past the store's pop-ups and its "Apps Selected for You" page."""
    p.start("com.vivo.appstore")
    for _ in range(3):
        if p.tab("Manage", maxwait=3.0):
            return True
        if not p.tap("Homepage", exact=True, scrolls=0, quiet=True):
            p.back()
        time.sleep(1.0)
    return False


@step("V-Appstore")
def _():
    if not store_manage_tab():
        print("  ✗ couldn't find the Manage tab"); return
    p.click(int(p.W * GEAR[0]), int(p.H * GEAR[1])); time.sleep(1.2)
    if not p.entry("Notifications & updates", scrolls=0):
        print("  ✗ couldn't open V-Appstore's settings"); p.back(2); return
    p.off(only=["Notifications"], page="V-Appstore: alerts")
    p.back(2)
