import Phaser from "phaser";
import { getMapAudioGainForKey } from "./map-audio-levels";

// Keep the game's looping map audio alive when the browser tab/window loses focus.
// Phaser pauses audio on blur by default, and Web Audio is more likely to be
// suspended by browsers in the background, so use HTML5 Audio for map ambience.
const phaserRuntime = Phaser as any;

// Apply map-specific loudness compensation at the sound-object boundary.
// main.ts can keep treating its volume as the user's master volume; every
// mapped ambience sound automatically receives:
//   effective volume = master volume * per-map gain
// This also covers later volume-slider changes because setVolume is wrapped.
const html5ManagerProto = phaserRuntime.Sound?.HTML5AudioSoundManager?.prototype as any;
if (html5ManagerProto && !html5ManagerProto.__summerEndMapGainPatched) {
  const originalAdd = html5ManagerProto.add;

  html5ManagerProto.add = function addWithMapGain(key: unknown, config?: Record<string, unknown>) {
    const sound = originalAdd.call(this, key, config);
    if (!sound || typeof sound.setVolume !== "function") return sound;

    const mapGain = getMapAudioGainForKey(String(key));
    const rawSetVolume = sound.setVolume.bind(sound);
    const clamp = (value: number) => Math.min(1, Math.max(0, value));

    sound.setVolume = (masterVolume: number) =>
      rawSetVolume(clamp(Number(masterVolume) * mapGain));

    // The constructor has already consumed config.volume before the wrapper was
    // installed, so re-apply it once through the calibrated path before play().
    const initialMasterVolume = Number(config?.volume ?? sound.volume ?? 1);
    sound.setVolume(Number.isFinite(initialMasterVolume) ? initialMasterVolume : 1);
    return sound;
  };

  html5ManagerProto.__summerEndMapGainPatched = true;
}

const OriginalGame = phaserRuntime.Game;

phaserRuntime.Game = class BackgroundAudioGame extends OriginalGame {
  constructor(config: any) {
    super({
      ...config,
      audio: {
        ...(config.audio ?? {}),
        disableWebAudio: true,
      },
    });

    // player-depth.ts is loaded as a separate browser entry point. Depending on
    // bundling, importing Phaser again there can produce a different runtime and
    // an empty Phaser.GAMES array. Expose the actual game instance created here
    // so depth sorting always targets the live game that owns the player objects.
    (window as any).__summerEnd3pmGame = this;
  }

  boot() {
    const result = super.boot();
    if (this.sound) {
      this.sound.pauseOnBlur = false;
    }
    return result;
  }
};

void import("./main");
