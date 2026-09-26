import Phaser from "phaser";

const SHRINE_AUDIO_KEY = "komorebi-cicadas-birds";
const SHRINE_AUDIO_URL = "/audio/komorebi-cicadas-birds-275634.mp3";
const LOOP_TRIM_SECONDS = 0.05;

const phaserRuntime = Phaser as any;
const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

type WebAudioContext = AudioContext & { state: AudioContextState };

let sharedContext: WebAudioContext | undefined;
let decodedBufferPromise: Promise<AudioBuffer> | undefined;

const getAudioContext = (): WebAudioContext => {
  if (sharedContext) return sharedContext;

  const AudioContextCtor =
    window.AudioContext ??
    (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

  if (!AudioContextCtor) {
    throw new Error("Web Audio API is not available in this browser.");
  }

  sharedContext = new AudioContextCtor() as WebAudioContext;
  return sharedContext;
};

const getDecodedBuffer = (context: AudioContext): Promise<AudioBuffer> => {
  if (!decodedBufferPromise) {
    decodedBufferPromise = fetch(SHRINE_AUDIO_URL, { cache: "force-cache" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to fetch shrine ambience: ${response.status}`);
        }
        return response.arrayBuffer();
      })
      .then((encoded) => context.decodeAudioData(encoded.slice(0)))
      .catch((error) => {
        decodedBufferPromise = undefined;
        throw error;
      });
  }

  return decodedBufferPromise;
};

const createShrineLoopSound = (config?: Record<string, unknown>) => {
  let requestedVolume = Number(config?.volume ?? 1);
  if (!Number.isFinite(requestedVolume)) requestedVolume = 1;
  requestedVolume = clamp01(requestedVolume);

  let running = false;
  let generation = 0;
  let source: AudioBufferSourceNode | undefined;
  let gainNode: GainNode | undefined;

  const disposeNodes = () => {
    if (source) {
      source.onended = null;
      try {
        source.stop();
      } catch {
        // Already stopped / never started.
      }
      source.disconnect();
      source = undefined;
    }
    if (gainNode) {
      gainNode.disconnect();
      gainNode = undefined;
    }
  };

  const startDecodedLoop = async (token: number) => {
    try {
      const context = getAudioContext();
      if (context.state === "suspended") {
        await context.resume();
      }

      const buffer = await getDecodedBuffer(context);
      if (!running || token !== generation) return;

      disposeNodes();

      const nextSource = context.createBufferSource();
      const nextGain = context.createGain();
      const trim = Math.min(LOOP_TRIM_SECONDS, Math.max(0, buffer.duration / 4));
      const loopStart = trim;
      const loopEnd = Math.max(loopStart + 0.001, buffer.duration - trim);

      nextSource.buffer = buffer;
      nextSource.loop = true;
      nextSource.loopStart = loopStart;
      nextSource.loopEnd = loopEnd;
      nextGain.gain.setValueAtTime(requestedVolume, context.currentTime);

      nextSource.connect(nextGain);
      nextGain.connect(context.destination);

      source = nextSource;
      gainNode = nextGain;
      nextSource.start(0, loopStart);
    } catch (error) {
      console.error("Failed to start shrine Web Audio loop", error);
      if (token === generation) running = false;
    }
  };

  const wrapper = {
    play: () => {
      running = true;
      const token = ++generation;
      void startDecodedLoop(token);
      return true;
    },
    stop: () => {
      running = false;
      generation += 1;
      disposeNodes();
      return wrapper;
    },
    destroy: () => {
      wrapper.stop();
    },
    setVolume: (value: number) => {
      const next = Number(value);
      if (Number.isFinite(next)) requestedVolume = clamp01(next);
      if (gainNode && sharedContext) {
        gainNode.gain.setValueAtTime(requestedVolume, sharedContext.currentTime);
      }
      return wrapper;
    },
    get volume() {
      return requestedVolume;
    },
    get isPlaying() {
      return running;
    },
  };

  return wrapper;
};

// This patch intentionally runs BEFORE background-audio-bootstrap.ts.
// The bootstrap's outer ambience wrapper will see this sound as having no
// duration/seek values, so it never starts its timer-based crossfade. The shrine
// therefore stays on one native AudioBufferSourceNode loop for its whole lifetime.
const html5ManagerProto = phaserRuntime.Sound?.HTML5AudioSoundManager?.prototype as any;
if (html5ManagerProto && !html5ManagerProto.__summerEndShrineWebAudioPatched) {
  const originalAdd = html5ManagerProto.add;

  html5ManagerProto.add = function addShrineWebAudioLoop(
    key: unknown,
    config?: Record<string, unknown>
  ) {
    if (String(key) === SHRINE_AUDIO_KEY) {
      return createShrineLoopSound(config);
    }
    return originalAdd.call(this, key, config);
  };

  html5ManagerProto.__summerEndShrineWebAudioPatched = true;
}
