"""English channel rules: what gets turned off, what the owner decides, what's never listed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tool"))
import promo_policy as policy
from promo_policy import ASK, KEEP, OFF, classify


class Promotional(unittest.TestCase):
    def test_plain_promotional_names_go(self):
        for name in ("Promotions", "Promotional messages", "Offers", "Offer zone", "Welcome Offers", "Deals",
                     "Newsletter", "Marketing", "Promotions and Marketing", "New Releases & Recommendations",
                     "Discounts", "Coupons", "Cashback", "Sale", "Sponsored", "Ads", "Offers messages"):
            self.assertEqual(classify(name, "x", "com.shop.app"), OFF, name)

    def test_the_id_can_give_it_away(self):
        for cid in ("promotional_notifications", "020_PlayStationPromotions", "marketing_notification_id", "crosssell", "offers", "300_ia_coupon_comeback"):
            self.assertEqual(classify("From the app", cid, "com.shop.app"), OFF, cid)

    def test_vivo_marketing_lane(self):
        self.assertEqual(classify("Promotional messages", "VPushChannel_0", "com.tv.app"), OFF)
        self.assertEqual(classify("Service messages", "VPushChannel_4", "com.tv.app"), ASK)
        self.assertEqual(classify("Promotional messages", "VPushChannel_1", "com.tv.app"), OFF)


class NeverByDefault(unittest.TestCase):
    def test_useful_channels_stay(self):
        for name in ("Order updates", "Delivery status", "OTP", "Payments", "Transaction alerts", "Security alerts",
                     "Incoming calls", "Missed calls", "Chats", "Account updates", "Downloads", "System update",
                     "Booking confirmation", "Flight status", "Trip reminders", "Navigation urgent updates",
                     "Expense updated/deleted", "Connection status change"):
            self.assertEqual(classify(name, "plain_id", "com.shop.app"), KEEP, name)

    def test_mixed_names_go_to_the_owner(self):
        for name in ("Offers and Updates", "Payments, Deals, and Recommendations", "Offers on your order", "Deal alerts"):
            self.assertEqual(classify(name, "x", "com.shop.app"), ASK, name)

    def test_vague_names_go_to_the_owner(self):
        for name in ("General", "General notifications", "News", "Announcements", "Suggestions", "New & trending places", "Suggested features"):
            self.assertEqual(classify(name, "x", "com.shop.app"), ASK, name)

    def test_vague_names_in_messaging_apps_stay(self):
        for pk in ("com.whatsapp", "org.telegram.messenger", "com.google.android.gm"):
            self.assertEqual(classify("General", "x", pk), KEEP, pk)

    def test_messaging_apps_can_still_have_promotions(self):
        self.assertEqual(classify("Promotional messages", "VPushChannel_0", "org.telegram.messenger"), OFF)

    def test_system_plumbing_is_never_listed(self):
        for pk, name in (("android", "Recommendations"), ("com.android.phone", "Offers"), ("com.google.android.gms", "Deals"),
                         ("com.bbk.updater", "Promotions"), ("com.vivo.pushservice", "General")):
            self.assertEqual(classify(name, "x", pk), KEEP, pk)

    def test_words_inside_other_words_dont_count(self):
        # each of these was a real false match from looser patterns
        self.assertEqual(classify("Connection status change", "openvpn_newstat", "com.vpn.app"), KEEP)
        self.assertEqual(classify("Idealista", "x", "com.home.app"), KEEP)
        self.assertEqual(classify("Upload status", "x", "com.home.app"), KEEP)
        self.assertEqual(classify("Headline", "x", "com.home.app"), KEEP)

    def test_empty_is_safe(self):
        self.assertEqual(classify("", "", ""), KEEP)
        self.assertEqual(classify(None, None, None), KEEP)


class Names(unittest.TestCase):
    def test_readable_app_names(self):
        self.assertEqual(policy.app_name("com.flipkart.android"), "Flipkart")
        self.assertEqual(policy.app_name("in.startv.hotstar"), "Hotstar")
        self.assertEqual(policy.app_name("com.google.android.apps.photos"), "Google Photos")
        self.assertEqual(policy.app_name(""), "?")


class Safety(unittest.TestCase):
    """A switch whose job is protecting you has to stay on. The rule only knew Chinese."""

    def setUp(self):
        import fast
        self.want = fast.want_state

    def test_protective_english_switches_stay_on(self):
        for title in ("Limit ad tracking", "Block ads", "Prevent ad tracking", "Stop personalized ads",
                      "Disable personalized recommendations", "Opt out of ads personalization",
                      "Don't show personalized ads", "Do not track ads", "Turn off personalized ads"):
            self.assertIs(self.want(title), True, title)

    def test_english_ad_switches_go_off(self):
        for title in ("Personalized ads", "Personalized recommendations", "Show ads"):
            self.assertIs(self.want(title), False, title)

    def test_protective_words_without_ads_arent_touched(self):
        self.assertIsNone(self.want("Block unknown callers"))
        self.assertIsNone(self.want("Limit background data"))

    def test_chinese_still_works(self):
        self.assertIs(self.want("限制广告跟踪"), True)
        self.assertIs(self.want("个性化广告"), False)


if __name__ == "__main__":
    unittest.main()
