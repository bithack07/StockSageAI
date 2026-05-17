# StockSage AI — Mobile (Expo)

> **Run commands from this folder** (`StockSageAI/mobile`), not the parent `StockSageAI` repo root.  
> If you cloned to `~/workspace/StockSageAI`, use:
> ```bash
> cd StockSageAI/mobile
> ```

## Install on your phone (development — fastest)

### 1. Start the backend (on your Mac)

Phone cannot use `localhost` — the API must listen on all interfaces:

```bash
cd ../backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Keep Postgres/Redis running as usual.

### 2. Same Wi‑Fi

Mac and phone must be on the **same Wi‑Fi** network.

### 3. Install Expo Go

- **iPhone:** [Expo Go on the App Store](https://apps.apple.com/app/expo-go/id982107779)
- **Android:** [Expo Go on Google Play](https://play.google.com/store/apps/details?id=host.exp.exponent)

### 4. Start Metro

Uses **Expo SDK 54** (React Native 0.81, React 19). Requires a recent **Expo Go** from the App Store / Play Store.

```bash
cd mobile
npm install
npx expo start
```

Scan the **QR code** with:

- iPhone: Camera app → opens Expo Go  
- Android: Expo Go app → Scan QR  

The app auto-detects your Mac’s IP from the Expo dev server (no `.env` required in most cases).

### 5. Optional: set API URL manually

If auto-detection fails, find your Mac’s IP (`System Settings → Network`, e.g. `192.168.1.42`):

```bash
cp .env.example .env
```

```env
EXPO_PUBLIC_API_URL=http://192.168.1.42:8000
EXPO_PUBLIC_WS_URL=ws://192.168.1.42:8000
```

Restart Expo (`npx expo start`).

### 6. Sign in

Use the same account as desktop. The login screen shows **green** “Connected” when the backend is reachable.

---

## Android emulator

```bash
npx expo start --android
```

API defaults to `http://10.0.2.2:8000` (emulator → host machine).

## iOS Simulator (Mac only)

```bash
npx expo start --ios
```

`localhost:8000` works if the backend runs on the same Mac.

---

## Standalone app (TestFlight / APK — not Expo Go)

For a installable build without Expo Go:

```bash
npm install -g eas-cli
eas login
eas build:configure
eas build --platform android   # or ios
```

Requires an [Expo](https://expo.dev) account. Point `EXPO_PUBLIC_API_URL` at your production HTTPS API before building.

---

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| Login “Network error” | Backend `--host 0.0.0.0`, same Wi‑Fi, check IP in login banner |
| Analysis never loads | Sign in first; WebSocket needs JWT |
| Red backend banner | Open `http://YOUR_IP:8000/health` in phone browser — should show `{"status":"ok"}` |
| Works on simulator, not phone | Replace `localhost` with LAN IP in `.env` |
