import Phaser from "phaser";
import { getMapAudioGainForKey, isMapAudioKey } from "./map-audio-levels";

// Keep the game's looping map audio alive when the browser tab/window loses focus.
// Phaser pauses audio on blur by default, and Web Audio is more likely to be
// suspended by browsers in the background, so use HTML5 Audio for map ambience.
const phaserRuntime = Phaser as any;

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
// Ambient recordings can contain quiet lead-in/out material in addition to MP3
// encoder padding. Start the standby copy early enough that both boundaries are
// buried inside a long overlap instead of exposing a short silent notch.
const LOOP_OVERLAP_SECONDS = 5.0;
const CROSSFADE_MS = 4000;
const LOOP_MONITOR_MS = 100;
const HALF_PI = Math.PI / 2;

// Phaser's HTML5 Audio loader creates one HTMLAudioElement per key by default.
// A real crossfade needs two physical elements playing the same key at once,
// otherwise starting the standby sound steals the only available element and
// interrupts the active sound. Force two instances for map ambience at load time.
const loaderProto = phaserRuntime.Loader?.LoaderPlugin?.prototype as any;
if (loaderProto && !loaderProto.__summerEndMapAudioInstancesPatched) {
  const originalAudio = loaderProto.audio;

  loaderProto.audio = function loadMapAudioWithOverlapInstances(
    key: unknown,
    urls?: unknown,
    config?: Record<string, unknown>,
    xhrSettings?: unknown
  ) {
    const audioKey =
      typeof key === "string"
        ? key
        : String((key as { key?: unknown } | null)?.key ?? "");

    if (!isMapAudioKey(audioKey)) {
      return originalAudio.call(this, key, urls, config, xhrSettings);
    }

    const requestedInstances = Number(config?.instances ?? 0);
    const instances =
      Number.isFinite(requestedInstances) && requestedInstances >= 2
        ? Math.floor(requestedInstances)
        : 2;

    return originalAudio.call(
      this,
      key,
      urls,
      { ...(config ?? {}), instances },
      xhrSettings
    );
  };

  loaderProto.__summerEndMapAudioInstancesPatched = true;
}

const html5ManagerProto = phaserRuntime.Sound?.HTML5AudioSoundManager?.prototype as any;
if (html5ManagerProto && !html5ManagerProto.__summerEndSeamlessLoopPatched) {
  const originalAdd = html5ManagerProto.add;

  html5ManagerProto.add = function addWithSeamlessMapLoop(
    key: unknown,
    config?: Record<string, unknown>
  ) {
    const audioKey = String(key);

    // Ordinary/non-map sounds keep Phaser's normal behavior.
    if (!isMapAudioKey(audioKey)) {
      return originalAdd.call(this, key, config);
    }

    // MP3 files can contain encoder padding at their boundaries. A single
    // HTML5 Audio element with loop=true can therefore expose a short gap.
    // Use two independent Phaser HTML5 sound instances and overlap/crossfade
    // them before the current copy reaches its encoded end.
    const childConfig = {
      ...(config ?? {}),
      loop: false,
      volume: 0,
    };
    const sounds = [
      originalAdd.call(this, key, childConfig),
      originalAdd.call(this, key, childConfig),
    ] as any[];

    const mapGain = getMapAudioGainForKey(audioKey);
    let masterVolume = Number(config?.volume ?? 1);
    if (!Number.isFinite(masterVolume)) masterVolume = 1;
    masterVolume = clamp01(masterVolume);

    let running = false;
    let activeIndex = 0;
    let nextIndex = 1;
    let crossfading = false;
    let fadeStartedAt = 0;
    let fadeProgress = 0;
    let monitorTimer: number | undefined;

    const targetVolume = () => clamp01(masterVolume * mapGain);

    const setChildVolume = (index: number, value: number) => {
      const sound = sounds[index];
      if (sound && typeof sound.setVolume === "function") {
        sound.setVolume(clamp01(value));
      }
    };

    const applyCurrentVolumes = () => {
      const target = targetVolume();
      if (!crossfading) {
        setChildVolume(activeIndex, target);
        setChildVolume(1 - activeIndex, 0);
        return;
      }

      // Equal-power crossfade: unlike a linear 50/50 fade, this keeps perceived
      // power roughly constant through the middle instead of producing a dip.
      const oldGain = Math.cos(fadeProgress * HALF_PI);
      const newGain = Math.sin(fadeProgress * HALF_PI);
      setChildVolume(activeIndex, target * oldGain);
      setChildVolume(nextIndex, target * newGain);
    };

    const finishCrossfade = () => {
      if (!crossfading) return;
      const oldIndex = activeIndex;
      activeIndex = nextIndex;
      nextIndex = 1 - activeIndex;
      crossfading = false;
      fadeProgress = 0;
      sounds[oldIndex]?.stop?.();
      setChildVolume(oldIndex, 0);
      setChildVolume(activeIndex, targetVolume());
    };

    const beginCrossfade = () => {
      if (!running || crossfading) return false;
      nextIndex = 1 - activeIndex;
      const next = sounds[nextIndex];
      if (!next) return false;

      next.stop?.();
      setChildVolume(nextIndex, 0);

      // Do not fade the current track until the standby track has actually
      // started. If HTML5 Audio cannot allocate/start it yet, monitor() retries
      // every 100ms while the current track keeps playing at full level.
      const started = next.play?.() === true;
      if (!started) return false;

      crossfading = true;
      fadeStartedAt = performance.now();
      fadeProgress = 0;
      applyCurrentVolumes();
      return true;
    };

    const recoverFromUnexpectedEnd = (endedIndex: number) => {
      if (!running || endedIndex !== activeIndex) return;

      if (crossfading) {
        fadeProgress = 1;
        applyCurrentVolumes();
        finishCrossfade();
        return;
      }

      // Fallback for aggressive browser timer throttling: if the overlap check
      // missed the window completely, start the standby copy immediately. Only
      // switch ownership after play() confirms that the standby copy started.
      nextIndex = 1 - activeIndex;
      const next = sounds[nextIndex];
      if (!next) return;
      next.stop?.();
      setChildVolume(nextIndex, targetVolume());
      const started = next.play?.() === true;
      if (!started) {
        setChildVolume(nextIndex, 0);
        return;
      }
      activeIndex = nextIndex;
      nextIndex = 1 - activeIndex;
    };

    sounds.forEach((sound, index) => {
      sound?.on?.("complete", () => recoverFromUnexpectedEnd(index));
    });

    const monitor = () => {
      if (!running) return;

      if (crossfading) {
        fadeProgress = clamp01((performance.now() - fadeStartedAt) / CROSSFADE_MS);
        applyCurrentVolumes();
        if (fadeProgress >= 1) finishCrossfade();
        return;
      }

      const active = sounds[activeIndex];
      const duration = Number(active?.duration ?? 0);
      const seek = Number(active?.seek ?? 0);
      if (
        Number.isFinite(duration) &&
        Number.isFinite(seek) &&
        duration > LOOP_OVERLAP_SECONDS + 0.2 &&
        duration - seek <= LOOP_OVERLAP_SECONDS
      ) {
        beginCrossfade();
      }
    };

    const startMonitor = () => {
      if (monitorTimer !== undefined) window.clearInterval(monitorTimer);
      monitorTimer = window.setInterval(monitor, LOOP_MONITOR_MS);
    };

    const stopMonitor = () => {
      if (monitorTimer !== undefined) {
        window.clearInterval(monitorTimer);
        monitorTimer = undefined;
      }
    };

    const wrapper = {
      play: () => {
        running = true;
        activeIndex = 0;
        nextIndex = 1;
        crossfading = false;
        fadeProgress = 0;
        sounds.forEach((sound) => sound?.stop?.());
        setChildVolume(0, targetVolume());
        setChildVolume(1, 0);
        const result = sounds[0]?.play?.();
        startMonitor();
        return result;
      },
      stop: () => {
        running = false;
        crossfading = false;
        fadeProgress = 0;
        stopMonitor();
        sounds.forEach((sound) => sound?.stop?.());
        return wrapper;
      },
      destroy: () => {
        wrapper.stop();
        sounds.forEach((sound) => sound?.destroy?.());
      },
      setVolume: (value: number) => {
        const nextMaster = Number(value);
        masterVolume = Number.isFinite(nextMaster) ? clamp01(nextMaster) : masterVolume;
        applyCurrentVolumes();
        return wrapper;
      },
      get volume() {
        return masterVolume;
      },
      get isPlaying() {
        return running;
      },
    };

    return wrapper;
  };

  html5ManagerProto.__summerEndSeamlessLoopPatched = true;
}

// The Phaser map title occupies the upper-left corner of the game canvas. The
// money HUD is created later by main.ts as a fixed DOM element, so move it into
// the upper-right HUD stack after login instead of letting both occupy ~14px/14px.
const positionMoneyHud = () => {
  const hud = Array.from(document.body.children).find(
    (child): child is HTMLDivElement =>
      child instanceof HTMLDivElement && (child.textContent ?? "").startsWith("所持金")
  );
  if (!hud) return false;

  Object.assign(hud.style, {
    left: "auto",
    right: "14px",
    top: "96px",
    maxWidth: "calc(100vw - 28px)",
    boxSizing: "border-box",
  } as Partial<CSSStyleDeclaration>);
  return true;
};

const installMoneyHudLayout = () => {
  if (positionMoneyHud()) return;
  const observer = new MutationObserver(() => {
    if (positionMoneyHud()) observer.disconnect();
  });
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
};

if (document.body) installMoneyHudLayout();
else window.addEventListener("DOMContentLoaded", installMoneyHudLayout, { once: true });

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