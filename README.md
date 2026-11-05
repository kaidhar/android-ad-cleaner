# Android Ad Cleaner, India fork

> **Want the full cleanup?** Use [Clean Your Phone](https://github.com/kaidhar/cleanyourphone). It includes this notification cleaning, and also disables ad apps and blocks ad servers. This fork stays up for anyone who only wants the notification part.

Turn off the promotional notifications on your Android phone and keep the useful ones. Flipkart's offers go, Flipkart's order updates stay. No root, nothing uninstalled, and you can undo it.

This is a fork of [rddmwmddr/android-ad-cleaner](https://github.com/rddmwmddr/android-ad-cleaner), which was built for phones sold in China and matches Chinese menu text. This fork adds English rules and an English command line, so it works on phones with English menus. The careful part, switching one setting at a time and checking the result, is the original author's work. [The original README is here](README.zh-CN.md).

## What's been tested

**One phone so far: a vivo V27 (V2231) on Funtouch OS 15, Android 15, India build.** The scan, turning a channel off and the undo were all checked on that phone.

| Part | Other phones |
| --- | --- |
| `scan` | Should work on any Android 8 or later with English menus, because every app's channels are stored the same way. Not yet tried. |
| `off` and `undo` | Settings screens differ by brand. The original project handles many of them, but none of the others have been tried in English. Try `--only` with one channel first. |
| `phone` | vivo V27 only. Each model needs its own script. |

If you try it on another phone, please open an issue with your phone's model and what happened, even if it failed.

## What you need

- A Windows, Mac or Linux computer with Python 3.10 or later
- [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) (`adb`)
- A USB data cable
- USB debugging turned on: go to Settings, About phone, tap the build or software version 7 times, then turn on USB debugging in Developer options. The menu names change a little between brands.

```bash
git clone https://github.com/kaidhar/android-ad-cleaner
cd android-ad-cleaner
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # on Mac or Linux: .venv/bin/pip
```

Or paste this into an AI coding assistant that can run commands on your computer:

```text
Clone https://github.com/kaidhar/android-ad-cleaner and read README.md and AGENTS.md.
Then scan my connected phone with tool/promo.py and show me the list. Don't turn anything off until I've checked it.
```

## How to use it

Connect the phone and keep it unlocked. On Mac or Linux, use `.venv/bin/python` in place of `.venv/Scripts/python`.

**1. Scan.** This only reads. It changes nothing and saves a list file in `backups/`.

```bash
.venv/Scripts/python tool/promo.py scan
```

```
TURN OFF (14): these look like ads
  Flipkart: Offer zone
  Hotstar: Promotional messages
  ...
YOUR CALL (23): could be either, left on unless you choose
  Hotstar: General
  Play Store: Payments, Deals, and Recommendations
  ...
LEFT ALONE: the other 417, like orders, OTPs, payments, calls and chats.
```

**2. Check the list.** Open the file in any text editor. Lines starting with `#` are skipped: delete the `#` to include one, add a `#` to spare one. "Left alone" only means no rule matched, so read the list rather than trusting it.

**3. Try one channel, then the rest.** Without `--yes`, `off` only shows what would change. The phone moves through screens by itself while this runs, so don't touch it.

```bash
.venv/Scripts/python tool/promo.py off backups/promo-list-XXXX.tsv --only photos --yes
.venv/Scripts/python tool/promo.py off backups/promo-list-XXXX.tsv --yes
```

**4. Undo, if you want to.** This turns everything in that list back on. Add `--only` to pick some.

```bash
.venv/Scripts/python tool/promo.py undo backups/promo-list-XXXX.tsv --yes
```

**5. Clean up.** This removes the helper from the phone. Then turn off USB debugging.

```bash
.venv/Scripts/python tool/promo.py cleanup
```

### vivo V27 only

`phone` also turns off vivo's own "Personalized recommendations" and V-Appstore's promotional notifications. To undo it, turn them back on in the phone's settings.

```bash
.venv/Scripts/python tool/promo.py phone --yes
```

## What it doesn't do

- **It only stops notifications.** Ads inside apps, and the promotions on V-Appstore's home screen, stay.
- **New channels can appear.** If an app adds a channel after an update, scan again.
- **It can't catch everything.** Some apps put promotions and real alerts in the same channel. Those land in "your call", or get left alone if the name gives nothing away.
- **It never agrees to anything for you,** never uninstalls an app and doesn't need root.

## What goes where

- **The command line sends nothing anywhere.** It only talks to your phone over the USB cable.
- **It leaves a small helper on the phone,** `u2.jar` (about 4 MB) in a temporary folder. `cleanup` removes it.
- **Your list file shows which apps you have.** It's in `backups/`, which git ignores, so don't share it by accident.
- **The desktop app in `gui/` isn't part of this fork's work.** It's still in Chinese, and its update check and error reports go to the original author's servers. Use the command line.

## Credits and license

MIT, same as the original. See [LICENSE](LICENSE). All the credit for the switching engine, the model scripts and the safety rules goes to [rddmwmddr](https://github.com/rddmwmddr/android-ad-cleaner) and its contributors.
