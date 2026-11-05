"""Which notification channels look like ads, for phones with English menus.

Kept apart from channel_policy.py, whose Chinese rules are frozen by upstream's tests. A pure function: no phone needed.

Three answers:
  OFF   clearly promotional: on the list, ready to turn off
  ASK   could be an ad or could be useful: on the list but commented out, the owner decides
  KEEP  not listed

When in doubt it answers ASK, never OFF. Turning off a delivery alert by mistake is worse than leaving an ad on.
"""
import re

OFF, ASK, KEEP = "off", "ask", "keep"

# Words that mean a channel is promotional, in its name.
PROMO_NAME = re.compile(
    r"(?<![a-z])(?:promo|promos|promotion|promotions|promotional|marketing|offers?|deals?|discounts?|coupons?|"
    r"cashback|sales?|newsletters?|campaigns?|sponsored|advert\w*|ads?|recommendations?|recommended|"
    r"upsell|cross-?sell|re-?engagement)(?![a-z])", re.I)

# The same idea in a channel ID, which runs words together: PlayStationPromotions, marketing_notification_id.
PROMO_ID = re.compile(
    r"promotion|marketing|coupon|cross-?sell|upsell|re-?engag|newsletter|"
    r"(?<![a-z])(?:promo|promos|offers?|deals?|ads?|sales?)(?![a-z])", re.I)

# Words that mean a channel may matter. Matched on the name, because IDs are full of accidents.
SERVICE_NAME = re.compile(
    r"(?<![a-z])(?:orders?|deliver\w*|otps?|verification|payments?|transactions?|bills?|invoices?|refunds?|banking|"
    r"security|fraud|login|sign-?in|accounts?|passwords?|warnings?|safety|emergency|alerts?|alarms?|timers?|reminders?|"
    r"calls?|calling|voicemail|chats?|sms|mentions?|replies|comments?|"
    r"downloads?|downloader|uploads?|backup|sync|syncing|updates?|updated|system|setup|"
    r"bookings?|tickets?|flights?|trips?|rides?|navigation|traffic|location|expenses?|"
    r"connection|vpn|playback|media|recording|screenshots?)(?![a-z])", re.I)

# Vague names. Promotions often hide in these, and so do real alerts, so a person decides.
VAGUE_NAME = re.compile(
    r"(?<![a-z])(?:general|announcements?|news|suggestions?|suggested|trending|what'?s new|new releases|"
    r"tips|stories|engagement)(?![a-z])", re.I)

# vivo files pushed marketing under these fixed IDs (found by upstream, seen on a V2231 too).
VIVO_MARKETING_ID = re.compile(r"^VPushChannel_(?:0|4|6)$", re.I)

# The phone's own plumbing. Never list these, whatever they're called.
SYSTEM_PACKAGE = re.compile(
    r"^(?:android|com\.android\.(?:phone|settings|systemui|server\.\w+|dynsystem|shell|providers\.\w+)|"
    r"com\.google\.android\.(?:cellbroadcast\w*|gms)|com\.mediatek\.\w+|com\.bbk\.updater|com\.vivo\.pushservice)$")

# Messaging apps: a "General" channel here is someone's messages, not an ad. Promotional names are still caught.
CONVERSATION_PACKAGE = re.compile(
    r"^(?:com\.whatsapp(?:\.w4b)?|org\.telegram\.messenger|com\.google\.android\.apps\.messaging|"
    r"com\.google\.android\.gm|com\.Slack|com\.discord)$")


def classify(name, channel_id="", package=""):
    """OFF, ASK or KEEP for one channel that's currently switched on."""
    name, channel_id = (name or "").strip(), (channel_id or "").strip()
    if SYSTEM_PACKAGE.match(package or ""):
        return KEEP
    promo_name = bool(PROMO_NAME.search(name))
    promo_id = bool(PROMO_ID.search(channel_id))
    service = bool(SERVICE_NAME.search(name))
    if VIVO_MARKETING_ID.match(channel_id):
        return OFF if promo_name and not service else ASK
    if promo_name:
        return ASK if service else OFF         # "Offers and order updates": could be either
    if promo_id:
        return ASK if service else OFF         # "From PlayStation" with the ID PlayStationPromotions
    if service:
        return KEEP
    if VAGUE_NAME.search(name):
        return KEEP if CONVERSATION_PACKAGE.match(package or "") else ASK
    return KEEP


def app_name(package):
    """A readable guess from the package name, without running anything on the phone."""
    junk = {"com", "in", "org", "net", "co", "uk", "app", "apps", "android", "mobile", "client", "application", "global",
            "www", "io", "me", "main", "passenger", "mediaclient", "music", "thirdpartyclient", "google", "amazon"}
    parts = [p for p in (package or "").split(".") if p]
    keep = [p for p in parts if p.lower() not in junk]
    known = {"com.google.android.apps.photos": "Google Photos", "com.google.android.apps.maps": "Google Maps",
             "com.android.vending": "Play Store", "com.google.android.youtube": "YouTube",
             "com.amazon.avod.thirdpartyclient": "Prime Video", "in.amazon.mShop.android.shopping": "Amazon",
             "in.startv.hotstar": "Hotstar", "com.scee.psxandroid": "PlayStation", "com.netflix.mediaclient": "Netflix",
             "com.spotify.music": "Spotify", "com.application.zomato": "Zomato", "in.swiggy.android": "Swiggy",
             "com.grabtaxi.passenger": "Grab", "com.gojek.app": "Gojek", "org.telegram.messenger": "Telegram",
             "com.android.launcher3": "Home screen", "com.lgeha.nuts": "LG ThinQ", "com.google.android.apps.wellbeing": "Digital Wellbeing",
             "com.google.android.projection.gearhead": "Android Auto", "com.bbk.theme": "Themes", "com.vivo.appstore": "V-Appstore"}
    if package in known:
        return known[package]
    word = keep[0] if keep else (parts[-1] if parts else "?")
    return word[:1].upper() + word[1:]
