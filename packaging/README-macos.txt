Physiognomy.ai — standalone macOS app
=====================================

Pull a face or throw a hand gesture at your webcam and the matching meme
pops up on screen for a few seconds. 100% local — nothing is recorded or
sent anywhere.

Needs: macOS 11 (Big Sur) or newer, on Apple Silicon or Intel, with a
working webcam (the MacBook Air's built-in FaceTime camera is fine).


-------------------------------------------------------------------------
STEP 1 — UNZIP, AND KEEP THE FOLDER TOGETHER
-------------------------------------------------------------------------
Double-click the .zip to unzip it. Inside you'll see:

    Physiognomy.app      <- the app you launch
    config.yaml          <- settings (optional to edit)
    assets/              <- the meme images
    models/              <- the face/hand AI models

Keep all of these together in the same folder. The app reads config.yaml,
assets/ and models/ from right beside itself. If you move Physiognomy.app
out on its own, it won't find them and will show an error.

Tip: don't run it straight from the Downloads folder — drag the whole
unzipped folder to your Desktop or Applications-adjacent folder first.


-------------------------------------------------------------------------
STEP 2 — OPEN IT THE FIRST TIME (bypassing Gatekeeper)
-------------------------------------------------------------------------
This app is not signed with an Apple Developer certificate, so macOS blocks
it on the first launch. This is expected. Do ONE of the following:

  Easiest (macOS 12 / 13 / 14):
    1. Right-click (or Control-click) Physiognomy.app -> "Open".
    2. In the warning dialog, click "Open" again.
    (You only do this once; afterwards a normal double-click works.)

  macOS 15 (Sequoia) — if right-click "Open" doesn't offer a bypass:
    1. Double-click the app once (it gets blocked — that's fine).
    2. Open  System Settings -> Privacy & Security.
    3. Scroll down to the Security section. You'll see a line like
       '"Physiognomy" was blocked...'. Click "Open Anyway".
    4. Confirm with Touch ID / your password.

  If it still refuses ("app is damaged / can't be opened"):
    This happens when macOS quarantines files from the internet. Open the
    Terminal app, then run (drag the folder in to fill the path):

        xattr -dr com.apple.quarantine "/path/to/Physiognomy.app"

    Then try Step 2 again.


-------------------------------------------------------------------------
STEP 3 — ALLOW THE CAMERA
-------------------------------------------------------------------------
On first successful launch, macOS asks to let the app use the camera.
Click "Allow" / "OK".

If you missed the prompt or the preview window is black:
    System Settings -> Privacy & Security -> Camera
    -> turn ON the switch next to Physiognomy.
Then quit and reopen the app.


-------------------------------------------------------------------------
USING IT
-------------------------------------------------------------------------
A preview window opens showing your mirrored webcam feed. Make a gesture and
the matching meme pops up on top for a few seconds.

Hotkeys (click the preview window first so it has keyboard focus):
    q   Quit
    p   Toggle the preview on/off (detection keeps running)
    c   Clear all open popups

The 10 triggers:
    head_shake        Shake your head left-right a few times
    squint_smile      Squint + a faint smile
    nerd              Index finger up, other fingers curled
    thumbs_up         Thumb up, four fingers balled into a fist
    fist_cover_mouth  Cover your mouth with a fist
    lip_pull          Shaka hand, pinky pulls lower lip down, teeth showing
    hands_up          Both palms open, raised above your chin, held still
    pray              Hands together near your mouth, prayer-style
    double_guns       Both "finger gun" hands — CLEARS all popups, then
                      shows its own meme
    six_seven         Both open hands bobbing up-down fast, several times


-------------------------------------------------------------------------
IF SOMETHING GOES WRONG
-------------------------------------------------------------------------
The app writes a log file named  physiognomy.log  next to Physiognomy.app
every time it launches, and shows a popup on fatal errors. If it won't work,
open physiognomy.log (TextEdit) and send it over — it names the exact cause.

Common ones:
  - Black preview / "Could not open webcam": camera permission (see Step 3),
    or another app (Zoom, Teams, Photo Booth) is holding the camera — quit it.
  - "config.yaml not found" / missing meme errors: the app got separated from
    its folder. Re-unzip and keep everything together (Step 1).


-------------------------------------------------------------------------
TWEAKING (optional)
-------------------------------------------------------------------------
Triggers firing too easily or not enough? Open config.yaml (it's next to the
app) in TextEdit — thresholds and cooldowns live under  thresholds:  and
gestures:. Swap any meme by replacing the matching file in  assets/.
