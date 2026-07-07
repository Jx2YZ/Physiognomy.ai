Physiognomy.ai — standalone Windows app
=======================================

Pull a face or throw a hand gesture at your webcam and the matching meme
pops up on screen for a few seconds. 100% local — nothing is recorded or
sent anywhere.


RUN IT
------
1. UNZIP THIS FOLDER FIRST. Do not run the .exe from inside the zip
   preview — it needs the folders next to it (_internal, assets, models).
2. Double-click  Physiognomy.exe
3. A preview window opens showing your mirrored webcam feed. Make a
   gesture; the meme appears.

Needs: 64-bit Windows 10 or 11, and a working webcam.


FIRST-LAUNCH WARNINGS (expected — the app is unsigned)
------------------------------------------------------
- "Windows protected your PC" (SmartScreen):
      click  More info  ->  Run anyway
- Antivirus may flag it briefly. It's a false positive from unsigned
  PyInstaller apps; allow it.


HOTKEYS  (click the preview window first so it has focus)
--------------------------------------------------------
  q   Quit
  p   Toggle the preview on/off (detection keeps running)
  c   Clear all open popups


THE 10 TRIGGERS
---------------
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


IF IT DOESN'T WORK
------------------
- Camera black / "Could not open webcam":
    Settings -> Privacy & security -> Camera ->
    "Let desktop apps access your camera"  (turn ON).
    Also close any other app using the webcam (Zoom, Teams, etc.).
- Anything else: a file named  physiognomy.log  appears next to the .exe
  after each launch, and fatal errors also show a popup. Send me that log.


TUNING (optional)
-----------------
Triggers firing too eagerly or not enough? Edit  config.yaml  next to the
.exe — thresholds and cooldowns live under  thresholds:  and  gestures:.
Swap any meme by replacing the matching file in  assets\.
